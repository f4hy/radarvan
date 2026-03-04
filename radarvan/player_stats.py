"""Compute player stats."""

from collections import Counter

from .api_types import (
    MatchInfo,
    General,
    PlayerStats,
    PlayerStat,
    WinLoss,
)
from . import replay_files
from . import game_composition
import logging
from .player_ids import resolve_player_name

logger = logging.getLogger(__name__)

NEEDED_GAMES = 8


def total_games(player_stat: PlayerStat) -> int:
    return sum(wl.wins + wl.losses for wl in player_stat.stats.values())


def get_player_stats(games: list[MatchInfo], game_format: str | None = None) -> PlayerStats:
    player_wl: dict[str, PlayerStat] = {}
    player_counts: dict[str, Counter[str]] = {}

    for game in games:
        if game.incomplete:
            continue
        if not replay_files.path_filter(game.filename):
            continue

        category = game.composition.category if game.composition else "Unknown"
        is_competitive = game_composition.competitive_game_filter(game.composition)

        for player in game.players:
            name = resolve_player_name(player.name, player.color)

            # Count all valid games regardless of competitive status
            if name not in player_counts:
                player_counts[name] = Counter()
            player_counts[name][category] += 1

            # Win/loss stats only for competitive games matching the format filter
            if not is_competitive:
                continue
            if game_format is not None and category != game_format:
                continue

            if name not in player_wl:
                player_wl[name] = PlayerStat(
                    player_name=name,
                    stats={General(i): WinLoss(wins=0, losses=0) for i in range(12)},
                    faction_stats=[],
                    over_time=[],
                )
            if player.general == General.UNRECOGNIZED:
                continue
            if player.won:
                player_wl[name].stats[player.general].wins += 1
            else:
                player_wl[name].stats[player.general].losses += 1

    for name, stat in player_wl.items():
        counts = player_counts.get(name, Counter())
        stat.game_counts = {"total": sum(counts.values()), **counts}

    filtered = [
        stat for stat in player_wl.values() if total_games(stat) > NEEDED_GAMES
    ]

    return PlayerStats(player_stats=sorted(filtered, key=total_games, reverse=True))
