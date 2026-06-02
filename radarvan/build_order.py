"""Per-player first-N build order (buildings, units, upgrades).

Reads build events out of the parsed replay and returns a `BuildOrder` per
player, capped at 10 entries each (chronological).
"""

from __future__ import annotations

from collections import defaultdict

from .api_types import BuildOrder, BuildOrderEntry, Upgrades
from .cncstats_model.zhreplay import EnhancedReplayV2
from .replay_helpers import clean_object_name, is_initial_seed_frame
from .utils import minutess_per_step


def build_order_from_replay(
    replay: EnhancedReplayV2,
    name_by_idx: dict[int, str],
    upgrades_by_player: dict[str, Upgrades],
) -> dict[str, BuildOrder]:
    """First 10 buildings, units, and upgrades per player, in chronological order.

    Buildings vs units come straight from cncstats's ``objectType`` on each
    build event — ``structure`` is a building, everything else (infantry,
    vehicle, missing) is treated as a unit. The per-player ``buildings_built``
    / ``units_created`` summary maps aren't always populated, so we don't rely
    on them.
    """
    scale = minutess_per_step(replay)
    buildings: dict[str, list[BuildOrderEntry]] = defaultdict(list)
    units: dict[str, list[BuildOrderEntry]] = defaultdict(list)
    if replay.stats is not None:
        for bev in sorted(replay.stats.build_events, key=lambda e: e.frame):
            if is_initial_seed_frame(bev.frame):
                continue
            name = name_by_idx.get(bev.player)
            if name is None:
                continue
            entry = BuildOrderEntry(
                at_minute=bev.frame * scale,
                name=clean_object_name(bev.object),
                cost=bev.cost,
            )
            if bev.object_type == "structure":
                if len(buildings[name]) < 10:
                    buildings[name].append(entry)
            else:
                if len(units[name]) < 10:
                    units[name].append(entry)

    upgrades: dict[str, list[BuildOrderEntry]] = {}
    for player_name, ups in upgrades_by_player.items():
        first_ten = sorted(ups.upgrades, key=lambda u: u.at_minute)[:10]
        upgrades[player_name] = [
            BuildOrderEntry(
                at_minute=u.at_minute,
                name=clean_object_name(u.upgrade_name),
                cost=u.cost,
            )
            for u in first_ten
        ]

    all_names = set(buildings) | set(units) | set(upgrades)
    return {
        name: BuildOrder(
            buildings=buildings.get(name, []),
            units=units.get(name, []),
            upgrades=upgrades.get(name, []),
        )
        for name in all_names
    }
