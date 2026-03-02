from datetime import date
from pydantic import BaseModel

from .api_types import (
    MatchInfo,
    General,
    Statistic,
    WinLoss,
    PlayerStat,
)
import logging
from . import player_stats

logger = logging.getLogger(__name__)


class Superlatives(BaseModel):
    match_count: int
    stats: list[Statistic]


def get_player_highest_winrate(
    games: list[MatchInfo], computed_at: date
) -> list[Statistic]:
    _player_stats = player_stats.get_player_stats(games).player_stats

    def total_win_rate(win_losses: list[WinLoss]) -> float:
        total_wins = sum(wl.wins for wl in win_losses)
        total_games = sum(wl.wins + wl.losses for wl in win_losses)
        return total_wins / total_games

    player_winrates = {
        s.player_name: total_win_rate(list(s.stats.values())) for s in _player_stats
    }

    stats: list[Statistic] = []

    for general in General:
        if general < 0:
            continue

        def win_rate(s: PlayerStat) -> float:
            wl = s.stats[general]
            if wl.losses == 0:
                return 0.0
            return (
                (float(wl.wins) / (wl.wins + wl.losses))
                - player_winrates[s.player_name]
            ) * 100

        highest_winrate = max(_player_stats, key=win_rate)
        stats.append(
            Statistic(
                stat_name=f"highest win rate above player average {General(general).name}",
                date_computed=computed_at,
                value=f"+{win_rate(highest_winrate):.1f}%",
                player=highest_winrate.player_name,
            )
        )
    return stats


def _fmt_duration(minutes: float) -> str:
    total_seconds = int(minutes * 60)
    return f"{total_seconds // 60}m {total_seconds % 60:02d}s"


def get_match_duration_extremes(
    games: list[MatchInfo], computed_at: date
) -> list[Statistic]:
    """Longest and shortest complete match for each of 2v2, 3v3, and 4v4."""
    stats: list[Statistic] = []
    for team_size in (2, 3, 4):
        category = f"{team_size}v{team_size}"
        eligible = [
            g
            for g in games
            if g.composition is not None
            and g.composition.category == category
            and not g.incomplete
        ]
        if not eligible:
            continue
        longest = max(eligible, key=lambda g: g.duration_minutes)
        shortest = min(eligible, key=lambda g: g.duration_minutes)
        stats.append(
            Statistic(
                stat_name=f"Longest {category}",
                date_computed=computed_at,
                value=_fmt_duration(longest.duration_minutes),
                match_id=longest.id,
            )
        )
        stats.append(
            Statistic(
                stat_name=f"Shortest {category}",
                date_computed=computed_at,
                value=_fmt_duration(shortest.duration_minutes),
                match_id=shortest.id,
            )
        )
    return stats


def get_superlatives(games: list[MatchInfo]) -> Superlatives:
    computed_at = date.today()
    count = len(games)

    stats: list[Statistic] = [
        *get_player_highest_winrate(games, computed_at),
        *get_match_duration_extremes(games, computed_at),
    ]

    return Superlatives(
        match_count=count,
        stats=stats,
    )
