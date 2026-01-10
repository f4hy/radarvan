"""Get match info from a replay."""

from api_types import (
    PlayerSummary as APIPlayerSummary,
)
from cncstats_types import EnhancedReplay
from api_types import MatchDetails, SpentOverTime, Team
import logging
from dataclasses import dataclass
from pydantic import BaseModel

logger = logging.getLogger(__name__)


@dataclass
class MoneyData:
    player_monies: dict[int, dict[str, int]]
    player_collected: dict[int, dict[str, int]]


def collected_value(current_val: int, prev_val: int) -> int:
    if current_val > prev_val:
        return current_val - prev_val
    return 0


def player_money_from_replay(replay: EnhancedReplay) -> MoneyData:
    """Get player money from replay."""

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
        md.player_monies[chunk.TimeCode] = {
            name: chunk.PlayerMoney.PlayerMoney[i]
            for i, name in player_index_to_name.items()
        }
        for i, name in player_index_to_name.items():
            current = chunk.PlayerMoney.PlayerMoney[i]
            collected = collected_value(current, previous[name])
            sofar[name] += collected
            previous[name] = current
        md.player_collected[chunk.TimeCode] = sofar.copy()

    return md


class StatsData(BaseModel):
    xp: dict[int, dict[str, int]]
    units_built: dict[int, dict[str, int]]
    money_earned: dict[int, dict[str, int]]


def stats_data_from_replay(replay: EnhancedReplay) -> StatsData:
    """Get player money from replay."""

    players = replay.Header.Metadata.Players
    player_index_to_name = {i: p.Name for i, p in enumerate(players) if p.Team >= 0}

    data: dict[str, dict[int, dict[str, int]]]
    prev_vals: dict[str, dict[str, int]]
    data_types = ["xp", "units_built", "money_earned"]
    data = {t: {} for t in data_types}
    prev_vals = {t: {} for t in data_types}

    for chunk in replay.Body:
        if chunk.PlayerStats is None:
            continue
        for dt in data_types:
            if (d := getattr(chunk.PlayerStats, dt)) is not None:
                new_values = {name: d[i] for i, name in player_index_to_name.items()}
                if new_values != prev_vals[dt]:
                    data[dt][chunk.TimeCode] = new_values
                    prev_vals[dt] = new_values

    sd = StatsData.model_validate(data)

    return sd


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
    logger.info(f"Money {len(money.player_monies)}")
    return MatchDetails(
        match_id=replay.Header.Metadata.Seed,
        costs=[],
        apms=[],
        upgrade_events={},
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
