"""Both recomputation entry points publish the same complete snapshot."""

import asyncio
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import event

from radarvan import computed_stats, general_stats, opening_book, schedule, superlatives
from radarvan.api_types import (
    General,
    Statistic,
    SuperlativeData,
    SuperlativePlayerSummary,
    Team,
)
from radarvan.db import ComputedStatistic
from radarvan.db_utils import DatabaseManager, ReplayManager
from radarvan.repositories.stats import StatsRepo
from radarvan.routes import superlatives as routes

import corpus


@pytest.fixture(params=["sqlite", "postgres"])
def manager(
    request: pytest.FixtureRequest, tmp_path: Path
) -> Iterator[DatabaseManager]:
    url = (
        request.getfixturevalue("postgres_db_url")
        if request.param == "postgres"
        else f"sqlite:///{tmp_path / 'stats.db'}"
    )
    manager = DatabaseManager(url)
    try:
        ComputedStatistic.__table__.create(manager.engine)
        yield manager
    finally:
        manager.engine.dispose()


@pytest.fixture
def inputs(monkeypatch: pytest.MonkeyPatch, manager: DatabaseManager) -> AsyncMock:
    game = corpus.match(1, day=5)
    player = game.players[0]
    detail = SuperlativeData(
        match_id=game.id,
        apms=[],
        player_summary=[
            SuperlativePlayerSummary(
                name=player.name,
                color=player.color,
                won=player.won,
                money_spent=0,
                units_created_count=0,
                buildings_built_count=0,
                value_destroyed=1500,
                value_lost=500,
            )
        ],
        upgrade_counts={},
        total_units_killed=0,
        total_buildings_killed=0,
        total_xp=0,
        match_money_spent=0,
        player_money_collected={},
    )
    winnerless = corpus.match(2, day=6, winner=Team.NONE)
    monkeypatch.setattr(
        computed_stats, "competitive_matches", lambda _: {1: game, 2: winnerless}
    )

    async def details(ids, db_manager):
        assert ids == [1]
        assert db_manager is manager
        return [detail]

    async def tallies(games, db_manager):
        assert [g.id for g in games] == [1]
        assert db_manager is manager
        return {
            (General(player.general), ("Barracks",)): opening_book._Tally(
                games=20, wins=12
            )
        }

    monkeypatch.setattr(superlatives, "load_many_superlative_data", details)
    monkeypatch.setattr(opening_book, "load_opening_tallies", tallies)
    # Reset the lock between asyncio.run loops; contention binds it to a loop.
    monkeypatch.setattr(computed_stats, "recompute_lock", asyncio.Lock())
    monkeypatch.setattr(computed_stats, "_queued", False)
    monkeypatch.setattr(routes, "db_manager", manager)
    notify = AsyncMock()
    monkeypatch.setattr(computed_stats, "notify_async", notify)
    return notify


async def _manual() -> None:
    tasks = BackgroundTasks()
    assert await routes.recompute_superlatives(tasks) == {"status": "started"}
    await tasks()


def _stored(manager: DatabaseManager) -> list[Statistic]:
    with manager.get_session() as session:
        return StatsRepo(session).get_computed_stats()


def _seed(manager: DatabaseManager, *, every_kind: bool = False) -> list[Statistic]:
    old = [
        Statistic(
            stat_name="previous snapshot", value=123, date_computed=date(2020, 1, 1)
        )
    ]
    if every_kind:
        old += [
            Statistic(
                stat_name=f"{general_stats.GENERAL_VALUE_STAT_PREFIX}destroyed",
                value=1.0,
                player="0",
                date_computed=date(2020, 1, 1),
            ),
            Statistic(
                stat_name=f"{opening_book.OPENING_STAT_PREFIX}0",
                value='{"general": 0, "total_games": 1, "openings": []}',
                date_computed=date(2020, 1, 1),
            ),
        ]
    with manager.get_session() as session:
        StatsRepo(session, auto_commit=False).replace_computed_stats(old)
    return old


def _identity(
    stats: list[Statistic],
) -> list[tuple[str, object, str | None, int | None]]:
    """Rows without date_computed, which two runs stamp from separate now() calls."""
    return [(s.stat_name, s.value, s.player, s.match_id) for s in stats]


def _messages(notify: AsyncMock) -> list[str]:
    return [call.args[0] for call in notify.await_args_list]


def test_manual_then_scheduled_retains_every_projection(manager, inputs) -> None:
    asyncio.run(_manual())
    manual = _stored(manager)
    asyncio.run(schedule.compute_and_save_superlatives(manager))
    scheduled = _stored(manager)
    assert _identity(scheduled) == _identity(manual)
    assert general_stats.value_stats_from_computed(scheduled) == {
        General.USA: (1500, 500)
    }
    book = opening_book.opening_book_from_computed(scheduled)
    assert len(book.generals) == 1
    assert book.generals[0].openings[0].buildings == ["Barracks"]
    assert book.generals[0].total_games == 20
    with manager.get_session() as session:
        public = routes.get_superlatives(ReplayManager(session))
    assert public.stats
    assert all(not stat.stat_name.startswith("__") for stat in public.stats)
    assert {stat.date_computed for stat in scheduled} == {public.computed_at}
    # The first run finds an empty table (stale), so it announces both ends; the
    # second is fresh and stays quiet.
    started, finished = _messages(inputs)
    assert started.startswith("Computing records")
    assert finished.startswith("Recomputed")


@pytest.mark.parametrize("entry", ["manual", "scheduled"])
@pytest.mark.parametrize("failure", ["load", "compute", "publish"])
def test_failed_refresh_preserves_snapshot(
    manager, inputs, monkeypatch, entry, failure
) -> None:
    old = _seed(manager)
    if failure == "load":
        monkeypatch.setattr(
            opening_book,
            "load_opening_tallies",
            AsyncMock(side_effect=RuntimeError("refresh failed")),
        )
    elif failure == "compute":

        def fail(*args):
            raise RuntimeError("refresh failed")

        monkeypatch.setattr(general_stats, "general_value_stats", fail)
    else:

        @event.listens_for(manager.SessionLocal, "after_flush_postexec")
        def fail(*args):
            raise RuntimeError("refresh failed")

    with pytest.raises(RuntimeError, match="refresh failed"):
        asyncio.run(
            _manual()
            if entry == "manual"
            else schedule.compute_and_save_superlatives(manager)
        )
    assert _stored(manager) == old
    # The run announced its start (the seeded snapshot is stale) but never its
    # completion - a hung or failed refresh has to stay visible.
    assert all(not m.startswith("Recomputed") for m in _messages(inputs))
    assert not computed_stats.recompute_pending()


def test_failed_loader_cancels_its_sibling(manager, inputs, monkeypatch) -> None:
    """A survivor outliving the lock would overlap the next run's corpus sweep."""

    async def exercise():
        cancelled = asyncio.Event()

        async def never_finishes(*args):
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancelled.set()
                raise

        async def fails(*args):
            raise RuntimeError("loader failed")

        monkeypatch.setattr(superlatives, "load_many_superlative_data", never_finishes)
        monkeypatch.setattr(opening_book, "load_opening_tallies", fails)
        with pytest.raises(RuntimeError, match="loader failed"):
            await computed_stats.recompute(manager)
        assert cancelled.is_set()
        assert not computed_stats.recompute_pending()

    asyncio.run(exercise())


def test_manual_and_scheduled_runs_share_exclusion(
    manager, inputs, monkeypatch
) -> None:
    original = opening_book.load_opening_tallies

    async def exercise():
        started = asyncio.Event()
        release = asyncio.Event()
        calls = 0

        async def held_tallies(*args):
            nonlocal calls
            calls += 1
            started.set()
            await release.wait()
            return await original(*args)

        monkeypatch.setattr(opening_book, "load_opening_tallies", held_tallies)
        manual = asyncio.create_task(_manual())
        await asyncio.wait_for(started.wait(), timeout=5)
        try:
            with pytest.raises(HTTPException) as exc:
                await routes.recompute_superlatives(BackgroundTasks())
            assert exc.value.status_code == 409
            # The nightly job skips outright rather than queueing behind it.
            await asyncio.wait_for(
                schedule.compute_and_save_superlatives(manager), timeout=5
            )
            assert calls == 1
        finally:
            release.set()
            await asyncio.wait_for(manual, timeout=10)
        assert calls == 1
        assert not computed_stats.recompute_pending()

    asyncio.run(exercise())


def test_queued_run_rejects_a_second_trigger_before_it_starts(manager, inputs) -> None:
    """The 409 must hold in the window before BackgroundTasks runs the first run."""

    async def exercise():
        tasks = BackgroundTasks()
        assert await routes.recompute_superlatives(tasks) == {"status": "started"}
        assert not computed_stats.recompute_lock.locked()
        with pytest.raises(HTTPException) as exc:
            await routes.recompute_superlatives(BackgroundTasks())
        assert exc.value.status_code == 409
        await tasks()
        assert not computed_stats.recompute_pending()

    asyncio.run(exercise())


@pytest.mark.parametrize("entry", ["manual", "scheduled"])
@pytest.mark.parametrize(
    ("degradation", "reason"),
    [
        ("empty_corpus", "no competitive matches"),
        ("failed_group", "stat groups failed"),
        ("lost_kind", "opening_book would be emptied"),
    ],
)
def test_degraded_run_preserves_previous_snapshot(
    manager, inputs, monkeypatch, entry, degradation, reason
) -> None:
    """A truncated snapshot raises nothing on its own - refuse to publish it."""
    old = _seed(manager, every_kind=True)
    if degradation == "empty_corpus":
        monkeypatch.setattr(computed_stats, "competitive_matches", lambda _: {})
    elif degradation == "failed_group":

        def fail(*args):
            raise RuntimeError("one bad producer")

        monkeypatch.setattr(superlatives, "get_duo_stats", fail)
    else:
        # An S3 blip that loads no build orders empties the opening book while
        # every other projection still looks healthy.
        async def no_tallies(games, db_manager):
            return {}

        monkeypatch.setattr(opening_book, "load_opening_tallies", no_tallies)

    with pytest.raises(computed_stats.IncompleteSnapshot, match=reason):
        asyncio.run(
            _manual()
            if entry == "manual"
            else schedule.compute_and_save_superlatives(manager)
        )
    assert _stored(manager) == old
    assert not computed_stats.recompute_pending()
