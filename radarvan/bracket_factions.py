"""Per-game general matchups across a bracket's linked 1v1s."""

from collections.abc import Iterable, Mapping

from .api_types import BracketFactionGame, General, MatchInfo
from .db import TournamentGame
from .player_ids import resolve_player_name
from .player_records import decided_games, winner_and_loser


def bracket_faction_games(
    links: Iterable[TournamentGame],
    known: Mapping[int, MatchInfo],
    set_winners: Mapping[str, str | None],
) -> list[BracketFactionGame]:
    """One row per decided, linked 1v1 whose two generals are known, oldest first."""
    stage_of = {link.match_id: link.stage for link in links if link.stage is not None}
    games = sorted(
        (known[i] for i in stage_of if i in known), key=lambda m: m.timestamp
    )
    rows = []
    for game in decided_games(games):
        sides = winner_and_loser(game)
        if sides is None:
            continue
        stage = stage_of[game.id]
        winner = resolve_player_name(sides.won.name, sides.won.color)
        set_winner = set_winners.get(stage)
        rows.append(
            BracketFactionGame(
                match_id=game.id,
                stage=stage,
                winner=winner,
                winner_general=General(sides.won.general),
                loser=resolve_player_name(sides.lost.name, sides.lost.color),
                loser_general=General(sides.lost.general),
                winner_lost_set=None if set_winner is None else winner != set_winner,
            )
        )
    return rows
