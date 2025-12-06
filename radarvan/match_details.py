"""Get match info from a replay."""

from api_types import (
    PlayerSummary as APIPlayerSummary,
)
from cncstats_types import EnhancedReplay
from api_types import (
    MatchDetails,
    SpentOverTime,
)
import logging
from dataclasses import dataclass

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
    player_index_to_name = {i: p.Name for i, p in enumerate(players)}

    md = MoneyData(player_monies={}, player_collected={})

    previous = {player_index_to_name[i]: 1_000_000 for i, p in enumerate(players)}
    sofar = {player_index_to_name[i]: 0 for i, p in enumerate(players)}

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


def api_player_summaries(replay: EnhancedReplay) -> list[APIPlayerSummary]:
    color_map = {p.Name: p.Color for p in replay.Header.Metadata.Players}
    player_summaries: list[APIPlayerSummary] = []
    for s in replay.Summary:
        d = s.model_dump()
        d["Color"] = color_map.get(s.Name, "black").lower().replace("color", "")
        APIPlayerSummary.model_validate(d)
        player_summaries.append(d)
    return player_summaries


def match_details_from_replay(replay: EnhancedReplay) -> MatchDetails | None:
    money = player_money_from_replay(replay)
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
        money_collected_values=money.player_collected,
        player_summary=api_player_summaries(replay),
    )
