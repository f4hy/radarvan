"""MatchupCommentaryRepo: durable cache round-trip and upsert behavior.

Same in-memory-SQLite pattern as test_match_repo_race.py - a real Session
against a real (if minimal) schema, no mocking of SQLAlchemy itself.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from radarvan.db import MatchupCommentaryCache
from radarvan.repositories.commentary import MatchupCommentaryRepo


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
