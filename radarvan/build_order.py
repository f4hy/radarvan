"""Per-player opening build order (buildings, units, upgrades).

Reads build events out of the parsed replay and returns a `BuildOrder` per
player. Consecutive identical builds are collapsed into a single run (e.g.
9 workers in a row become one entry with ``count=9`` spanning a time range), so
the cap-on-rows budget is spent on distinct openings rather than worker spam.
Economy/non-combat units are flagged so the UI can dim or fold them.
"""

from __future__ import annotations

from collections import defaultdict

from .api_types import BuildOrder, BuildOrderEntry, Upgrades
from .cncstats_model.zhreplay import EnhancedReplayV2
from .replay_helpers import clean_object_name, is_initial_seed_frame
from .utils import minutes_per_step

# Number of (collapsed) rows kept per category.
_MAX_ROWS = 10

# Substrings (matched against the cleaned object name, case-insensitively) that
# mark a non-combat economy unit: GLA workers, USA/China construction dozers,
# supply trucks, and USA supply chinooks. These flood the early units list, so
# they're flagged for the UI to dim and collapsed aggressively.
_ECONOMY_UNIT_KEYWORDS = ("worker", "dozer", "supplytruck", "chinook")


def _is_economy_unit(cleaned_name: str) -> bool:
    low = cleaned_name.lower()
    return any(keyword in low for keyword in _ECONOMY_UNIT_KEYWORDS)


def _collapse_runs(entries: list[BuildOrderEntry], limit: int) -> list[BuildOrderEntry]:
    """Collapse consecutive same-name entries into runs, then cap at ``limit`` rows.

    ``entries`` must already be in chronological order. A run records the first
    build's minute as ``at_minute``, the last build's minute as ``end_minute``
    (None for a single build), and how many builds it covers as ``count``. Cost
    stays per-unit.
    """
    collapsed: list[BuildOrderEntry] = []
    for entry in entries:
        if collapsed and collapsed[-1].name == entry.name:
            prev = collapsed[-1]
            collapsed[-1] = BuildOrderEntry(
                at_minute=prev.at_minute,
                end_minute=entry.at_minute,
                name=prev.name,
                cost=prev.cost,
                count=prev.count + 1,
                is_economy=prev.is_economy,
            )
        else:
            collapsed.append(entry)
    return collapsed[:limit]


def build_order_from_replay(
    replay: EnhancedReplayV2,
    name_by_idx: dict[int, str],
    upgrades_by_player: dict[str, Upgrades],
) -> dict[str, BuildOrder]:
    """First ``_MAX_ROWS`` collapsed buildings, units, and upgrades per player.

    Buildings vs units come straight from cncstats's ``objectType`` on each
    build event - ``structure`` is a building, everything else (infantry,
    vehicle, missing) is treated as a unit. Consecutive identical builds are
    collapsed into runs *before* capping, and economy units are flagged.
    """
    scale = minutes_per_step(replay)
    buildings: dict[str, list[BuildOrderEntry]] = defaultdict(list)
    units: dict[str, list[BuildOrderEntry]] = defaultdict(list)
    if replay.stats is not None:
        for bev in sorted(replay.stats.build_events, key=lambda e: e.frame):
            if is_initial_seed_frame(bev.frame):
                continue
            name = name_by_idx.get(bev.player)
            if name is None:
                continue
            cleaned = clean_object_name(bev.object)
            if bev.object_type == "structure":
                buildings[name].append(
                    BuildOrderEntry(
                        at_minute=bev.frame * scale, name=cleaned, cost=bev.cost
                    )
                )
            else:
                units[name].append(
                    BuildOrderEntry(
                        at_minute=bev.frame * scale,
                        name=cleaned,
                        cost=bev.cost,
                        is_economy=_is_economy_unit(cleaned),
                    )
                )

    upgrades: dict[str, list[BuildOrderEntry]] = {}
    for player_name, ups in upgrades_by_player.items():
        ordered = sorted(ups.upgrades, key=lambda u: u.at_minute)
        upgrades[player_name] = [
            BuildOrderEntry(
                at_minute=u.at_minute,
                name=clean_object_name(u.upgrade_name),
                cost=u.cost,
            )
            for u in ordered
        ]

    all_names = set(buildings) | set(units) | set(upgrades)
    return {
        name: BuildOrder(
            buildings=_collapse_runs(buildings.get(name, []), _MAX_ROWS),
            units=_collapse_runs(units.get(name, []), _MAX_ROWS),
            upgrades=_collapse_runs(upgrades.get(name, []), _MAX_ROWS),
        )
        for name in all_names
    }
