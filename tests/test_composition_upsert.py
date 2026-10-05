"""`MatchRepo.compute_and_save_composition` against PostgreSQL: concurrent saves."""

import threading
from collections.abc import Iterator
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from radarvan.db import (
    Base,
    Match,
    MatchCompostion,
    MatchPlayer,
    ParsedReplayJson,
    ReplayFile,
    sqlalchemy_url,
)
from radarvan.repositories.matches import MatchRepo

MATCH_ID = 689421214


def _player(name: str, team_id: int, color: str) -> MatchPlayer:
    return MatchPlayer(
        player_name=name,
        general_id=1,
        team_id=team_id,
        color=color,
        is_winner=team_id == 1,
    )


@pytest.fixture
def engine(postgres_db_url: str) -> Iterator[Engine]:
    engine = create_engine(sqlalchemy_url(postgres_db_url))
    url = f"https://replays/{MATCH_ID}.rep"
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            session.add_all(
                [
                    ReplayFile(
                        original_url=url,
                        s3_uri=f"s3://bucket/{MATCH_ID}.rep",
                        player_id="p",
                        source_date=date(2026, 10, 4),
                    ),
                    ParsedReplayJson(
                        json_s3_uri=f"s3://bucket/{MATCH_ID}.json",
                        match_id=MATCH_ID,
                        replay_file_url=url,
                        game_timestamp=datetime(2026, 10, 4),
                    ),
                    Match(
                        match_id=MATCH_ID,
                        json_s3_uri=f"s3://bucket/{MATCH_ID}.json",
                        timestamp=datetime(2026, 10, 4, tzinfo=UTC),
                        map="Tournament Desert",
                        winning_team_id=1,
                        duration_minutes=12.5,
                        filename=f"{MATCH_ID}.rep",
                        players=[_player("A", 1, "Red"), _player("B", 2, "Blue")],
                    ),
                ]
            )
            session.commit()
        yield engine
    finally:
        engine.dispose()


def _composition_rows(engine: Engine) -> list[MatchCompostion]:
    with Session(engine) as session:
        return list(session.scalars(select(MatchCompostion)).all())


def test_concurrent_uploads_both_save_the_composition(engine: Engine) -> None:
    # Session A inserts but hasn't committed when B saves, the window in which
    # merge()'s SELECT-then-INSERT raised UniqueViolation for B.
    errors: list[BaseException] = []
    with Session(engine) as first:
        MatchRepo(first, auto_commit=False).compute_and_save_composition(MATCH_ID)
        first.flush()

        def second() -> None:
            try:
                with Session(engine) as session:
                    MatchRepo(session).compute_and_save_composition(MATCH_ID)
            except BaseException as e:
                errors.append(e)

        racer = threading.Thread(target=second)
        racer.start()
        # B blocks on A's row lock until A commits.
        racer.join(timeout=0.5)
        assert racer.is_alive()
        first.commit()
        racer.join(timeout=10)

    assert not racer.is_alive()
    assert errors == []
    rows = _composition_rows(engine)
    assert [(r.match_id, r.is_1v1) for r in rows] == [(MATCH_ID, True)]


def test_recompute_updates_an_existing_composition(engine: Engine) -> None:
    with Session(engine) as session:
        repo = MatchRepo(session)
        repo.compute_and_save_composition(MATCH_ID)
        match = session.get_one(Match, MATCH_ID)
        assert match.composition is not None and match.composition.is_1v1

        match.players.extend([_player("C", 1, "Green"), _player("D", 2, "Gold")])
        session.commit()
        repo.compute_and_save_composition(MATCH_ID)

        assert match.composition is not None
        assert not match.composition.is_1v1
        assert match.composition.total_players == 4

    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(MatchCompostion)) == 1
