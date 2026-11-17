"""Per-game general matchups across a bracket's linked 1v1s."""

from collections.abc import Iterable, Mapping

from .api_types import BracketFactionGame, General, MatchInfo
from .db import TournamentGame
from .player_ids import resolve_player_name
from .player_records import decided_games


def bracket_faction_games(
    links: Iterable[TournamentGame],
    known: Mapping[int, MatchInfo],
    set_winners: Mapping[str, str | None],
) -> list[BracketFactionGame]:
    """One row per decided, linked 1v1 whose two generals are known, oldest first."""
    stage_of = {link.match_id: link for link in links if link.stage is not None}
    rows = []
    for game in decided_games(known[i] for i in stage_of if i in known):
        sides = game.roster().participants
        winners = [p for p in sides if p.won]
        losers = [p for p in sides if not p.won]
        if len(winners) != 1 or len(losers) != 1:
            continue
        won, lost = winners[0], losers[0]
        if not (won.has_known_general and lost.has_known_general):
            continue
        link = stage_of[game.id]
        winner = resolve_player_name(won.name, won.color)
        set_winner = set_winners.get(link.stage or "")
        rows.append(
            BracketFactionGame(
                match_id=game.id,
                stage=link.stage or "",
                round_name=link.round_name,
                timestamp=game.timestamp,
                winner=winner,
                winner_general=General(won.general),
                loser=resolve_player_name(lost.name, lost.color),
                loser_general=General(lost.general),
                winner_lost_set=None if set_winner is None else winner != set_winner,
            )
        )
    return sorted(rows, key=lambda r: r.timestamp)
