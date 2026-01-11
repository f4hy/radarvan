"""Get match info from a replay."""

from api_types import (
    PlayerSummary as APIPlayerSummary,
)
from collections import defaultdict
from cncstats_types import EnhancedReplay
from api_types import MatchDetails, SpentOverTime, Team, UpgradeEvent, Upgrades
import logging
from dataclasses import dataclass
from pydantic import BaseModel
from utils import minutess_per_step

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


class StatsData(BaseModel):
    xp: dict[float, dict[str, int]]
    units_built: dict[float, dict[str, int]]
    units_lost: dict[float, dict[str, int]]
    money_earned: dict[float, dict[str, int]]
    units_killed: dict[float, dict[str, int]]
    buildings_killed: dict[float, dict[str, int]]
    buildings_lost: dict[float, dict[str, int]]
    buildings_built: dict[float, dict[str, int]]


def _sum(i: int | list[int]) -> int:
    return sum(i) if isinstance(i, list) else i

def stats_data_from_replay(replay: EnhancedReplay) -> StatsData:
    """Get player money from replay."""

    scale = minutess_per_step(replay)
    players = replay.Header.Metadata.Players
    player_index_to_name = {i: p.Name for i, p in enumerate(players) if p.Team >= 0}

    data: dict[str, dict[float, dict[str, int]]]
    prev_vals: dict[str, dict[str, int]]
    data_types = ["xp", "units_built", "units_lost", "buildings_built", "buildings_lost", "money_earned", "units_killed", "buildings_killed"]
    data = {t: {} for t in data_types}
    prev_vals = {t: {} for t in data_types}

    for chunk in replay.Body:
        if chunk.PlayerStats is None:
            continue
        for dt in data_types:
            if (d := getattr(chunk.PlayerStats, dt)) is not None:
                new_values = {name: _sum(d[i]) for i, name in player_index_to_name.items()}
                if new_values != prev_vals[dt]:
                    data[dt][chunk.TimeCode * scale] = new_values
                    prev_vals[dt] = new_values

    sd = StatsData.model_validate(data)

    return sd


def events_from_replay(replay: EnhancedReplay) -> dict[str, Upgrades]:
    scale = minutess_per_step(replay)
    players = replay.Header.Metadata.Players
    player_index_to_name = {i: p.Name for i, p in enumerate(players) if p.Team >= 0}

    upgrades: dict[str, list[UpgradeEvent]] = {
        name: [] for name in player_index_to_name.values()
    }
    has_details = [c.Details for c in replay.Body if c.Details]
    logger.info(f"details {has_details=}")
    for chunk in replay.Body:
        if not chunk.OrderName.startswith("BuildUpgrade"):
            continue
        logger.info(f"details {chunk.Details=}")
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
        APIPlayerSummary.model_validate(d)
        player_summaries.append(d)
    return player_summaries


def match_details_from_replay(replay: EnhancedReplay) -> MatchDetails | None:
    money = player_money_from_replay(replay)
    stats_data = stats_data_from_replay(replay)
    upgrades = events_from_replay(replay)
    logger.info(f"Money {len(money.player_monies)}")
    return MatchDetails(
        match_id=replay.Header.Metadata.Seed,
        costs=[],
        apms=[],
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
        stats_data=stats_data.model_dump(),
        player_summary=api_player_summaries(replay),
    )
