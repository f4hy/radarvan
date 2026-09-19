"""MatchupCommentaryRepo: durable cache round-trip and upsert behavior.

Same in-memory-SQLite pattern as test_match_repo_race.py - a real Session
against a real (if minimal) schema, no mocking of SQLAlchemy itself.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from radarvan.db import MatchBlurbCache, MatchupCommentaryCache
from radarvan.repositories.commentary import MatchBlurbRepo, MatchupCommentaryRepo


@pytest.fixture
def engine():  # type: ignore[no-untyped-def]
    engine = create_engine("sqlite://")
    MatchupCommentaryCache.__table__.create(engine)
    return engine


def test_get_cached_commentary_is_none_on_miss(engine) -> None:  # type: ignore[no-untyped-def]
    with Session(engine) as session:
        repo = MatchupCommentaryRepo(session)
        assert repo.get_cached_commentary("Alice", "Bob", "Winners Round 1") is None


def test_save_then_get_round_trips(engine) -> None:  # type: ignore[no-untyped-def]
    with Session(engine) as session:
        repo = MatchupCommentaryRepo(session)
        repo.save_commentary("Alice", "Bob", "Winners Round 1", "**Hype!**", "gemini")
        assert (
            repo.get_cached_commentary("Alice", "Bob", "Winners Round 1")
            == "**Hype!**"
        )


def test_different_round_name_is_a_different_cache_key(engine) -> None:  # type: ignore[no-untyped-def]
    with Session(engine) as session:
        repo = MatchupCommentaryRepo(session)
        repo.save_commentary("Alice", "Bob", "Winners Round 1", "**Round 1 hype.**", "gemini")
        assert repo.get_cached_commentary("Alice", "Bob", "Losers Final") is None
        assert (
            repo.get_cached_commentary("Alice", "Bob", "Winners Round 1")
            == "**Round 1 hype.**"
        )


def test_save_commentary_upserts_existing_row(engine) -> None:  # type: ignore[no-untyped-def]
    with Session(engine) as session:
        repo = MatchupCommentaryRepo(session)
        repo.save_commentary("Alice", "Bob", "Winners Round 1", "**First draft.**", "gemini")
        repo.save_commentary("Alice", "Bob", "Winners Round 1", "**Regenerated.**", "anthropic")
        assert (
            repo.get_cached_commentary("Alice", "Bob", "Winners Round 1")
            == "**Regenerated.**"
        )


# --- MatchBlurbRepo ------------------------------------------------------------


@pytest.fixture
def blurbs():  # type: ignore[no-untyped-def]
    engine = create_engine("sqlite://")
    MatchBlurbCache.__table__.create(engine)
    with Session(engine) as session:
        yield MatchBlurbRepo(session)


def test_a_match_without_a_blurb_is_absent(blurbs: MatchBlurbRepo) -> None:
    assert blurbs.get_blurbs([1]) == {}


def test_a_saved_blurb_round_trips_and_upserts(blurbs: MatchBlurbRepo) -> None:
    blurbs.save_blurb(7, "First.", "gemini")
    blurbs.save_blurb(7, "Second.", "anthropic")
    assert blurbs.get_blurbs([7]) == {7: "Second."}


def test_get_blurbs_returns_only_the_ids_that_have_one(blurbs: MatchBlurbRepo) -> None:
    blurbs.save_blurb(1, "One.", "gemini")
    blurbs.save_blurb(2, "Two.", "gemini")
    assert blurbs.get_blurbs([2, 3]) == {2: "Two."}
    assert blurbs.get_blurbs([]) == {}
