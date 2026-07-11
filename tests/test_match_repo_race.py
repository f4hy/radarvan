"""`MatchRepo.register_match` under the concurrent-upload race.

Both players' clients upload their own recording of the same match when it
ends, and the files aren't byte-identical, so both requests get past the
hash-dedup check and race into `register_match`. This reproduces the race
deterministically: two sessions on the same DB, interleaved so both do their
"does this match exist?" check before either has inserted, then both attempt
the insert. See `radarvan/repositories/matches.py`.
"""

from datetime import datetime, UTC

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from radarvan.db import Match, MatchPlayer
from radarvan.repositories.matches import MatchRepo


@pytest.fixture
def engine():
    engine = create_engine("sqlite://")
    Match.__table__.create(engine)
    MatchPlayer.__table__.create(engine)
    return engine


def _match(match_id: int) -> Match:
    return Match(
        match_id=match_id,
        json_s3_uri=f"s3://bucket/{match_id}.json",
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        map="Tournament Desert",
        winning_team_id=1,
        duration_minutes=12.5,
        filename=f"{match_id}.rep",
    )


def test_first_registration_creates_the_match(engine) -> None:
    with Session(engine) as session:
        repo = MatchRepo(session, auto_commit=True)
        match, created = repo.register_match(_match(1))
        assert created is True
        assert match.match_id == 1


def test_second_registration_after_commit_returns_existing(engine) -> None:
    # Sequential (non-racing) case: the second call's existence check already
    # sees the first call's committed row, so it takes the early-return path.
    with Session(engine) as session_a:
        MatchRepo(session_a, auto_commit=True).register_match(_match(1))

    with Session(engine) as session_b:
        match, created = MatchRepo(session_b, auto_commit=True).register_match(
            _match(1)
        )
        assert created is False
        assert match.match_id == 1


def _repo_racing_another_insert(engine, monkeypatch, match_id: int) -> MatchRepo:
    """A MatchRepo whose existence check has a concurrent winner injected.

    `register_match`'s only race window is between its own `session.get`
    existence check and its `flush`/`commit` of the insert. To reproduce that
    deterministically (no real threads, and sqlite has no MVCC snapshot to
    fool a second `get` the way Postgres does) we patch that exact `get` call:
    the moment it reports "no existing row", a second session commits one for
    real, so the subsequent flush hits the actual unique-constraint conflict.
    """
    session = Session(engine)
    original_get = session.get

    def racing_get(model: type, ident: object, *args: object, **kwargs: object):
        result = original_get(model, ident, *args, **kwargs)
        if model is Match and ident == match_id and result is None:
            with Session(engine) as other:
                MatchRepo(other, auto_commit=True).register_match(_match(match_id))
        return result

    monkeypatch.setattr(session, "get", racing_get)
    return MatchRepo(session, auto_commit=True)


def test_concurrent_registration_is_deduplicated_not_raised(
    engine, monkeypatch
) -> None:
    # Simulates the real race: another request's session commits the same
    # match_id in the instant between our existence check reporting "not
    # found" and our own insert. register_match must catch the resulting
    # IntegrityError and return the row the other request created, not raise.
    repo = _repo_racing_another_insert(engine, monkeypatch, match_id=1)

    match, created = repo.register_match(_match(1))

    assert created is False
    assert match.match_id == 1


def test_concurrent_registration_leaves_exactly_one_row(engine, monkeypatch) -> None:
    repo = _repo_racing_another_insert(engine, monkeypatch, match_id=1)

    repo.register_match(_match(1))

    with Session(engine) as verify:
        assert verify.query(Match).filter_by(match_id=1).count() == 1
