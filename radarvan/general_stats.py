"""Compute generals stats."""

from .api_types import (
    MatchInfo,
    General,
    GeneralStat,
    GeneralStats,
    WinLoss,
)
from . import replay_files
import logging

logger = logging.getLogger(__name__)


def get_player_stats(games: list[MatchInfo]) -> GeneralStats:
    general_stats: dict[str, GeneralStat] = {}

    for game in games:
        if game.incomplete:
            continue
        if not replay_files.path_filter(game.filename):
            continue
        for player in game.players:
            if player.general not in general_stats:
                general_stats[player.general] = GeneralStat(
                    general=player.general,
                    stats=[],
                    total=WinLoss(wins=0, losses=0),
                )
            if player.general == General.UNRECOGNIZED:
                continue
            if player.team == game.winning_team:
                general_stats[player.general].total.wins += 1
            else:
                general_stats[player.general].total.losses += 1

    filtered = [
        s
        for s in sorted(general_stats.values(), key=lambda x: x.general)
        if (s.total.wins + s.total.losses) > 0
    ]
    return GeneralStats(general_stats=filtered)
