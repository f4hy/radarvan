"""Map-vote repository: per-player-count votes and vetoes.

Limits are enforced here (not in the schema): a user may cast at most
``VOTE_LIMIT`` votes and ``VETO_LIMIT`` vetoes per player count. A map can be
voted or vetoed but not both - setting one replaces the other on that map.
"""

from sqlalchemy import func, select

from ..db import MapVote

from .base import BaseRepo

VOTE_LIMIT = 10
VETO_LIMIT = 4
_CHOICES = ("vote", "veto")


class VoteLimitExceeded(Exception):
    """Raised when a user tries to exceed their vote/veto allowance."""

    def __init__(self, choice: str, limit: int):
        self.choice = choice
        self.limit = limit
        super().__init__(f"You can {choice} at most {limit} maps for this player count")


class MapVoteRepo(BaseRepo):
    """Operations on per-player-count map votes/vetoes."""

    def get_choices(self, user_id: int, player_count: int) -> dict[str, str]:
        """Return {map_name: choice} for this user and player count."""
        rows = self.session.scalars(
            select(MapVote).where(
                MapVote.user_id == user_id,
                MapVote.player_count == player_count,
            )
        ).all()
        return {row.map_name: row.choice for row in rows}

    def tally(
        self, player_count: int, user_ids: list[int] | None = None
    ) -> dict[str, tuple[int, int]]:
        """Aggregate {map_name: (votes, vetoes)} for a count.

        When ``user_ids`` is given, only those users' votes are counted (an empty
        list yields an empty tally).
        """
        stmt = (
            select(MapVote.map_name, MapVote.choice, func.count())
            .where(MapVote.player_count == player_count)
            .group_by(MapVote.map_name, MapVote.choice)
        )
        if user_ids is not None:
            stmt = stmt.where(MapVote.user_id.in_(user_ids))
        rows = self.session.execute(stmt).all()
        result: dict[str, tuple[int, int]] = {}
        for map_name, choice, count in rows:
            votes, vetoes = result.get(map_name, (0, 0))
            result[map_name] = (count, vetoes) if choice == "vote" else (votes, count)
        return result

    def _count(self, user_id: int, player_count: int, choice: str) -> int:
        return (
            self.session.scalar(
                select(func.count())
                .select_from(MapVote)
                .where(
                    MapVote.user_id == user_id,
                    MapVote.player_count == player_count,
                    MapVote.choice == choice,
                )
            )
            or 0
        )

    def set_choice(
        self, user_id: int, player_count: int, map_name: str, choice: str | None
    ) -> dict[str, str]:
        """Set (or clear, when ``choice`` is None) a user's pick for one map.

        Enforces the per-choice limit; raises VoteLimitExceeded if exceeded.
        Returns the user's full {map_name: choice} map afterward.
        """
        if choice is not None and choice not in _CHOICES:
            raise ValueError(f"invalid choice {choice!r}")

        row = self.session.scalar(
            select(MapVote).where(
                MapVote.user_id == user_id,
                MapVote.player_count == player_count,
                MapVote.map_name == map_name,
            )
        )
        current = row.choice if row is not None else None
        if choice == current:
            return self.get_choices(user_id, player_count)

        if choice is None:
            if row is not None:
                self.session.delete(row)
        else:
            # Switching to a new choice on this map adds one to that choice's
            # tally (this map is not currently that choice, since choice != current).
            limit = VOTE_LIMIT if choice == "vote" else VETO_LIMIT
            if self._count(user_id, player_count, choice) >= limit:
                raise VoteLimitExceeded(choice, limit)
            if row is not None:
                row.choice = choice
            else:
                self.session.add(
                    MapVote(
                        user_id=user_id,
                        player_count=player_count,
                        map_name=map_name,
                        choice=choice,
                    )
                )
        self.session.flush()
        self._commit_if_auto()
        return self.get_choices(user_id, player_count)
