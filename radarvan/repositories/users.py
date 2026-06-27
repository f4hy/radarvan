"""User repository (Discord-authenticated community members)."""

from sqlalchemy import select

from ..db import User

from .base import BaseRepo


class UserRepo(BaseRepo):
    """Operations on User accounts (login identity + claimed in-game name)."""

    def get_by_id(self, user_id: int) -> User | None:
        return self.session.get(User, user_id)

    def get_by_discord_id(self, discord_id: str) -> User | None:
        return self.session.scalars(
            select(User).where(User.discord_id == discord_id)
        ).one_or_none()

    def get_by_player_name(self, player_name: str) -> User | None:
        return self.session.scalars(
            select(User).where(User.player_name == player_name)
        ).one_or_none()

    def list_claimed_player_names(self) -> list[str]:
        """In-game names that have an associated account, sorted."""
        rows = self.session.scalars(
            select(User.player_name)
            .where(User.player_name.is_not(None))
            .order_by(User.player_name)
        ).all()
        return [name for name in rows if name]

    def ids_for_player_names(self, names: list[str]) -> list[int]:
        """User ids for the given claimed in-game names (missing names ignored)."""
        if not names:
            return []
        return list(
            self.session.scalars(
                select(User.id).where(User.player_name.in_(names))
            ).all()
        )

    def upsert_discord_user(
        self, discord_id: str, username: str, avatar: str | None
    ) -> User:
        """Create the account on first login, else refresh its Discord profile."""
        user = self.get_by_discord_id(discord_id)
        if user is None:
            user = User(
                discord_id=discord_id,
                discord_username=username,
                discord_avatar=avatar,
            )
            self.session.add(user)
        else:
            user.discord_username = username
            user.discord_avatar = avatar
        self.session.flush()
        self._commit_if_auto()
        return user

    def set_player_name(self, user: User, player_name: str) -> User:
        """Assign the in-game name claimed by this user."""
        user.player_name = player_name
        self._commit_if_auto()
        return user
