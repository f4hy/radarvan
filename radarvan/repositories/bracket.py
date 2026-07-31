"""Bracket tournament repository (1v1 double-elimination bracket).

Only one BracketTournament row exists at a time; ``create`` replaces it.
Match topology/routing lives in ``radarvan.bracket`` - this repo only
persists the seeded entrant list and per-match date/best-of/score.
"""

from datetime import date, datetime

from sqlalchemy import select

from ..db import BracketMatchState, BracketPlayer, BracketTournament

from .base import BaseRepo


class BracketRepo(BaseRepo):
    """Operations on the current bracket tournament (players + match state)."""

    def get_active(self) -> BracketTournament | None:
        stmt = select(BracketTournament).order_by(BracketTournament.id.desc())
        return self.session.scalars(stmt).first()

    def create(
        self, players: list[tuple[int, str]], reveal_at: datetime | None = None
    ) -> BracketTournament:
        """Replace any existing bracket with a fresh one for these seeded entrants.

        ``players`` is a list of (seed, player_name) pairs.
        """
        existing = self.get_active()
        if existing is not None:
            self.session.delete(existing)
            self.session.flush()

        tournament = BracketTournament()
        tournament.reveal_at = reveal_at
        tournament.players = [
            BracketPlayer(seed=seed, player_name=name) for seed, name in players
        ]
        self.session.add(tournament)
        self.session.flush()
        self._commit_if_auto()
        return tournament

    def set_reveal_at(
        self, tournament_id: int, reveal_at: datetime | None
    ) -> BracketTournament:
        tournament = self.session.get(BracketTournament, tournament_id)
        if tournament is None:
            raise ValueError(f"No bracket tournament with id {tournament_id}")
        tournament.reveal_at = reveal_at
        self.session.flush()
        self._commit_if_auto()
        return tournament

    def get_match_states(self, tournament_id: int) -> dict[str, BracketMatchState]:
        stmt = select(BracketMatchState).where(
            BracketMatchState.tournament_id == tournament_id
        )
        rows = self.session.scalars(stmt).all()
        return {row.match_id: row for row in rows}

    def set_match(
        self,
        tournament_id: int,
        match_id: str,
        scheduled_date: date | None,
        best_of: int | None,
        score_a: int | None,
        score_b: int | None,
    ) -> BracketMatchState:
        row = self.session.get(BracketMatchState, (tournament_id, match_id))
        if row is None:
            row = BracketMatchState(tournament_id=tournament_id, match_id=match_id)
            self.session.add(row)
        row.scheduled_date = scheduled_date
        row.best_of = best_of
        row.score_a = score_a
        row.score_b = score_b
        self.session.flush()
        self._commit_if_auto()
        return row
