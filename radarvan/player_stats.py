"""Compute player stats."""

from .api_types import (
    MatchInfo,
    General,
    PlayerStats,
    PlayerStat,
    WinLoss,
)
from . import replay_files
import logging
from .player_ids import player_name_map

logger = logging.getLogger(__name__)


def total_games(player_stat: PlayerStat) -> int:
    return sum(wl.wins + wl.losses for wl in player_stat.stats.values())


def get_player_stats(games: list[MatchInfo]) -> PlayerStats:
    player_stats: dict[str, PlayerStat] = {}

    for game in games:
        if game.incomplete:
            continue
        if not replay_files.path_filter(game.filename):
            continue
        for player in game.players:
            name = player_name_map(player.name)
            if name not in player_stats:
                player_stats[name] = PlayerStat(
                    player_name=name,
                    stats={General(i): WinLoss(wins=0, losses=0) for i in range(12)},
                    faction_stats=[],
                    over_time=[],
                )
            if player.general == General.UNRECOGNIZED:
                continue
            logger.info(f"adding {player.general=} win for {game.winning_team}")
            if player.team == game.winning_team:
                player_stats[name].stats[player.general].wins += 1
            else:
                player_stats[name].stats[player.general].losses += 1

    filtered = [stat for stat in player_stats.values() if total_games(stat) > 8]

    return PlayerStats(player_stats=sorted(filtered, key=total_games, reverse=True))
