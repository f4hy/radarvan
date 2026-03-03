"""Get match info from a replay."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from .api_types import (
    PlayerSummary as APIPlayerSummary,
)
from .cncstats_types import EnhancedReplay
from .api_types import MatchDetails, SpentOverTime, Team, UpgradeEvent, Upgrades, APM
import logging
from dataclasses import dataclass
from pydantic import BaseModel
from .utils import minutess_per_step

if TYPE_CHECKING:
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


def player_money_from_replay(replay: EnhancedReplay) -> MoneyData:
    """Get player money from replay."""

    scale = minutess_per_step(replay)
    players = replay.Header.Metadata.Players
    player_index_to_name = {i: p.Name for i, p in enumerate(players) if p.Team >= 0}

    md = MoneyData(player_monies={}, player_collected={})

    previous = {
        player_index_to_name[i]: 1_000_000 for i, p in enumerate(players) if p.Team >= 0
    }
    sofar = {player_index_to_name[i]: 0 for i, p in enumerate(players) if p.Team >= 0}

    for chunk in replay.Body:
        if chunk.PlayerMoney is None:
            continue
        md.player_monies[chunk.TimeCode * scale] = {
            name: chunk.PlayerMoney.PlayerMoney[i]
            for i, name in player_index_to_name.items()
        }
        for i, name in player_index_to_name.items():
            current = chunk.PlayerMoney.PlayerMoney[i]
            collected = collected_value(current, previous[name])
            sofar[name] += collected
            previous[name] = current
        md.player_collected[chunk.TimeCode * scale] = sofar.copy()

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


def apms_from_replay(replay: EnhancedReplay) -> list[APM]:
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


def stats_data_from_replay(replay: EnhancedReplay) -> AllExtractedData:
    """Get player money from replay."""

    scale = minutess_per_step(replay)
    players = replay.Header.Metadata.Players

    player_index_to_name = {i: p.Name for i, p in enumerate(players) if p.Faction >= -2}

    data: dict[str, dict[float, dict[str, int]]]
    prev_vals: dict[str, dict[str, int]]
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
    data = {t: {} for t in data_types}
    prev_vals = {t: {} for t in data_types}

    first_blood: FirstBlood | None = None
    building_first_blood: FirstBlood | None = None

    for chunk in replay.Body:
        if chunk.PlayerStats is None:
            continue
        for dt in data_types:
            if (d := getattr(chunk.PlayerStats, dt)) is not None:
                if dt in {"units_killed"} and first_blood is None:
                    if sum(sum(v) for v in d) > 0:
                        for victim_idx, vs in enumerate(d):
                            for killer_idx, ks in enumerate(vs):
                                if ks > 0:
                                    first_blood = FirstBlood(
                                        attacker=player_index_to_name[killer_idx],
                                        victim=player_index_to_name.get(
                                            victim_idx, "unk"
                                        ),
                                        atMinute=chunk.TimeCode * scale,
                                    )
                if dt in {"buildings_killed"} and building_first_blood is None:
                    if sum(sum(v) for v in d) > 0:
                        for victim_idx, vs in enumerate(d):
                            for killer_idx, ks in enumerate(vs):
                                if ks > 0:
                                    building_first_blood = FirstBlood(
                                        attacker=player_index_to_name[killer_idx],
                                        victim=player_index_to_name.get(
                                            victim_idx, "unk"
                                        ),
                                        atMinute=chunk.TimeCode * scale,
                                    )

                if isinstance(d[0], list):
                    new_values = {
                        name: sum(v[i] for v in d)
                        for i, name in player_index_to_name.items()
                    }
                else:
                    new_values = {
                        name: d[i] for i, name in player_index_to_name.items()
                    }
                if new_values != prev_vals[dt]:
                    data[dt][chunk.TimeCode * scale] = new_values
                    prev_vals[dt] = new_values

    sd = StatsData.model_validate(data)
    return AllExtractedData(
        stats_data=sd,
        first_blood=first_blood,
        building_first_blood=building_first_blood,
    )


def events_from_replay(replay: EnhancedReplay) -> dict[str, Upgrades]:
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


def api_player_summaries(replay: EnhancedReplay) -> list[APIPlayerSummary]:
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


def match_details_from_replay(replay: EnhancedReplay) -> MatchDetails | None:
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
    logger.info(f"Money {len(money.player_monies)}")
    logger.info(f"First blood {first_blood}")
    logger.info(f"Last Event{replay.Body[-3:]}")
    logger.info(f"Headers {replay.Header}")
    return MatchDetails(
        match_id=replay.Header.Metadata.Seed,
        game_version=replay.Header.Version,
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
        # money_collected_values=money.player_collected,
        money_collected_values={},
        stats_data=stats_data.stats_data.model_dump(),
        first_blood=first_blood,
        building_first_blood=building_first_blood,
        player_summary=api_player_summaries(replay),
    )
