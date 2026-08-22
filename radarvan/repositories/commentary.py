"""Repositories for the two durable caches of AI-generated text.

``MatchupCommentaryRepo`` holds the pre-game matchup commentary, keyed on
(player1, player2, round_name); ``BracketSummaryRepo`` holds the post-game
recap of a completed bracket set, keyed on (tournament_id, stage);
``GameNightSummaryRepo`` holds the once-a-night game-night recap, keyed on
the game-night date.
Generation is a real, billed LLM call either way (see radarvan.commentary) -
once written, a row is served on every subsequent request for the same key
instead of regenerating.
"""

from datetime import UTC, date, datetime

from ..db import (
    BracketSummaryCache,
    GameNightSummaryCache,
    MatchupCommentaryCache,
)
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


class BracketSummaryRepo(BaseRepo):
    """Operations on BracketSummaryCache."""

    def get_cached_summary(self, tournament_id: int, stage: str) -> str | None:
        """Return the cached post-game recap text, or None on a cache miss."""
        row = self.session.get(BracketSummaryCache, (tournament_id, stage))
        return row.summary if row is not None else None

    def save_summary(
        self, tournament_id: int, stage: str, summary: str, provider: str
    ) -> None:
        """Upsert the generated recap for (tournament_id, stage)."""
        # computed_at is set explicitly for the same reason it is in
        # save_commentary above - see that comment.
        self.session.merge(
            BracketSummaryCache(
                tournament_id=tournament_id,
                stage=stage,
                summary=summary,
                provider=provider,
                computed_at=datetime.now(UTC),
            )
        )
        self._commit_if_auto()


class GameNightSummaryRepo(BaseRepo):
    """Operations on GameNightSummaryCache.

    Read-mostly: the only writer is the nightly scheduler job (and the ops
    endpoint that triggers the same code by hand). See the table's docstring
    for why this cache is never filled on the read path.
    """

    def get_night_summary(self, night_date: date) -> GameNightSummaryCache | None:
        """Return the stored row for a game night, or None if none was written."""
        return self.session.get(GameNightSummaryCache, night_date)

    def has_night_summary(self, night_date: date) -> bool:
        return self.get_night_summary(night_date) is not None

    def list_summarized_nights(self, limit: int = 60) -> list[date]:
        """Most recent game nights that have a stored summary, newest first."""
        rows = (
            self.session.query(GameNightSummaryCache.night_date)
            .order_by(GameNightSummaryCache.night_date.desc())
            .limit(limit)
            .all()
        )
        return [row[0] for row in rows]

    def save_night_summary(
        self,
        night_date: date,
        summary: str,
        provider: str,
        match_count: int,
    ) -> None:
        """Upsert the generated recap for one game night."""
        # computed_at is set explicitly for the same reason it is in
        # save_commentary above - see that comment.
        self.session.merge(
            GameNightSummaryCache(
                night_date=night_date,
                summary=summary,
                provider=provider,
                match_count=match_count,
                computed_at=datetime.now(UTC),
            )
        )
        self._commit_if_auto()
