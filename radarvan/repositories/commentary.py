"""MatchupCommentaryCache repository.

A durable cache of AI-generated pre-game matchup commentary, keyed on
(player1, player2, round_name). Generation is a real, billed LLM call (see
radarvan.commentary) - once written, a row is served on every subsequent
request for the same triple instead of regenerating.
"""

from datetime import UTC, datetime

from ..db import MatchupCommentaryCache
from .base import BaseRepo


class MatchupCommentaryRepo(BaseRepo):
    """Operations on MatchupCommentaryCache."""

    def get_cached_commentary(
        self, player1: str, player2: str, round_name: str
    ) -> str | None:
        """Return the cached commentary text, or None on a cache miss."""
        row = self.session.get(MatchupCommentaryCache, (player1, player2, round_name))
        return row.commentary if row is not None else None

    def save_commentary(
        self,
        player1: str,
        player2: str,
        round_name: str,
        commentary: str,
        provider: str,
    ) -> None:
        """Upsert the generated commentary for (player1, player2, round_name)."""
        # computed_at is set explicitly: session.merge() copies attribute state
        # by PK, and an unset onupdate column would be merged as NULL. See
        # MatchDetailsRepo.save_cached_details / CLAUDE.md gotcha.
        self.session.merge(
            MatchupCommentaryCache(
                player1=player1,
                player2=player2,
                round_name=round_name,
                commentary=commentary,
                provider=provider,
                computed_at=datetime.now(UTC),
            )
        )
        self._commit_if_auto()
