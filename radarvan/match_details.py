"""Get match info from a replay."""

import datetime
from api_types import Matches, MatchInfo, Player, General, Team
from cncstats_types import EnhancedReplay, PlayerSummary, Money
from api_types import (
    Matches,
    MatchInfo,
    Player,
    General,
    Team,
    MatchDetails,
    SpentOverTime,
)
import logging
import utils

logger = logging.getLogger(__name__)


def player_money_from_replay(replay: EnhancedReplay) -> dict[int, dict[str, int]]:
    """Get player money from replay."""

    players = replay.Header.Metadata.Players
    player_index_to_name = {i: p.Name for i, p in enumerate(players)}

    player_monies: dict[int, dict[str, float]] = {}
    for chunk in replay.Body:
        if chunk.PlayerMoney is None:
            continue
        player_monies[chunk.TimeCode] = {
            name: chunk.PlayerMoney.PlayerMoney[i]
            for i, name in player_index_to_name.items()
        }
    return player_monies


def match_details_from_replay(replay: EnhancedReplay) -> MatchDetails | None:
    money = player_money_from_replay(replay)
    logger.info(f"Summary : {replay.Summary}")
    return MatchDetails(
        match_id=replay.Header.TimeStampBegin,
        costs=[],
        apms=[],
        upgrade_events={},
        spent=SpentOverTime(
            buildings=[],
            units=[],
            upgrades=[],
            total=[],
        ),
        money_values=money,
        player_summary=[s.model_dump() for s in  replay.Summary],
    )
