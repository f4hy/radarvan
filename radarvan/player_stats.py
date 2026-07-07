"""Compute player stats."""

from collections import Counter, defaultdict

from .api_types import (
    MatchInfo,
    General,
    PlayerStats,
    PlayerStat,
    WinLoss,
)
from . import game_composition
from .general_stats import CPU_NAMES
import structlog
from .player_ids import PLAYER_NAMES, resolve_player_name

logger = structlog.get_logger(__name__)

NEEDED_GAMES = 8


def most_common_colors(games: list[MatchInfo]) -> dict[str, str]:
    """Each player's most common raw in-game color across every game they've
    played (e.g. "Red", "Blue") - this community's players rarely contest the
    same color, so it doubles as a data-driven identity color for the UI
    (PlayerChip) instead of an arbitrary hash. Restricted to known roster
    names (PLAYER_NAMES minus the CPU labels folded into it) - unresolved/
    CPU/junk names aren't real identities worth a color.
    """
    counts: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for game in games:
        for p in game.players:
            if not p.is_real() or p.Type == "C":
                continue
            name = resolve_player_name(p.name, p.color)
            if name not in PLAYER_NAMES or name in CPU_NAMES:
                continue
            counts[name][p.color] += 1
    return {
        name: color_counts.most_common(1)[0][0] for name, color_counts in counts.items()
    }


def total_games(player_stat: PlayerStat) -> int:
    return sum(wl.wins + wl.losses for wl in player_stat.stats.values())


def stats_game_filter(game: MatchInfo) -> bool:
    """The game set behind the Player Stats page W/L numbers.

    Complete, competitive team games. Shared with the player profile page so
    its record and per-general numbers match this page's.
    """
    return not game.incomplete and game_composition.competitive_game_filter(
        game.composition
    )


def get_player_stats(
    games: list[MatchInfo], game_format: str | None = None
) -> PlayerStats:
    player_wl: dict[str, PlayerStat] = {}
    player_counts: defaultdict[str, Counter[str]] = defaultdict(Counter)

    for game in games:
        if game.incomplete:
            continue
        if game.composition is None or not game_composition.is_recognized_team_game(
            game.composition
        ):
            continue

        category = game.composition.category
        is_competitive = stats_game_filter(game)

        for player in game.players:
            name = resolve_player_name(player.name, player.color)
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
            if not player.is_real():
                continue
            if player.won:
                player_wl[name].stats[player.general].wins += 1
            else:
                player_wl[name].stats[player.general].losses += 1

    for name, stat in player_wl.items():
        counts = player_counts[name]
        stat.game_counts = {"total": sum(counts.values()), **counts}

    filtered = [stat for stat in player_wl.values() if total_games(stat) > NEEDED_GAMES]

    return PlayerStats(player_stats=sorted(filtered, key=total_games, reverse=True))
