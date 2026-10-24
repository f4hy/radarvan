"""Offline app configuration and opt-in, isolated PostgreSQL test databases.

radarvan.dependencies reads DATABASE_URL at import time (and fails fast when
it's missing - desirable in production), so a placeholder has to be injected
before any test module imports the app. create_engine doesn't connect, so the
URL below is never dialled; setdefault keeps a real value (e.g. the dev
shell's) untouched. The PostgreSQL fixtures here are the one part of the suite
that does open a connection, and they use TEST_POSTGRES_URL instead - never
DATABASE_URL - so they can't reach whatever this placeholder names.
"""

import os
from collections.abc import Iterator
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from radarvan.db import sqlalchemy_url

os.environ.setdefault("DATABASE_URL", "postgresql://localhost:5432/radarvan_test")

_skipped_postgres = 0


@pytest.fixture
def postgres_db_url() -> Iterator[str]:
    global _skipped_postgres
    configured = os.environ.get("TEST_POSTGRES_URL")
    if not configured:
        # Silently dropping a whole tier is how a green run stops meaning
        # anything; CI sets REQUIRE_POSTGRES_TESTS so a broken service container
        # fails the build instead of skipping into a pass.
        if os.environ.get("REQUIRE_POSTGRES_TESTS"):
            pytest.fail("REQUIRE_POSTGRES_TESTS is set but TEST_POSTGRES_URL is not")
        _skipped_postgres += 1
        pytest.skip("Set TEST_POSTGRES_URL to run PostgreSQL integration tests")
    url = make_url(configured)
    if url.get_backend_name() != "postgresql":
        pytest.fail("TEST_POSTGRES_URL must point to PostgreSQL")
    database = f"radarvan_test_{uuid4().hex}"
    admin = create_engine(
        sqlalchemy_url(configured),
        isolation_level="AUTOCOMMIT",
        connect_args={"connect_timeout": 5},
    )
    try:
        with admin.connect() as connection:
            connection.exec_driver_sql(f'CREATE DATABASE "{database}"')
        try:
            yield url.set(database=database).render_as_string(hide_password=False)
        finally:
            # Only the randomly named database created above is removed.
            with admin.connect() as connection:
                connection.exec_driver_sql(f'DROP DATABASE "{database}" WITH (FORCE)')
    finally:
        admin.dispose()


def pytest_terminal_summary(terminalreporter: pytest.TerminalReporter) -> None:
    if _skipped_postgres:
        terminalreporter.write_sep(
            "!",
            f"{_skipped_postgres} PostgreSQL integration tests skipped "
            f"- run `make test-pg` to include them",
            yellow=True,
        )


class BackgroundGeneration:
    """Captures what routes/commentary.py would run on its background thread."""

    def __init__(self) -> None:
        self.spawned: list[tuple[object, object, object]] = []
        self.saved: list[tuple[object, ...]] = []

    def run_all(self) -> None:
        from radarvan.routes import commentary

        spawned, self.spawned = self.spawned, []
        for key, generate, save in spawned:
            commentary._run(key, generate, save)  # type: ignore[arg-type]


@pytest.fixture
def background_generation(monkeypatch: pytest.MonkeyPatch) -> BackgroundGeneration:
    from contextlib import contextmanager

    from radarvan.routes import commentary

    bg = BackgroundGeneration()

    class _Repo:
        def __init__(self, session: object) -> None:
            pass

        def save_commentary(self, *args: object) -> None:
            bg.saved.append(args)

        def save_summary(self, *args: object) -> None:
            bg.saved.append(args)

    class _DbManager:
        @contextmanager
        def get_session(self) -> Iterator[None]:
            yield None

    monkeypatch.setattr(commentary, "_in_flight", set())
    monkeypatch.setattr(commentary, "_failed_at", {})
    monkeypatch.setattr(commentary, "_spawn", lambda *args: bg.spawned.append(args))
    monkeypatch.setattr(commentary, "db_manager", _DbManager())
    monkeypatch.setattr(commentary, "MatchupCommentaryRepo", _Repo)
    monkeypatch.setattr(commentary, "BracketSummaryRepo", _Repo)
    return bg
