"""Tournament read models shared by `routes/tournaments.py` and commentary."""

from ..api_types import MatchInfo
from ..cache import sorted_deduped_matches
from ..db_utils import ReplayManager
from ..repositories import TournamentRepo


def linked_games(
    replay_manager: ReplayManager, tournament_repo: TournamentRepo, tournament_id: int
) -> list[MatchInfo]:
    """The matches linked to one tournament, newest first.

    Links whose match is missing from the listing are skipped - the link table
    has no FK to matches on purpose (see db.TournamentGame).
    """
    known = sorted_deduped_matches(replay_manager)
    linked = [
        known[link.match_id]
        for link in tournament_repo.list_links(tournament_id)
        if link.match_id in known
    ]
    linked.sort(key=lambda m: m.timestamp, reverse=True)
    return linked
