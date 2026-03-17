"""Get match info from a replay."""

from __future__ import annotations

import asyncio
from collections import defaultdict

from .api_types import (
    PlayerSummary as APIPlayerSummary,
)
from .cncstats_types_v2 import EnhancedReplayV2
from .api_types import (
    KillEventOutput,
    MatchDetails,
    SpentOverTime,
    Team,
    UpgradeEvent,
    Upgrades,
    APM,
    SuperlativeData,
    SuperlativePlayerSummary,
)
import logging
from dataclasses import dataclass
from pydantic import BaseModel
from .utils import minutess_per_step

from .db_utils import ReplayManager, DatabaseManager

logger = logging.getLogger(__name__)


@dataclass
class MoneyData:
    player_monies: dict[float, dict[str, int]]
    player_collected: dict[float, dict[str, int]]


def collected_value(current_val: int, prev_val: int) -> int:
    if current_val > prev_val:
        return current_val - prev_val
    return 0


def player_money_from_replay(replay: EnhancedReplayV2) -> MoneyData:
    """Get player money from replay."""

    if replay.Stats is None:
        return MoneyData(player_monies={}, player_collected={})

    scale = minutess_per_step(replay)
    interval = replay.Stats.game.snapshotInterval
    name_by_idx = {p.index: p.displayName for p in replay.Stats.players}
    ts_players = [p for p in replay.Stats.timeSeries.players if p.index in name_by_idx]
    num_snapshots = max((len(p.money) for p in ts_players), default=0)

    md = MoneyData(player_monies={}, player_collected={})
    for snap_idx in range(num_snapshots):
        frame = snap_idx * interval
        time_key = frame * scale
        md.player_monies[time_key] = {
            name_by_idx[p.index]: p.money[snap_idx]
            for p in ts_players
            if snap_idx < len(p.money)
        }
        md.player_collected[time_key] = {
            name_by_idx[p.index]: p.moneyEarned[snap_idx]
            for p in ts_players
            if snap_idx < len(p.moneyEarned)
        }
    return md


class FirstBlood(BaseModel):
    attacker: str
    victim: str
    atMinute: float


class StatsData(BaseModel):
    xp: dict[float, dict[str, int]]
    units_built: dict[float, dict[str, int]]
    units_lost: dict[float, dict[str, int]]
    money_earned: dict[float, dict[str, int]]
    units_killed: dict[float, dict[str, int]]
    buildings_killed: dict[float, dict[str, int]]
    buildings_lost: dict[float, dict[str, int]]
    buildings_built: dict[float, dict[str, int]]
    tech_buildings_captured: dict[float, dict[str, int]]
    faction_buildings_captured: dict[float, dict[str, int]]


class TimelineEvent(BaseModel):
    minute: float
    event_name: str


class AllExtractedData(BaseModel):
    stats_data: StatsData
    first_blood: FirstBlood | None
    building_first_blood: FirstBlood | None


def _sum(i: int | list[int]) -> int:
    return sum(i) if isinstance(i, list) else i


def is_action(order_name: str) -> bool:
    match order_name:
        case (
            "Chunksum" | "DeclareUserId" | "EndReplay" | "SelectBox" | "ClearSelection"
        ):
            return False
        case _ if order_name.startswith("Unknown"):
            return False
        case _:
            return True


ACTIVE_ACTIONS = {
    "AttackMove",
    "AttackObject",
    "BuildObject",
    "BuildUpgrade",
    "CreateUnit",
    "MoveTo",
    "ForceAttackObjectGuard",
    "FlamewallRocketPodContaminate",
    "Sell",
}


def is_active_action(order_name: str) -> bool:
    return order_name in ACTIVE_ACTIONS


def apms_from_replay(replay: EnhancedReplayV2) -> list[APM]:
    players = replay.Header.Metadata.Players
    action_counts = {p.Name: 0 for p in players if p.Team >= 0 and p.Type != "C"}
    player_first_active = {p.Name: -1 for p in players if p.Team >= 0}
    player_last_active = {p.Name: 0 for p in players if p.Team >= 0}

    for chunk in replay.Body:
        if chunk.PlayerName not in action_counts:
            continue
        if is_action(chunk.OrderName):
            action_counts[chunk.PlayerName] += 1
        if is_active_action(chunk.OrderName):
            player_last_active[chunk.PlayerName] = chunk.TimeCode
            if player_first_active[chunk.PlayerName] < 0:
                player_first_active[chunk.PlayerName] = chunk.TimeCode

    minutes_per = minutess_per_step(replay)

    player_minutes = {
        name: (player_last_active[name] - first) * minutes_per
        for name, first in player_first_active.items()
    }

    return [
        APM(
            player_name=name,
            action_count=count,
            minutes=player_minutes[name],
            apm=count / player_minutes[name],
        )
        for name, count in action_counts.items()
    ]


def _is_building(name: str) -> bool:
    """No way to know what is or is not a building right now

    TODO fix once this is added to the stats data. Assume non building for now
    """
    return False


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


def stats_data_from_replay(replay: EnhancedReplayV2) -> AllExtractedData:
    """Get stats data from replay."""

    data_types = [
        "xp",
        "units_built",
        "units_lost",
        "buildings_built",
        "buildings_lost",
        "money_earned",
        "units_killed",
        "buildings_killed",
        "tech_buildings_captured",
        "faction_buildings_captured",
    ]

    if replay.Stats is None:
        sd = StatsData.model_validate({t: {} for t in data_types})
        return AllExtractedData(
            stats_data=sd, first_blood=None, building_first_blood=None
        )

    scale = minutess_per_step(replay)
    name_by_idx = {p.index: p.displayName for p in replay.Stats.players}
    all_players = set(name_by_idx.values())
    header_team_by_name = {p.Name: p.Team for p in replay.Header.Metadata.Players}
    team_by_idx = {
        idx: header_team_by_name.get(name, -1) for idx, name in name_by_idx.items()
    }
    # money_earned from time series snapshots
    interval = replay.Stats.game.snapshotInterval
    ts_players = [p for p in replay.Stats.timeSeries.players if p.index in name_by_idx]
    num_snapshots = max((len(p.moneyEarned) for p in ts_players), default=0)
    money_earned: dict[float, dict[str, int]] = {}
    for snap_idx in range(num_snapshots):
        frame = snap_idx * interval
        money_earned[frame * scale] = {
            name_by_idx[p.index]: p.moneyEarned[snap_idx]
            for p in ts_players
            if snap_idx < len(p.moneyEarned)
        }

    # xp from skillPointsEvents — each event records the player's current total
    xp: dict[float, dict[str, int]] = {}
    current_xp: dict[str, int] = dict.fromkeys(all_players, 0)
    xp_by_frame: dict[int, dict[str, int]] = defaultdict(dict)
    for ev in replay.Stats.skillPointsEvents:
        name = name_by_idx.get(ev.player, "unk")
        if name != "unk":
            xp_by_frame[ev.frame][name] = ev.skillPoints
    for frame in sorted(xp_by_frame):
        current_xp.update(xp_by_frame[frame])
        xp[frame * scale] = dict(current_xp)

    # units_built / buildings_built from buildEvents
    ub_deltas: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    bb_deltas: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for bev in replay.Stats.buildEvents:
        name = name_by_idx.get(bev.player, "unk")
        if name == "unk":
            continue
        if _is_building(bev.object):
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
    for kev in replay.Stats.killEvents:
        killer_name = name_by_idx.get(kev.killerPlayer, "unk")
        victim_name = name_by_idx.get(kev.victimPlayer, "unk")
        at_minute = kev.frame * scale
        is_bldg = _is_building(kev.victim)
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
    for cev in replay.Stats.captureEvents:
        new_team = team_by_idx.get(cev.newOwner, -1)
        old_team = team_by_idx.get(cev.oldOwner, -1)
        if new_team >= 0 and new_team == old_team:
            continue
        name = name_by_idx.get(cev.newOwner, "unk")
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
        units_killed=units_killed,
        buildings_killed=buildings_killed,
        tech_buildings_captured=tech_buildings_captured,
        faction_buildings_captured=faction_buildings_captured,
    )
    return AllExtractedData(
        stats_data=sd,
        first_blood=first_blood,
        building_first_blood=building_first_blood,
    )


def events_from_replay(replay: EnhancedReplayV2) -> dict[str, Upgrades]:
    scale = minutess_per_step(replay)
    players = replay.Header.Metadata.Players
    player_index_to_name = {i: p.Name for i, p in enumerate(players)}

    upgrades: dict[str, list[UpgradeEvent]] = {
        name: [] for name in player_index_to_name.values()
    }
    for chunk in replay.Body:
        if not chunk.OrderName.startswith("BuildUpgrade"):
            continue
        if not chunk.Details:
            continue
        event = UpgradeEvent(
            player_name=chunk.PlayerName,
            timecode=chunk.TimeCode,
            upgrade_name=chunk.Details.Name.removeprefix("Upgrade_"),
            cost=chunk.Details.Cost or 0,
            at_minute=chunk.TimeCode * scale,
        )
        upgrades[chunk.PlayerName].append(event)

    return {name: Upgrades(upgrades=values) for name, values in upgrades.items()}


def api_player_summaries(replay: EnhancedReplayV2) -> list[APIPlayerSummary]:
    color_map = {p.Name: p.Color for p in replay.Header.Metadata.Players}
    player_summaries: list[APIPlayerSummary] = []
    for s in replay.Summary:
        if s.Team == Team.OBSERVER:
            continue
        d = s.model_dump()
        d["Color"] = color_map.get(s.Name, "black").lower().replace("color", "")
        player_summaries.append(APIPlayerSummary.model_validate(d))
    return player_summaries


def load_match_details(
    match_id: int, replay_manager: ReplayManager
) -> MatchDetails | None:
    """Load and parse match details for a single match_id. Returns None if not found."""
    from . import replay_files

    rep = replay_manager.get_replay_json_by_match_id(match_id)
    if rep is None:
        return None
    replay = replay_files.parse_replay(rep.replay_file_url, replay_manager)
    return match_details_from_replay(replay)


def load_match_details_threadsafe(
    match_id: int, db_manager: DatabaseManager
) -> MatchDetails | None:
    """Load match details with a fresh session — safe to call from any thread."""
    from .db_utils import ReplayManager as _ReplayManager

    try:
        with db_manager.get_session() as session:
            return load_match_details(match_id, _ReplayManager(session))
    except Exception:
        logger.exception(f"Failed to load match details for match_id={match_id}")
        return None


async def load_many_match_details(
    match_ids: list[int], db_manager: DatabaseManager, max_concurrent: int = 20
) -> list[MatchDetails]:
    """Load match details for many matches in parallel with bounded concurrency."""
    semaphore = asyncio.Semaphore(max_concurrent)

    async def _bounded(match_id: int) -> MatchDetails | None:
        async with semaphore:
            return await asyncio.to_thread(
                load_match_details_threadsafe, match_id, db_manager
            )

    results = await asyncio.gather(*[_bounded(mid) for mid in match_ids])
    return [r for r in results if r is not None]


def superlative_data_from_details(d: MatchDetails) -> SuperlativeData:
    """Convert a full MatchDetails into the smaller SuperlativeData used by superlatives."""

    def _last_total(key: str) -> int:
        data = d.stats_data.get(key, {})
        if not data:
            return 0
        return sum(data[max(data)].values())

    money_values = d.money_values
    if money_values:
        first_key, last_key = min(money_values), max(money_values)
        start_balance = sum(money_values[first_key].values())
        end_balance = sum(money_values[last_key].values())
    else:
        start_balance = end_balance = 0
    match_money_spent = start_balance + _last_total("money_earned") - end_balance

    player_money_collected: dict[str, int] = {}
    if d.money_collected_values:
        last_time = max(d.money_collected_values)
        player_money_collected = {
            name: amt
            for name, amt in d.money_collected_values[last_time].items()
            if amt > 0
        }

    player_summary = [
        SuperlativePlayerSummary(
            name=ps.Name,
            color=ps.Color,
            won=ps.Win,
            money_spent=d.player_money_spent.get(ps.Name, 0),
            units_created_count=sum(v.Count for v in ps.UnitsCreated.values()),
            buildings_built_count=sum(v.Count for v in ps.BuildingsBuilt.values()),
        )
        for ps in d.player_summary
    ]

    return SuperlativeData(
        match_id=d.match_id,
        first_blood=d.first_blood,
        building_first_blood=d.building_first_blood,
        apms=d.apms,
        player_summary=player_summary,
        upgrade_counts={
            player_name: len(upgrades.upgrades)
            for player_name, upgrades in d.upgrade_events.items()
            if upgrades.upgrades
        },
        total_units_killed=_last_total("units_killed"),
        total_buildings_killed=_last_total("buildings_killed"),
        total_xp=_last_total("xp"),
        match_money_spent=match_money_spent,
        player_money_collected=player_money_collected,
    )


async def load_many_superlative_data(
    match_ids: list[int],
    db_manager: DatabaseManager,
    max_concurrent: int = 2,
    chunk_size: int = 10,
) -> list[SuperlativeData]:
    """Load reduced superlative data for many matches in parallel.

    Each match is loaded as full MatchDetails, immediately converted to the smaller
    SuperlativeData, and the full details discarded — keeping peak memory low.

    Processed in chunks of chunk_size to bound the number of coroutines scheduled at
    once and give Python's GC a chance to release completed batches between chunks.
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def _bounded(match_id: int) -> SuperlativeData | None:
        async with semaphore:
            details = await asyncio.to_thread(
                load_match_details_threadsafe, match_id, db_manager
            )
        if details is None:
            return None
        return superlative_data_from_details(details)

    all_results: list[SuperlativeData] = []
    for i in range(0, len(match_ids), chunk_size):
        chunk = match_ids[i : i + chunk_size]
        chunk_results = await asyncio.gather(*[_bounded(mid) for mid in chunk])
        all_results.extend(r for r in chunk_results if r is not None)
    return all_results


def match_details_from_replay(replay: EnhancedReplayV2) -> MatchDetails | None:
    money = player_money_from_replay(replay)
    apms = apms_from_replay(replay)
    stats_data = stats_data_from_replay(replay)
    first_blood = (
        stats_data.first_blood.model_dump() if stats_data.first_blood else None
    )
    building_first_blood = (
        stats_data.building_first_blood.model_dump()
        if stats_data.building_first_blood
        else None
    )
    upgrades = events_from_replay(replay)
    player_money_spent = {}
    kill_events = []
    if replay.Stats is not None:
        name_by_idx = {p.index: p.displayName for p in replay.Stats.players}
        player_money_spent = {p.displayName: p.moneySpent for p in replay.Stats.players}
        scale = minutess_per_step(replay)
        kill_events = [
            KillEventOutput(
                at_minute=ev.frame * scale,
                killer_player=name_by_idx.get(ev.killerPlayer, "unk"),
                victim_player=name_by_idx.get(ev.victimPlayer, "unk"),
                x=ev.x,
                y=ev.y,
                killer=ev.killer,
                victim=ev.victim,
                damage_type=ev.damageType,
            )
            for ev in replay.Stats.killEvents
        ]
    return MatchDetails(
        match_id=replay.Header.Metadata.Seed,
        game_version=replay.Header.Version,
        map_name=replay.Header.Metadata.MapFile,
        costs=[],
        apms=apms,
        upgrade_events=upgrades,
        spent=SpentOverTime(
            buildings=[],
            units=[],
            upgrades=[],
            total=[],
        ),
        money_values=money.player_monies,
        money_collected_values=stats_data.stats_data.money_earned,
        stats_data=stats_data.stats_data.model_dump(),
        player_money_spent=player_money_spent,
        first_blood=first_blood,
        building_first_blood=building_first_blood,
        player_summary=api_player_summaries(replay),
        kill_events=kill_events,
    )
