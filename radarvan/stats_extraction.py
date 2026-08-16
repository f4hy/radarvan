"""Extract time-series and milestone data from a parsed `replay.stats` block.

Builds cumulative per-frame series for money / xp / units / buildings /
captures, plus the first-blood detection used by MatchDetails. Also exposes
`milestone_timings_from_replay` for one-off "first time player hit X"
extractions used by the superlatives.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import NamedTuple

from pydantic import BaseModel

from .cncstats_model.statsfile import IncomeBySource
from .cncstats_model.zhreplay import EnhancedReplayV2
from .utils import minutes_per_step


@dataclass
class MoneyData:
    player_monies: dict[float, dict[str, int]]
    player_collected: dict[float, dict[str, int]]


class FirstBlood(BaseModel):
    attacker: str
    victim: str
    atMinute: float


class StatsData(BaseModel):
    xp: dict[float, dict[str, int]]
    units_built: dict[float, dict[str, int]]
    units_lost: dict[float, dict[str, int]]
    money: dict[float, dict[str, int]]
    money_earned: dict[float, dict[str, int]]
    money_spent: dict[float, dict[str, int]]
    units_killed: dict[float, dict[str, int]]
    buildings_killed: dict[float, dict[str, int]]
    buildings_lost: dict[float, dict[str, int]]
    buildings_built: dict[float, dict[str, int]]
    tech_buildings_captured: dict[float, dict[str, int]]
    faction_buildings_captured: dict[float, dict[str, int]]


class AllExtractedData(BaseModel):
    stats_data: StatsData
    # Cumulative income broken down by source, keyed by the IncomeBySource
    # field name ("supply", "oil_derrick", ...). Only populated when cncstats
    # supplied `incomeBySource` for this replay (newer replay versions only).
    # Sparse to keep the wire payload small: an all-zero source is omitted, a
    # player who never earned from a source is omitted from that source's
    # snapshots, and only change-boundary snapshots are kept - so a missing
    # source/player/timestep means "zero" / "unchanged", never "unknown".
    income_by_source: dict[str, dict[float, dict[str, int]]]
    first_blood: FirstBlood | None
    building_first_blood: FirstBlood | None


# The replay model owns the source list; a source added there flows through
# extraction (and the wire dict) without further edits here.
_INCOME_SOURCES = tuple(IncomeBySource.model_fields)

# Trickle sources (supply, black market, hacker) change on nearly every
# snapshot, so "only changed snapshots" alone can't bound the payload for a
# long game. Cap the kept grid: a details chart is well under a thousand
# pixels wide, so ~300 points is visually lossless while keeping the wire
# size and recharts render cost flat regardless of match length.
_MAX_INCOME_SNAPSHOTS = 300


def _sparse_keep_indices(
    series: list[list[int]], num_snapshots: int, max_points: int
) -> list[int]:
    """Snapshot indices worth emitting for a set of cumulative series.

    Keeps the endpoints and every index where some series changes value - plus
    the index right before each change, so plateaus keep their shape when the
    consumer interpolates between kept points - then thins by a uniform stride
    if still over ``max_points`` (the endpoints always survive)."""
    keep: set[int] = {0, num_snapshots - 1}
    for vals in series:
        if len(keep) >= num_snapshots:
            break
        for i in range(1, len(vals)):
            if vals[i] != vals[i - 1]:
                keep.add(i)
                keep.add(i - 1)
    kept = sorted(keep)
    if len(kept) > max_points:
        stride = -(-len(kept) // max_points)  # ceil division
        last = kept[-1]
        kept = kept[::stride]
        if kept[-1] != last:
            kept.append(last)
    return kept


def _is_building(name: str | None) -> bool:
    return name == "structure"


def _event_counts_to_series(
    deltas_by_frame: dict[int, dict[str, int]],
    all_players: set[str],
    scale: float,
) -> dict[float, dict[str, int]]:
    """Convert per-frame event count deltas into a cumulative time series."""
    result: dict[float, dict[str, int]] = {}
    cumulative: dict[str, int] = dict.fromkeys(all_players, 0)
    for frame in sorted(deltas_by_frame):
        for name, delta in deltas_by_frame[frame].items():
            cumulative[name] = cumulative.get(name, 0) + delta
        result[frame * scale] = dict(cumulative)
    return result


def _drop_redundant_consecutive(
    series: dict[float, dict[str, int]],
) -> dict[float, dict[str, int]]:
    """Drop rows identical to the previously kept row (the first row always stays).

    Lossless: a straight line between two equal-valued points looks the same
    whether or not identical points sit between them, so a flat run only needs
    its starting point.
    """
    result: dict[float, dict[str, int]] = {}
    last: dict[str, int] | None = None
    for t, values in series.items():
        if values != last:
            result[t] = values
            last = values
    return result


def stats_data_from_replay(replay: EnhancedReplayV2) -> AllExtractedData | None:
    """Get stats data from replay."""

    if not replay.stats or not replay.game_info:
        return None

    scale = minutes_per_step(replay)
    name_by_idx: dict[int, str] = {p.index: p.name for p in replay.summary}
    all_players: set[str] = set(name_by_idx.values())
    header_team_by_name = {
        p.name: int(p.team or "-1") for p in replay.header.metadata.players
    }
    team_by_idx = {
        idx: header_team_by_name.get(name, -1) for idx, name in name_by_idx.items()
    }
    # money_earned from time series snapshots
    interval = replay.game_info.snapshot_interval
    ts_players = [p for p in replay.stats.time_series.players if p.index in name_by_idx]
    num_snapshots = max((len(p.money_earned) for p in ts_players), default=0)
    money_earned: dict[float, dict[str, int]] = {}
    money_spent: dict[float, dict[str, int]] = {}
    money: dict[float, dict[str, int]] = {}
    for snap_idx in range(num_snapshots):
        frame = snap_idx * interval
        money_earned[frame * scale] = {
            name_by_idx[p.index]: p.money_earned[snap_idx]
            for p in ts_players
            if snap_idx < len(p.money_earned)
        }
        money_spent[frame * scale] = {
            name_by_idx[p.index]: p.money_spent[snap_idx]
            for p in ts_players
            if snap_idx < len(p.money_spent)
        }
        money[frame * scale] = {
            name_by_idx[p.index]: p.money[snap_idx]
            for p in ts_players
            if snap_idx < len(p.money)
        }
    money_earned = _drop_redundant_consecutive(money_earned)
    money_spent = _drop_redundant_consecutive(money_spent)
    money = _drop_redundant_consecutive(money)

    # income_by_source: only cncstats replay versions newer than statsVersion 1
    # populate this per-player. The dense form (every source x player x
    # snapshot) is mostly zeros and repeats, so emit it sparse (see the
    # AllExtractedData field comment). The series are cumulative, so a
    # (source, player) pair earned anything iff its final value is nonzero.
    pruned: dict[str, list[tuple[str, list[int]]]] = {}
    for src in _INCOME_SOURCES:
        entries = []
        for p in ts_players:
            if p.income_by_source is None:
                continue
            vals: list[int] = getattr(p.income_by_source, src)
            if vals and vals[-1] != 0:
                entries.append((name_by_idx[p.index], vals))
        if entries:
            pruned[src] = entries
    income_by_source: dict[str, dict[float, dict[str, int]]] = {
        src: {} for src in pruned
    }
    if pruned:
        kept = _sparse_keep_indices(
            [vals for entries in pruned.values() for _, vals in entries],
            num_snapshots,
            _MAX_INCOME_SNAPSHOTS,
        )
        for snap_idx in kept:
            minute = snap_idx * interval * scale
            for src, entries in pruned.items():
                income_by_source[src][minute] = {
                    name: vals[snap_idx]
                    for name, vals in entries
                    if snap_idx < len(vals)
                }

    # xp from skillPointsEvents - each event records the player's current total
    xp: dict[float, dict[str, int]] = {}
    current_xp: dict[str, int] = dict.fromkeys(all_players, 0)
    xp_by_frame: dict[int, dict[str, int]] = defaultdict(dict)
    for ev in replay.stats.skill_points_events:
        name = name_by_idx.get(ev.player, "unk")
        if name != "unk":
            xp_by_frame[ev.frame][name] = ev.skill_points
    for frame in sorted(xp_by_frame):
        current_xp.update(xp_by_frame[frame])
        xp[frame * scale] = dict(current_xp)

    # units_built / buildings_built from buildEvents
    ub_deltas: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    bb_deltas: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for bev in replay.stats.build_events:
        name = name_by_idx.get(bev.player, "unk")
        if name == "unk":
            continue
        if _is_building(bev.object_type):
            bb_deltas[bev.frame][name] += 1
        else:
            ub_deltas[bev.frame][name] += 1
    units_built = _event_counts_to_series(ub_deltas, all_players, scale)
    buildings_built = _event_counts_to_series(bb_deltas, all_players, scale)

    # units_killed / buildings_killed (credit killer) and units_lost / buildings_lost (credit victim)
    uk_deltas: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    bk_deltas: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    ul_deltas: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    bl_deltas: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    first_blood: FirstBlood | None = None
    building_first_blood: FirstBlood | None = None
    for kev in replay.stats.kill_events:
        killer_name = name_by_idx.get(kev.killer_player, "unk")
        victim_name = name_by_idx.get(kev.victim_player, "unk")
        at_minute = kev.frame * scale
        is_bldg = _is_building(kev.victim_type)
        if killer_name != "unk":
            (bk_deltas if is_bldg else uk_deltas)[kev.frame][killer_name] += 1
        if victim_name != "unk":
            (bl_deltas if is_bldg else ul_deltas)[kev.frame][victim_name] += 1
        if first_blood is None:
            first_blood = FirstBlood(
                attacker=killer_name, victim=victim_name, atMinute=at_minute
            )
        if building_first_blood is None and is_bldg:
            building_first_blood = FirstBlood(
                attacker=killer_name, victim=victim_name, atMinute=at_minute
            )
    units_killed = _event_counts_to_series(uk_deltas, all_players, scale)
    buildings_killed = _event_counts_to_series(bk_deltas, all_players, scale)
    units_lost = _event_counts_to_series(ul_deltas, all_players, scale)
    buildings_lost = _event_counts_to_series(bl_deltas, all_players, scale)

    # tech_buildings_captured / faction_buildings_captured from captureEvents
    # exclude captures where newOwner and oldOwner are on the same team (e.g. garrisoning)
    tc_deltas: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    fc_deltas: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for cev in replay.stats.capture_events:
        new_team = team_by_idx.get(cev.new_owner, -1)
        old_team = team_by_idx.get(cev.old_owner, -1)
        if new_team >= 0 and new_team == old_team:
            continue
        name = name_by_idx.get(cev.new_owner, "unk")
        if name == "unk":
            continue
        if cev.object.startswith("Tech"):
            tc_deltas[cev.frame][name] += 1
        else:
            fc_deltas[cev.frame][name] += 1
    tech_buildings_captured = _event_counts_to_series(tc_deltas, all_players, scale)
    faction_buildings_captured = _event_counts_to_series(fc_deltas, all_players, scale)

    sd = StatsData(
        xp=xp,
        units_built=units_built,
        units_lost=units_lost,
        buildings_built=buildings_built,
        buildings_lost=buildings_lost,
        money_earned=money_earned,
        money_spent=money_spent,
        money=money,
        units_killed=units_killed,
        buildings_killed=buildings_killed,
        tech_buildings_captured=tech_buildings_captured,
        faction_buildings_captured=faction_buildings_captured,
    )
    return AllExtractedData(
        stats_data=sd,
        income_by_source=income_by_source,
        first_blood=first_blood,
        building_first_blood=building_first_blood,
    )


class MilestoneTimings(NamedTuple):
    """Minutes to each milestone, keyed by player name.

    Named rather than a bare pair: both fields are ``dict[str, float]``, so
    swapping them at a call site would type-check and silently mislabel every
    rank-5 time as a search-and-destroy time.
    """

    time_to_rank_5: dict[str, float]
    time_to_search_destroy: dict[str, float]


def milestone_timings_from_replay(
    replay: EnhancedReplayV2, name_by_idx: dict[int, str]
) -> MilestoneTimings:
    """Minutes to rank 5 and to Search & Destroy, keyed by player name.

    Each map only contains entries for players who actually reached the milestone.
    """
    time_to_rank_5: dict[str, float] = {}
    time_to_search_destroy: dict[str, float] = {}
    if replay.stats is None:
        return MilestoneTimings(time_to_rank_5, time_to_search_destroy)
    scale = minutes_per_step(replay)
    for rev in replay.stats.rank_events:
        if rev.rank_level < 5:
            continue
        name = name_by_idx.get(rev.player)
        if name is None or name in time_to_rank_5:
            continue
        time_to_rank_5[name] = rev.frame * scale
    for bpev in replay.stats.battle_plan_events:
        if bpev.search_and_destroy <= 0:
            continue
        name = name_by_idx.get(bpev.player)
        if name is None or name in time_to_search_destroy:
            continue
        time_to_search_destroy[name] = bpev.frame * scale
    return MilestoneTimings(time_to_rank_5, time_to_search_destroy)
