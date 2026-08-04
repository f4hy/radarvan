"""Community "who wins this match" prediction repository.

One row per (tournament, match, user) - a fun hype feature, not the
authoritative result (see BracketRepo/BracketMatchState for that).
"""

from sqlalchemy import func, select

from ..db import BracketPrediction, User

from .base import BaseRepo


class BracketPredictionRepo(BaseRepo):
    def tally(self, tournament_id: int, match_id: str) -> dict[str, int]:
        """{predicted_winner: count} for one match."""
        stmt = (
            select(BracketPrediction.predicted_winner, func.count())
            .where(
                BracketPrediction.tournament_id == tournament_id,
                BracketPrediction.match_id == match_id,
            )
            .group_by(BracketPrediction.predicted_winner)
        )
        result: dict[str, int] = {}
        for predicted_winner, count in self.session.execute(stmt).all():
            result[predicted_winner] = count  # noqa: PERF403 (mypy rejects the dict()/comprehension form here - Row isn't seen as tuple[str, int])
        return result

    def tally_all(self, tournament_id: int) -> dict[str, dict[str, int]]:
        """{match_id: {predicted_winner: count}} for every match in the tournament."""
        stmt = (
            select(
                BracketPrediction.match_id,
                BracketPrediction.predicted_winner,
                func.count(),
            )
            .where(BracketPrediction.tournament_id == tournament_id)
            .group_by(BracketPrediction.match_id, BracketPrediction.predicted_winner)
        )
        result: dict[str, dict[str, int]] = {}
        for match_id, predicted_winner, count in self.session.execute(stmt).all():
            result.setdefault(match_id, {})[predicted_winner] = count
        return result

    def all_picks_with_names(self, tournament_id: int) -> list[tuple[str, str, str]]:
        """(match_id, predicted_winner, display_name) for every prediction in
        the tournament - display_name prefers the user's claimed in-game
        player_name (what the rest of the site calls them) and falls back to
        their Discord username for users who haven't claimed one yet.
        Correctness against the resolved winner is computed by the caller
        (bracket.py owns match resolution, not this repo).
        """
        stmt = (
            select(
                BracketPrediction.match_id,
                BracketPrediction.predicted_winner,
                func.coalesce(User.player_name, User.discord_username),
            )
            .join(User, User.id == BracketPrediction.user_id)
            .where(BracketPrediction.tournament_id == tournament_id)
        )
        return [
            (match_id, predicted_winner, display_name)
            for match_id, predicted_winner, display_name in self.session.execute(
                stmt
            ).all()
        ]

    def get_user_picks(self, tournament_id: int, user_id: int) -> dict[str, str]:
        """{match_id: predicted_winner} for this user's picks in the tournament."""
        rows = self.session.scalars(
            select(BracketPrediction).where(
                BracketPrediction.tournament_id == tournament_id,
                BracketPrediction.user_id == user_id,
            )
        ).all()
        return {row.match_id: row.predicted_winner for row in rows}

    def set_pick(
        self,
        tournament_id: int,
        match_id: str,
        user_id: int,
        predicted_winner: str | None,
    ) -> None:
        """Set (or clear, when ``predicted_winner`` is None) a user's pick."""
        row = self.session.scalar(
            select(BracketPrediction).where(
                BracketPrediction.tournament_id == tournament_id,
                BracketPrediction.match_id == match_id,
                BracketPrediction.user_id == user_id,
            )
        )
        if predicted_winner is None:
            if row is not None:
                self.session.delete(row)
        elif row is not None:
            row.predicted_winner = predicted_winner
        else:
            self.session.add(
                BracketPrediction(
                    tournament_id=tournament_id,
                    match_id=match_id,
                    user_id=user_id,
                    predicted_winner=predicted_winner,
                )
            )
        self.session.flush()
        self._commit_if_auto()
