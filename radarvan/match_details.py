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


def _get_player_money_index(idx: int, cnc_player_money: Money) -> int:
    match idx:
        case 1:
            return cnc_player_money.Player1Money
        case 2:
            return cnc_player_money.Player2Money
        case 3:
            return cnc_player_money.Player3Money
        case 4:
            return cnc_player_money.Player4Money
        case 5:
            return cnc_player_money.Player5Money
        case 6:
            return cnc_player_money.Player6Money
        case 7:
            return cnc_player_money.Player7Money
        case 8:
            return cnc_player_money.Player8Money
    logger.warning("Beyond 8 players!")
    return 0


def player_money_from_replay(replay: EnhancedReplay) -> dict[int, dict[str, int]]:
    """Get player money from replay."""

    players = replay.Header.Metadata.Players
    player_index_to_name = {i: p.Name for i, p in enumerate(players, start=1)}

    player_monies: dict[int, dict[str, float]] = {}
    for chunk in replay.Body:
        if chunk.PlayerMoney is None:
            continue
        player_monies[chunk.TimeCode] = {
            name: _get_player_money_index(i, chunk.PlayerMoney)
            for i, name in player_index_to_name.items()
        }
    return player_monies


def match_details_from_replay(replay: EnhancedReplay) -> MatchDetails | None:
    money = player_money_from_replay(replay)
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
    )
