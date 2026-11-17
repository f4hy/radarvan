"""Per-player win-loss over a caller-chosen game set, grouped by any key."""

from collections import defaultdict
from collections.abc import Callable, Iterable, Iterator
from typing import NamedTuple

from .api_types import MatchInfo, PlayerWL
from .game_composition import RosterSlot
from .player_ids import resolve_player_name


def decided_games(games: Iterable[MatchInfo]) -> Iterator[MatchInfo]:
    return (g for g in games if not g.incomplete and g.winning_team >= 1)


class WinnerLoser(NamedTuple):
    won: RosterSlot
    lost: RosterSlot


def winner_and_loser(match: MatchInfo) -> WinnerLoser | None:
    """The two sides of a two-human 1v1 with known generals and one winner."""
    slots = [s for s in match.roster().human_participants if s.has_known_general]
    winners = [s for s in slots if s.won]
    losers = [s for s in slots if not s.won]
    if len(winners) != 1 or len(losers) != 1:
        return None
    return WinnerLoser(winners[0], losers[0])


def player_records_by[K](
    games: Iterable[MatchInfo], key: Callable[[MatchInfo, RosterSlot], K]
) -> dict[K, list[PlayerWL]]:
    """No competitive filter: every decided game counts. Busiest player first."""
    records: dict[K, dict[str, list[int]]] = defaultdict(
        lambda: defaultdict(lambda: [0, 0])
    )
    for game in decided_games(games):
        for player in game.roster().participants:
            name = resolve_player_name(player.name, player.color)
            records[key(game, player)][name][0 if player.won else 1] += 1
    return {
        k: sorted(
            (
                PlayerWL(player=name, wins=w, losses=l)
                for name, (w, l) in by_player.items()
            ),
            key=lambda p: (-(p.wins + p.losses), -p.wins, p.player),
        )
        for k, by_player in records.items()
    }
