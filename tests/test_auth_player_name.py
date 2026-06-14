"""A claimed in-game name can't be taken by a second Discord account.

Two layers protect this: the application check in routes.auth.select_player
(returns 409), and the UNIQUE constraint on users.player_name as a backstop
against a race that slips past the check.
"""

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from radarvan.api_types import SelectPlayerRequest
from radarvan.db import User
from radarvan.repositories import UserRepo
from radarvan.routes.auth import select_player


@pytest.fixture
def session() -> Session:
    # In-memory SQLite with just the users table (other tables use
    # postgres-only column types we don't need here).
    engine = create_engine("sqlite://")
    User.__table__.create(engine)
    with Session(engine) as s:
        yield s


def _make_user(session: Session, discord_id: str) -> User:
    user = User(discord_id=discord_id, discord_username=discord_id)
    session.add(user)
    session.flush()
    return user


def test_second_user_cannot_claim_same_name(session: Session) -> None:
    repo = UserRepo(session, auto_commit=False)
    alice = _make_user(session, "alice")
    bob = _make_user(session, "bob")

    # Alice claims "Skip".
    status = select_player(SelectPlayerRequest(player_name="Skip"), alice, repo)
    assert status.user is not None
    assert status.user.player_name == "Skip"

    # Bob tries to claim "Skip" -> rejected with 409.
    with pytest.raises(HTTPException) as exc:
        select_player(SelectPlayerRequest(player_name="Skip"), bob, repo)
    assert exc.value.status_code == 409
    assert session.get(User, bob.id).player_name is None


def test_same_user_can_reselect_their_own_name(session: Session) -> None:
    repo = UserRepo(session, auto_commit=False)
    alice = _make_user(session, "alice")
    select_player(SelectPlayerRequest(player_name="Skip"), alice, repo)
    # Re-confirming the same name is fine (existing.id == user.id).
    status = select_player(SelectPlayerRequest(player_name="Skip"), alice, repo)
    assert status.user is not None
    assert status.user.player_name == "Skip"


def test_db_unique_constraint_is_the_backstop(session: Session) -> None:
    # Even bypassing the app check (e.g. a race), the DB refuses two rows
    # with the same player_name.
    alice = _make_user(session, "alice")
    bob = _make_user(session, "bob")
    alice.player_name = "Skip"
    bob.player_name = "Skip"
    with pytest.raises(IntegrityError):
        session.flush()
