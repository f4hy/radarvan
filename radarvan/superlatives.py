from pydantic import BaseModel

from collections import Counter
from .api_types import (
    MatchInfo,
    General,
    GeneralStat,
    GeneralStats,
    WinLoss,
    PlayerStat,
)
from . import replay_files
import logging
from . import tournament
from . import player_stats

logger = logging.getLogger(__name__)


class Statistic(BaseModel, frozen=True):
    stat_name: str
    value: float | str | None = None
    player: str | None = None
    match_id: int | None = None


class Superlatives(BaseModel):
    match_count: int
    stats: list[Statistic]


def get_player_highest_winrate(games: list[MatchInfo]) -> list[Statistic]:
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
            return ((float(wl.wins) / (wl.wins + wl.losses)) - player_winrates[
                s.player_name
            ])*100

        highest_winrate = max(_player_stats, key=win_rate)
        stats.append(
            Statistic(
                stat_name=f"highest win rate above player average {General(general).name}",
                value=f"+{win_rate(highest_winrate):.1f}%",
                player=highest_winrate.player_name,
            )
        )
    return stats


def get_superlatives(games: list[MatchInfo]) -> Superlatives:
    count = len(games)

    stats: list[Statistic] = [
        *get_player_highest_winrate(games),
    ]

    return Superlatives(
        match_count=count,
        stats=stats,
    )
