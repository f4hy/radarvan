"""Persistence for Discord-authenticated user accounts.

Small session-scoped helpers rather than a full repository — auth has a handful
of straightforward queries and doesn't need to join the ReplayManager facade.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import User


def get_user_by_id(session: Session, user_id: int) -> User | None:
    return session.get(User, user_id)


def get_user_by_discord_id(session: Session, discord_id: str) -> User | None:
    return session.scalars(
        select(User).where(User.discord_id == discord_id)
    ).one_or_none()


def get_user_by_player_name(session: Session, player_name: str) -> User | None:
    return session.scalars(
        select(User).where(User.player_name == player_name)
    ).one_or_none()


def upsert_discord_user(
    session: Session, discord_id: str, username: str, avatar: str | None
) -> User:
    """Create the account on first login, else refresh its Discord profile.

    Mutating the managed ORM entity is the intended persistence operation here;
    the returned object is the live, session-attached row.
    """
    user = get_user_by_discord_id(session, discord_id)
    if user is None:
        user = User(
            discord_id=discord_id,
            discord_username=username,
            discord_avatar=avatar,
        )
        session.add(user)
    else:
        user.discord_username = username
        user.discord_avatar = avatar
    session.flush()
    return user


def set_player_name(session: Session, user: User, player_name: str) -> User:
    """Assign the in-game name claimed by this user."""
    user.player_name = player_name
    session.flush()
    return user
