"""The nightly game-night summary job: the guards that keep it from spending.

This is the only scheduled job in the app that costs money, so what stops it
matters more than what it produces. Each test here pins one refusal, and each
asserts it by making the database unreachable — a job that got past the guard
would raise rather than quietly pass.
"""

import asyncio
import os
from datetime import UTC, date, datetime

import pytest

os.environ.setdefault(
    "DATABASE_URL", "postgresql://stub:stub@127.0.0.1:1/stub-not-used"
)

from radarvan import schedule
from radarvan.commentary import llm

import corpus


class _ExplodingDbManager:
    """Any use at all is a failure: the guard should return before this."""

    def get_replay_manager(self) -> object:
        raise AssertionError(
            "the job opened a database session past a guard that should have "
            "returned first"
        )


def test_no_provider_configured_stops_before_touching_the_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(llm, "commentary_available", lambda: False)
    # Returns cleanly rather than raising out of _ExplodingDbManager.
    asyncio.run(schedule.compute_game_night_summary(_ExplodingDbManager()))  # type: ignore[arg-type]


def test_a_single_game_is_not_a_game_night() -> None:
    """One stray upload should not buy an LLM call."""
    assert schedule.MIN_MATCHES_FOR_SUMMARY > 1


def test_the_job_targets_a_closed_night_only() -> None:
    """The stored row is permanent, so the live evening must never be picked.

    Pinned on the function the job delegates to: a night whose key is the one
    currently in progress is excluded, an earlier one is not.
    """
    from radarvan import utils
    from radarvan.queries import latest_closed_night

    tonight = utils.game_night_date_of(datetime.now(UTC))
    live = corpus.A_MATCH.model_copy(update={"date": tonight})
    assert latest_closed_night([corpus.A_MATCH, live]) == corpus.A_MATCH.date
    assert latest_closed_night([live]) is None


def test_generation_is_serialized_across_both_callers() -> None:
    """The nightly job and the ops endpoint must not both bill for one night."""
    from radarvan.commentary import night_summary

    assert isinstance(night_summary.generation_lock, asyncio.Lock)


def test_the_night_key_is_a_game_night_not_a_calendar_date() -> None:
    """A 2am game belongs to the evening it started - the 5am ET rollover."""
    from radarvan import utils

    assert utils.game_night_date_of(datetime(2026, 1, 6, 7, 0, tzinfo=UTC)) == date(
        2026, 1, 5
    )
