"""Compute generals stats."""

from .api_types import (
    MatchInfo,
    General,
    GeneralStat,
    GeneralStats,
    WinLoss,
)
from . import game_composition
from . import player_ids
import structlog

logger = structlog.get_logger(__name__)


CPU_NAMES = set(player_ids.CPU_NAME_MAPPING.values())


def get_generals_stats(games: list[MatchInfo]) -> GeneralStats:
    general_stats: dict[General, GeneralStat] = {}
    for game in games:
        if game.incomplete or game.winning_team < 1:
            continue
        if not game_composition.competitive_game_filter(game.composition):
            continue
        resolved = [
            player_ids.resolve_player_name(p.name, p.color) for p in game.players
        ]
        if sum(1 for n in resolved if n in CPU_NAMES) > 1:
            continue
        for player, name in zip(game.players, resolved, strict=True):
            if player.general not in general_stats:
                general_stats[player.general] = GeneralStat(
                    general=player.general,
                    stats=[],
                    total=WinLoss(wins=0, losses=0),
                )
            if not player.is_real():
                continue
            if name in CPU_NAMES:
                continue
            if player.won:
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
    logger.info("totals", wins=wins, losses=losses)
    return GeneralStats(general_stats=filtered)
