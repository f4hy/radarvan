"""Per-player win-loss over a caller-chosen game set, grouped by any key."""

from collections import defaultdict
from collections.abc import Callable, Iterable, Iterator

from .api_types import MatchInfo, PlayerWL
from .game_composition import RosterSlot
from .player_ids import resolve_player_name


def decided_games(games: Iterable[MatchInfo]) -> Iterator[MatchInfo]:
    return (g for g in games if not g.incomplete and g.winning_team >= 1)


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
