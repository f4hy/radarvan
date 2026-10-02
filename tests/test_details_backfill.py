"""`MatchDetailsRepo` against PostgreSQL: JSON round trips and stale-row listing."""

import json
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from radarvan.api_types import MatchDetails, MatchPowers, PlayerPowers
from radarvan.db import (
    Base,
    Match,
    MatchDetailsCache,
    ParsedReplayJson,
    ReplayFile,
    sqlalchemy_url,
)
from radarvan.repositories.details import MatchDetailsRepo


def _match(match_id: int, day: int) -> list[object]:
    url = f"https://replays/{match_id}.rep"
    return [
        ReplayFile(
            original_url=url,
            s3_uri=f"s3://bucket/{match_id}.rep",
            player_id="p",
            source_date=date(2026, 1, day),
        ),
        ParsedReplayJson(
            json_s3_uri=f"s3://bucket/{match_id}.json",
            match_id=match_id,
            replay_file_url=url,
            game_timestamp=datetime(2026, 1, day),
        ),
        Match(
            match_id=match_id,
            json_s3_uri=f"s3://bucket/{match_id}.json",
            timestamp=datetime(2026, 1, day, tzinfo=UTC),
            map="Tournament Desert",
            winning_team_id=1,
            duration_minutes=12.5,
            filename=f"{match_id}.rep",
        ),
    ]


def _row(match_id: int, version: str) -> MatchDetailsCache:
    return MatchDetailsCache(
        match_id=match_id, version=version, data={}, computed_at=datetime.now(UTC)
    )


def test_stale_details_are_missing_or_old_rows_newest_first(
    postgres_db_url: str,
) -> None:
    engine = create_engine(sqlalchemy_url(postgres_db_url))
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            for i in (1, 2, 3, 4):
                session.add_all(_match(i, day=i))
                session.flush()
            session.add_all([_row(1, "v2"), _row(2, "v1"), _row(4, "v1")])
            session.commit()
            repo = MatchDetailsRepo(session)

            assert repo.list_stale_details_match_ids("v2", limit=10) == [4, 3, 2]
            assert repo.list_stale_details_match_ids("v2", limit=2) == [4, 3]
            assert repo.count_stale_details("v2") == 3
            assert repo.count_stale_details("v1") == 2
    finally:
        engine.dispose()


def test_cached_reads_round_trip_through_pydantic(postgres_db_url: str) -> None:
    raw = json.loads(Path("references/example_api_match_details.json").read_text())
    powers = MatchPowers(
        players=[PlayerPowers(player_name="P1", faction="F", general=1, minutes=12.0)]
    )
    details = MatchDetails.model_validate(raw).model_copy(update={"powers": powers})
    # Storing rounds Minute/Rate (their json serializers), so compare against
    # what was stored rather than the unrounded fixture.
    stored = MatchDetails.model_validate(details.model_dump(mode="json", by_alias=True))
    engine = create_engine(sqlalchemy_url(postgres_db_url))
    try:
        MatchDetailsCache.__table__.create(engine)  # type: ignore[attr-defined]
        with Session(engine) as session:
            repo = MatchDetailsRepo(session)
            repo.save_cached_details(details.match_id, details, "v1")

            assert repo.get_cached_details(details.match_id, "v1") == stored
            assert repo.get_cached_details(details.match_id, "v2") is None
            kills = repo.get_cached_kill_data_rows([details.match_id, 999], "v1")
            assert list(kills) == [details.match_id]
            assert kills[details.match_id].kill_events == stored.kill_events
            assert kills[details.match_id].player_summary == stored.player_summary
            powers = repo.get_cached_powers_rows([details.match_id], "v1")
            assert powers == {details.match_id: stored.powers}
    finally:
        engine.dispose()
