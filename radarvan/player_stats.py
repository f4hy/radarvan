"""Compute player stats."""

from collections import Counter, defaultdict
from datetime import date
from typing import NamedTuple

from .api_types import (
    MatchInfo,
    General,
    PlayerStats,
    PlayerStat,
    WinLoss,
)
from . import game_composition
from .matches import months_back_cutoff
import structlog
from .player_ids import PLAYER_NAMES, resolve_player_name

logger = structlog.get_logger(__name__)

NEEDED_GAMES = 8

# How far back "most common color" looks to reflect a player's *current*
# favorite rather than an average over their entire history - a player who
# switched colors a year ago shouldn't still show their old one.
RECENT_COLOR_MONTHS = 6


class ColorCounts(NamedTuple):
    """Per-player colour tallies over two windows.

    Named rather than a bare pair: both fields have the same type, so swapping
    them would type-check and silently make every player's "current" colour
    their all-time one.
    """

    all_time: defaultdict[str, Counter[str]]
    recent: defaultdict[str, Counter[str]]


def _color_counts(games: list[MatchInfo], recent_cutoff: date) -> ColorCounts:
    """All-time and recent-only (``date >= recent_cutoff``) color counts, in
    one pass over ``games`` rather than filtering-then-counting twice."""
    all_time: defaultdict[str, Counter[str]] = defaultdict(Counter)
    recent: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for game in games:
        # roster().humans is the whole CPU/observer filter - the old
        # `name in CPU_NAMES` guard below was a second, weaker one.
        for p in game.roster().humans:
            if not p.has_known_general:
                continue
            name = resolve_player_name(p.name, p.color)
            if name not in PLAYER_NAMES:
                continue
            all_time[name][p.color] += 1
            if game.date >= recent_cutoff:
                recent[name][p.color] += 1
    return ColorCounts(all_time=all_time, recent=recent)


def most_common_colors(games: list[MatchInfo]) -> dict[str, str]:
    """Each player's most common raw in-game color over their last
    RECENT_COLOR_MONTHS months (e.g. "Red", "Blue") - this community's
    players rarely contest the same color, so it doubles as a data-driven
    identity color for the UI (PlayerChip) instead of an arbitrary hash.
    Restricted to known roster names (PLAYER_NAMES minus the CPU labels
    folded into it) - unresolved/CPU/junk names aren't real identities worth
    a color. Players with no games in the recent window (inactive, or new
    and not yet resolved into it) fall back to their full history instead of
    losing a color entirely.
    """
    counts = _color_counts(games, months_back_cutoff(RECENT_COLOR_MONTHS))
    for name, color_counts in counts.all_time.items():
        counts.recent.setdefault(name, color_counts)
    return {
        name: color_counts.most_common(1)[0][0]
        for name, color_counts in counts.recent.items()
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

        # Observers are dropped up front so they're never counted as having
        # played in `player_counts`.
        for player in game.roster().competitors:
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
            if not player.has_known_general:
                continue
            general = General(player.general)
            if player.won:
                player_wl[name].stats[general].wins += 1
            else:
                player_wl[name].stats[general].losses += 1

    for name, stat in player_wl.items():
        counts = player_counts[name]
        stat.game_counts = {"total": sum(counts.values()), **counts}

    filtered = [stat for stat in player_wl.values() if total_games(stat) > NEEDED_GAMES]

    return PlayerStats(player_stats=sorted(filtered, key=total_games, reverse=True))
