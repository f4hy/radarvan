"""Get match info from a replay."""

from __future__ import annotations

import asyncio
from collections import defaultdict

from .api_types import (
    PlayerSummary as APIPlayerSummary,
    ObjectSummary as APIObjectSummary,
)
from .cncstats_model.zhreplay import EnhancedReplayV2
from .api_types import (
    KillEventOutput,
    MatchDetails,
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
    players = replay.header.metadata.players
    action_counts = {p.name: 0 for p in players if int(p.team) >= 0 and p.type != "C"}
    player_first_active = {p.name: -1 for p in players if int(p.team) >= 0}
    player_last_active = {p.name: 0 for p in players if int(p.team) >= 0}

    for chunk in replay.body:
        if chunk.player_name not in action_counts:
            continue
        if is_action(chunk.order_name):
            action_counts[chunk.player_name] += 1
        if is_active_action(chunk.order_name):
            player_last_active[chunk.player_name] = chunk.time_code
            if player_first_active[chunk.player_name] < 0:
                player_first_active[chunk.player_name] = chunk.time_code

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


def stats_data_from_replay(replay: EnhancedReplayV2) -> AllExtractedData | None:
    """Get stats data from replay."""

    if not replay.stats or not replay.game_info:
        return None

    scale = minutess_per_step(replay)
    name_by_idx: dict[int, str] = {p.index: p.name for p in replay.summary}
    all_players: set[str] = set(name_by_idx.values())
    header_team_by_name = {p.name: int(p.team) for p in replay.header.metadata.players}
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
            if snap_idx < len(p.money_earned)
        }
        money[frame * scale] = {
            name_by_idx[p.index]: p.money[snap_idx]
            for p in ts_players
            if snap_idx < len(p.money_earned)
        }

    # xp from skillPointsEvents — each event records the player's current total
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
        first_blood=first_blood,
        building_first_blood=building_first_blood,
    )


def events_from_replay(replay: EnhancedReplayV2) -> dict[str, Upgrades]:
    scale = minutess_per_step(replay)
    player_index_to_name: dict[int, str] = {
        i: p.name for i, p in enumerate(replay.header.metadata.players)
    }

    upgrades: dict[str, list[UpgradeEvent]] = {
        name: [] for name in player_index_to_name.values()
    }
    for chunk in replay.body:
        if not chunk.order_name.startswith("BuildUpgrade"):
            continue
        if not chunk.details:
            continue
        detail_name = (
            getattr(chunk.details, "Name", None)
            or (chunk.details.get("name") if isinstance(chunk.details, dict) else None)
            or ""
        )
        detail_cost = getattr(chunk.details, "Cost", None) or (
            chunk.details.get("cost") if isinstance(chunk.details, dict) else None
        )
        event = UpgradeEvent(
            player_name=chunk.player_name,
            timecode=chunk.time_code,
            upgrade_name=detail_name.removeprefix("Upgrade_"),
            cost=detail_cost or 0,
            at_minute=chunk.time_code * scale,
        )
        upgrades[chunk.player_name].append(event)

    return {name: Upgrades(upgrades=values) for name, values in upgrades.items()}


def api_player_summaries(
    replay: EnhancedReplayV2,
    units_destroyed: dict[str, dict[str, APIObjectSummary]] | None = None,
    buildings_destroyed: dict[str, dict[str, APIObjectSummary]] | None = None,
    units_lost_by_type: dict[str, dict[str, APIObjectSummary]] | None = None,
    buildings_lost_by_type: dict[str, dict[str, APIObjectSummary]] | None = None,
) -> list[APIPlayerSummary]:
    color_map = {p.name: p.color for p in replay.header.metadata.players}
    player_summaries: list[APIPlayerSummary] = []
    for s in replay.summary:
        if s.team == Team.OBSERVER:
            continue
        color = (color_map.get(s.name, "") or "black").lower().replace("color", "")
        player_summaries.append(
            APIPlayerSummary(
                Name=s.name,
                Side=s.side,
                Team=s.team,
                Win=s.win,
                Color=color,
                UnitsCreated={
                    k: APIObjectSummary(Count=v.count, TotalSpent=v.total_spent)
                    for k, v in s.units_created.items()
                },
                BuildingsBuilt={
                    k: APIObjectSummary(Count=v.count, TotalSpent=v.total_spent)
                    for k, v in s.buildings_built.items()
                },
                UpgradesBuilt={
                    k: APIObjectSummary(Count=v.count, TotalSpent=v.total_spent)
                    for k, v in s.upgrades_built.items()
                },
                PowersUsed=s.powers_used,
                UnitsDestroyed=(units_destroyed or {}).get(s.name, {}),
                BuildingsDestroyed=(buildings_destroyed or {}).get(s.name, {}),
                UnitsLostByType=(units_lost_by_type or {}).get(s.name, {}),
                BuildingsLostByType=(buildings_lost_by_type or {}).get(s.name, {}),
            )
        )
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

    player_summary = [
        SuperlativePlayerSummary(
            name=ps.Name,
            color=ps.Color,
            won=ps.Win,
            money_spent=0,  # TODO fix
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
        match_money_spent=0,  # TODO fix
        player_money_collected={},  # TODO fix
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
    apms = apms_from_replay(replay)
    stats_data = stats_data_from_replay(replay)
    if stats_data:
        first_blood = (
            stats_data.first_blood.model_dump() if stats_data.first_blood else None
        )
        building_first_blood = (
            stats_data.building_first_blood.model_dump()
            if stats_data.building_first_blood
            else None
        )
    else:
        first_blood = None
        building_first_blood = None
    upgrades = events_from_replay(replay)
    name_by_idx: dict[int, str] = {}
    player_money_spent: dict[str, int] = {}
    for p in replay.summary:
        name_by_idx[p.index] = p.name
        player_money_spent[p.name] = p.money_spent
    scale = minutess_per_step(replay)
    kill_events = [
        KillEventOutput(
            at_minute=ev.frame * scale,
            killer_player=name_by_idx.get(ev.killer_player, "unk"),
            victim_player=name_by_idx.get(ev.victim_player, "unk"),
            x=ev.x,
            y=ev.y,
            killer=ev.killer,
            victim=ev.victim,
            damage_type=ev.damage_type,
        )
        for ev in (replay.stats.kill_events if replay.stats else [])
    ]
    # Build unit cost map from build events {object_name: cost}
    unit_cost: dict[str, int] = {}
    for bev in (replay.stats.build_events if replay.stats else []):
        if bev.object not in unit_cost and bev.cost > 0:
            unit_cost[bev.object] = bev.cost

    # Single pass: compute destroyed (killer perspective) and lost (victim perspective)
    ud_by_player: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    bd_by_player: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    ul_by_player: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    bl_by_player: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for kev in (replay.stats.kill_events if replay.stats else []):
        cost = unit_cost.get(kev.victim, 0)
        is_bldg = _is_building(kev.victim_type)
        killer_name = name_by_idx.get(kev.killer_player, "unk")
        victim_name = name_by_idx.get(kev.victim_player, "unk")
        if killer_name != "unk":
            dest = bd_by_player if is_bldg else ud_by_player
            dest[killer_name][kev.victim][0] += 1
            dest[killer_name][kev.victim][1] += cost
        if victim_name != "unk":
            lost = bl_by_player if is_bldg else ul_by_player
            lost[victim_name][kev.victim][0] += 1
            lost[victim_name][kev.victim][1] += cost

    def _to_obj_map(
        by_player: dict[str, dict[str, list[int]]],
    ) -> dict[str, dict[str, APIObjectSummary]]:
        return {
            name: {u: APIObjectSummary(Count=d[0], TotalSpent=d[1]) for u, d in units.items()}
            for name, units in by_player.items()
        }

    hdr = replay.header
    return MatchDetails(
        match_id=replay.replay_id,
        game_version=hdr.version,
        map_name=hdr.metadata.map_path,
        costs=[],
        apms=apms,
        upgrade_events=upgrades,
        stats_data=stats_data.stats_data.model_dump() if stats_data else {},
        player_money_spent=player_money_spent,
        first_blood=first_blood,
        building_first_blood=building_first_blood,
        player_summary=api_player_summaries(
            replay,
            units_destroyed=_to_obj_map(ud_by_player),
            buildings_destroyed=_to_obj_map(bd_by_player),
            units_lost_by_type=_to_obj_map(ul_by_player),
            buildings_lost_by_type=_to_obj_map(bl_by_player),
        ),
        kill_events=kill_events,
    )
