from sqlalchemy import select
from sqlalchemy.orm import selectinload
from collections.abc import Iterator
from sqlalchemy import create_engine, select, func, and_
from sqlalchemy.orm import sessionmaker, Session, joinedload
from contextlib import contextmanager
from datetime import datetime, timedelta, date
from notify import notify
from db import (
    Base,
    ReplayFile,
    ParsedReplayJson,
    Match,
    MatchPlayer,
    ProcessingStatus,
)
import logging
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class FileListing(BaseModel):
    original_path: str
    match_id: int


class DatabaseManager:
    def __init__(self, connection_string: str):
        """
        Initialize database connection.
        Example: DatabaseManager('postgresql://user:password@localhost:5432/cnc_stats')
        """
        con_str = connection_string.replace("postgres://", "postgresql://")
        self.engine = create_engine(con_str, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def create_all_tables(self):
        """Create all tables in the database."""
        Base.metadata.create_all(self.engine)

    def drop_all_tables(self):
        """Drop all tables - USE WITH CAUTION!"""
        Base.metadata.drop_all(self.engine)

    @contextmanager
    def get_session(self):
        """Context manager for database sessions."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def refresh_materialized_views(self):
        """Refresh materialized views for aggregated stats."""
        with self.engine.connect() as conn:
            conn.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY player_general_stats")
            conn.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY map_stats_view")
            conn.commit()


class ReplayManager:
    """Repository for match-related operations."""

    def __init__(
        self,
        session: Session,
        notify: bool = False,
        auto_commit: bool = True,
    ):
        self.session = session
        self.notify = notify
        self.auto_commit = auto_commit

    def get_replay_file(self, url: str) -> ReplayFile | None:
        fetched = self.session.get(ReplayFile, url)
        return fetched

    def get_parsed_file(self, json_uri: str) -> ParsedReplayJson | None:
        fetched = self.session.get(ParsedReplayJson, json_uri)
        return fetched

    def register_replay(self, from_url: str, s3_uri: str) -> ReplayFile:
        """Register a new replay."""
        logger.info(f"Registering {from_url=} {s3_uri=}")
        prefix = "https://www.gentool.net/data/zh/"
        date_str = from_url.removeprefix(prefix).split("/")[0]
        player = from_url.removeprefix(prefix).split("/")[2]
        player_id = player.split("_")[-1]
        date = datetime.strptime(date_str, "%Y_%m_%B")
        replay_file = ReplayFile(
            original_url=from_url,
            s3_uri=s3_uri,
            source_date=date,
            player_id=player_id,
        )
        self.session.add(replay_file)
        if self.auto_commit:
            self.session.flush()
            self.session.commit()
        if self.notify:
            notify(f"Registered {from_url=} {s3_uri=}")
        return replay_file

    def save_parsed_json(
        self,
        json_s3_uri: str,
        replay_id: int,
        original_replay_file_url: str,
        game_timestamp: datetime,
    ) -> ParsedReplayJson:
        """Save the result of parsing."""
        logger.info(
            f"Saving parsed json {replay_id=} {original_replay_file_url=} {json_s3_uri=} {game_timestamp=}"
        )
        game_date = (game_timestamp - timedelta(hours=5)).date()
        parsed_json = ParsedReplayJson(
            json_s3_uri=json_s3_uri,
            match_id=replay_id,
            replay_file_url=original_replay_file_url,
            game_timestamp=game_timestamp,
            game_date=game_date,
        )
        self.session.add(parsed_json)
        replay_file = self.session.get(ReplayFile, original_replay_file_url)
        replay_file.status = ProcessingStatus.PARSED
        if self.auto_commit:
            self.session.flush()
            self.session.commit()
        if self.notify:
            notify(
                f"Saved parsed json {replay_id=} {original_replay_file_url=} {json_s3_uri=} {game_timestamp=}"
            )
        return parsed_json

    def register_match(self, db_match: Match) -> Match:
        """Register a new replay."""
        logger.info(f"Registering {db_match=}")
        self.session.add(db_match)
        if self.auto_commit:
            self.session.commit()
        if self.notify:
            notify(f"Registered Match {db_match}")
        return db_match

    def list_files(self) -> list[ReplayFile]:
        """List all files."""
        query = self.session.query(ReplayFile)
        return self.session.execute(query).scalars().all()

    def list_jsons(
        self, date: date | None = None, distinct: bool = True
    ) -> list[ParsedReplayJson]:
        """List all jsons or filter by date."""
        stmt = (
            select(ParsedReplayJson)
            .order_by(ParsedReplayJson.match_id, ParsedReplayJson.game_timestamp)
            .options(
                selectinload(ParsedReplayJson.match).selectinload(Match.players)
            )
        )

        if distinct:
            stmt = stmt.distinct(ParsedReplayJson.match_id)

        if date:
            stmt = stmt.where(ParsedReplayJson.game_date == date)

        return self.session.scalars(stmt).all()

    def list_matches(self, duration_cutoff: float) -> list[Match]:
        """List all files."""
        stmt = (
            select(Match)
            .where(Match.duration_minutes > duration_cutoff)
            .options(selectinload(Match.players))
        )
        return self.session.scalars(stmt).all()

    def already_scraped(self) -> set[str]:
        query = self.session.query(ReplayFile.original_url)
        return set(self.session.execute(query).scalars().all())

    def list_dates_with_games(self) -> list[date]:
        """Get the set of dates which have games."""

        stmt = select(ParsedReplayJson.game_date).distinct()
        unique_dates = self.session.execute(stmt).scalars().all()
        return unique_dates
