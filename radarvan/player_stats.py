"""Computer player stats."""

"""Get match info from a replay.
"""

import datetime
from api_types import (
    Matches,
    MatchInfo,
    Player,
    General,
    Team,
    PlayerStats,
    PlayerStat,
    GeneralWL,
    WinLoss,
)
from cncstats_types import EnhancedReplay, PlayerSummary, GeneralsHeader
import utils
import logging

logger = logging.getLogger(__name__)


def get_player_stats(games: list[MatchInfo]) -> PlayerStats:
    player_stats: dict[str, PlayerStat] = {}

    for game in games:
        if game.incomplete:
            continue
        for player in game.players:
            if player.name not in player_stats:
                player_stats[player.name] = PlayerStat(
                    player_name=player.name,
                    stats={General(i): WinLoss(wins=0, losses=0) for i in range(12)},
                    faction_stats=[],
                    over_time=[],
                )
            if player.general == General.UNRECOGNIZED:
                continue
            if player.team == game.winning_team:
                player_stats[player.name].stats[player.general].wins += 1
            else:
                player_stats[player.name].stats[player.general].losses += 1

    return PlayerStats(player_stats=player_stats.values())
