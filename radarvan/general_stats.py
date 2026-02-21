"""Compute generals stats."""

from collections import Counter
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


def get_generals_stats(games: list[MatchInfo]) -> GeneralStats:
    general_stats: dict[str, GeneralStat] = {}
    cpu_names = {"cpu", "hardarmy"}
    for game in games:
        if game.incomplete or game.winning_team < 1:
            continue
        if not replay_files.path_filter(game.filename):
            continue
        cpu_count = Counter(p.name.lower() for p in game.players)["hardarmy"]
        if cpu_count > 1:
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
            if player.name.lower() in cpu_names:
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
    wins = sum(s.total.wins for s in general_stats.values())
    losses = sum(s.total.losses for s in general_stats.values())
    logger.info(f"Total wins {wins} total loses {losses}")
    return GeneralStats(general_stats=filtered)
