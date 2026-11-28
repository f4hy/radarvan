"""The billed game-night recap routes answer with a plan and write in the background.

``night_summary.generate_summary`` is replaced in every test, so none can reach a provider.
"""

import asyncio
from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from radarvan import game_night, queries
from radarvan.commentary import llm, night_summary
from radarvan.db import GameNightSummaryCache
from radarvan.repositories import GameNightSummaryRepo
from radarvan.routes import game_night as routes
from radarvan.run_slot import RunSlot

import corpus
from corpus import BACK_AND_FORTH


@pytest.fixture
def repo():  # type: ignore[no-untyped-def]
    engine = create_engine("sqlite://")
    GameNightSummaryCache.__table__.create(engine)
    with Session(engine) as session:
        yield GameNightSummaryRepo(session)


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> list[object]:
    seen: list[object] = []

    def fake(recap, games):  # type: ignore[no-untyped-def]
        seen.append(recap.date)
        return f"Recap {len(seen)}."

    async def no_notify(message: str) -> None:
        pass

    monkeypatch.setattr(night_summary, "generate_summary", fake)
    monkeypatch.setattr(llm, "active_provider", lambda: "test")
    monkeypatch.setattr(llm, "commentary_available", lambda: True)
    monkeypatch.setattr(routes, "notify_async", no_notify)
    monkeypatch.setattr(night_summary, "manual_run", RunSlot())
    return seen


def _night_on(day: int, ids: range) -> queries.NightGames:
    games = [corpus.match(i, day=day) for i in ids]
    details = {i: corpus.curve_details(i, BACK_AND_FORTH) for i in ids}
    return queries.NightGames(
        recap=game_night.build_recap(games[0].date, games, games, details, []),
        played=games,
        counted=games,
        details_by_id=details,
    )


def _backfill(
    monkeypatch: pytest.MonkeyPatch,
    repo: GameNightSummaryRepo,
    nights: list[queries.NightGames],
    **kwargs: object,
):  # type: ignore[no-untyped-def]
    by_date = {n.recap.date: n for n in nights}

    async def build(night, all_games, competitive, db_manager):  # type: ignore[no-untyped-def]
        return by_date[night]

    @contextmanager
    def replay_manager():  # type: ignore[no-untyped-def]
        yield SimpleNamespace(session=repo.session)

    monkeypatch.setattr(queries, "build_night_recap", build)
    monkeypatch.setattr(
        routes, "db_manager", SimpleNamespace(get_replay_manager=replay_manager)
    )
    all_games = [g for n in nights for g in n.played]
    tasks = BackgroundTasks()

    async def run():  # type: ignore[no-untyped-def]
        report = await routes.backfill_game_night_summaries(
            all_games,
            [],
            tasks,
            summaries=repo,
            **{"days": 400, **kwargs},  # type: ignore[arg-type]
        )
        return report, len(tasks.tasks), tasks

    report, queued_tasks, tasks = asyncio.run(run())
    asyncio.run(tasks())
    return report, queued_tasks


def test_the_backfill_answers_with_the_plan_then_writes_newest_first(
    monkeypatch: pytest.MonkeyPatch, calls: list[object], repo: GameNightSummaryRepo
) -> None:
    older, newer = _night_on(5, range(1, 3)), _night_on(6, range(11, 13))
    report, queued_tasks = _backfill(monkeypatch, repo, [older, newer], max_to_update=1)
    assert [(n.date, n.outcome) for n in report.nights] == [
        (newer.recap.date, "queued"),
        (older.recap.date, "not_attempted"),
    ]
    assert (report.queued, report.remaining, queued_tasks) == (1, 1, 1)
    assert calls == [newer.recap.date]
    assert repo.has_night_summary(newer.recap.date)
    assert not night_summary.manual_run.held


def test_nothing_eligible_queues_no_task_and_holds_no_slot(
    monkeypatch: pytest.MonkeyPatch, calls: list[object], repo: GameNightSummaryRepo
) -> None:
    lonely = _night_on(5, range(1, 2))
    report, queued_tasks = _backfill(monkeypatch, repo, [lonely], max_to_update=3)
    assert [n.outcome for n in report.nights] == ["too_few_games"]
    assert (report.queued, queued_tasks) == (0, 0)
    assert calls == []
    assert not night_summary.manual_run.held


def test_a_provider_error_frees_the_slot_for_the_next_run(
    monkeypatch: pytest.MonkeyPatch, calls: list[object], repo: GameNightSummaryRepo
) -> None:
    def down(recap, games):  # type: ignore[no-untyped-def]
        raise llm.CommentaryGenerationError("provider down")

    monkeypatch.setattr(night_summary, "generate_summary", down)
    night = _night_on(5, range(1, 3))
    _backfill(monkeypatch, repo, [night], max_to_update=1)
    assert not repo.has_night_summary(night.recap.date)
    assert not night_summary.manual_run.held


def test_a_run_in_flight_turns_the_next_request_away(
    monkeypatch: pytest.MonkeyPatch, calls: list[object], repo: GameNightSummaryRepo
) -> None:
    assert night_summary.manual_run.try_reserve()
    with pytest.raises(HTTPException) as busy:
        _backfill(monkeypatch, repo, [_night_on(5, range(1, 3))], max_to_update=1)
    assert busy.value.status_code == 409
    assert calls == []
