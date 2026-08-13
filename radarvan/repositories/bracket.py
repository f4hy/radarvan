"""Bracket tournament repository (1v1 double-elimination bracket).

Only one BracketTournament row exists at a time; ``create`` replaces it.
Match topology/routing lives in ``radarvan.bracket`` - this repo only
persists the seeded entrant list and per-match date/best-of/score.
"""

from datetime import datetime

from sqlalchemy import select

from .. import bracket
from ..db import BracketMatchState, BracketPlayer, BracketTournament

from .base import BaseRepo


def states_from_rows(
    raw_states: dict[str, BracketMatchState],
) -> dict[str, bracket.MatchState]:
    """DB rows -> the pure domain state ``bracket.resolve_bracket`` takes."""
    return {
        match_id: bracket.MatchState(
            best_of=row.best_of, score_a=row.score_a, score_b=row.score_b
        )
        for match_id, row in raw_states.items()
    }


def seed_to_name(tournament: BracketTournament) -> dict[int, str]:
    return {p.seed: p.player_name for p in tournament.players}


def resolve_from_states(
    tournament: BracketTournament, raw_states: dict[str, BracketMatchState]
) -> bracket.BracketResult:
    """Derive the whole bracket from seeds + stored scores.

    The single conversion from persisted rows into ``radarvan.bracket``'s pure
    domain. Every caller that needs a resolved bracket goes through here - the
    read endpoints and the tournament-game detector both did their own copy of
    this, which meant a new ``MatchState`` field would have silently resolved
    two different brackets.
    """
    return bracket.resolve_bracket(
        seed_to_name(tournament), states_from_rows(raw_states)
    )


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

    def set_tournament_id(self, bracket_id: int, tournament_id: int) -> None:
        """Attach this bracket to a durable ``Tournament`` row.

        The link points *up* only: resetting the bracket deletes this row but
        must never touch the Tournament or the TournamentGame links hanging
        off it, which is why there's no cascade in that direction.
        """
        tournament = self.session.get(BracketTournament, bracket_id)
        if tournament is None:
            raise ValueError(f"No bracket tournament with id {bracket_id}")
        tournament.tournament_id = tournament_id
        self.session.flush()
        self._commit_if_auto()

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
        scheduled_at: datetime | None,
        best_of: int | None,
        score_a: int | None,
        score_b: int | None,
    ) -> BracketMatchState:
        row = self.session.get(BracketMatchState, (tournament_id, match_id))
        if row is None:
            row = BracketMatchState(tournament_id=tournament_id, match_id=match_id)
            self.session.add(row)
        row.scheduled_at = scheduled_at
        row.best_of = best_of
        row.score_a = score_a
        row.score_b = score_b
        self.session.flush()
        self._commit_if_auto()
        return row

    def set_discord_event_id(
        self, tournament_id: int, match_id: str, discord_event_id: str | None
    ) -> None:
        """Persist the Discord scheduled event id created/updated for a
        match's ``scheduled_at`` - see ``discord_events.sync_match_event``,
        called by the route just before this."""
        row = self.session.get(BracketMatchState, (tournament_id, match_id))
        if row is None:
            raise ValueError(f"No bracket_match_state row for {match_id}")
        row.discord_event_id = discord_event_id
        self.session.flush()
        self._commit_if_auto()
