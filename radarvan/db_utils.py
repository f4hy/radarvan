from cncstats_types import EnhancedReplay
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from collections.abc import Iterator
from sqlalchemy import create_engine, func, and_, update, or_
from sqlalchemy import desc, nulls_last
from sqlalchemy.orm import sessionmaker, Session, joinedload
from contextlib import contextmanager
from datetime import datetime, timedelta, date, UTC
from notify import notify
from typing import Literal
from db import (
    Base,
    ReplayFile,
    ParsedReplayJson,
    Match,
    ProcessingStatus,
    WinnerOverride,
)
import logging
from pydantic import BaseModel
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AllFilesForId:
    replay_files: list[ReplayFile]
    parsed_files: list[ParsedReplayJson]


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

    def all_files_for_id(self, match_id: int) -> AllFilesForId:
        stmt = (
            select(ParsedReplayJson)
            .where(ParsedReplayJson.match_id == match_id)
            .options(joinedload(ParsedReplayJson.replay_file))
        )

        parsed_files = self.session.execute(stmt).scalars().all()
        replay_files = [p.replay_file for p in parsed_files]
        return AllFilesForId(replay_files=replay_files, parsed_files=parsed_files)

    def get_replay_json_by_match_id(self, match_id: int) -> ParsedReplayJson | None:
        statement = (
            select(ParsedReplayJson)
            .where(ParsedReplayJson.match_id == match_id)
            .order_by(nulls_last(desc(ParsedReplayJson.num_time_stamps)))
            .limit(1)
        )
        return self.session.scalar(statement)

    def register_replay(self, from_url: str, s3_uri: str) -> ReplayFile:
        """Register a new replay."""
        logger.info(f"Registering {from_url=} {s3_uri=}")
        prefix2 = "https://generals-public.s3.us-east-2.amazonaws.com/reps/"
        if prefix2 in from_url:
            date_str = "2025_10_December"
            player_id = "5211058E5C33"
        else:
            prefix = "https://www.gentool.net/data/zh/"
            base = from_url.removeprefix(prefix)
            date_str = base.split("/")[0]
            player = base.split("/")[2]
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
        return replay_file

    def save_parsed_json(
        self,
        json_s3_uri: str,
        original_replay_file_url: str,
        parsed_replay: EnhancedReplay,
    ) -> ParsedReplayJson:
        """Save the result of parsing."""
        game_timestamp = datetime.fromtimestamp(parsed_replay.Header.TimeStampBegin)
        replay_id = parsed_replay.replay_id()
        has_enhanced_stats = any(
            chunk.PlayerStats is not None for chunk in parsed_replay.Body
        )
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
            num_time_stamps=parsed_replay.Header.NumTimeStamps,
            has_enhanced_stats=has_enhanced_stats,
        )
        self.session.merge(parsed_json)
        replay_file = self.session.get(ReplayFile, original_replay_file_url)
        replay_file.status = ProcessingStatus.PARSED
        if self.auto_commit:
            self.session.flush()
            self.session.commit()
        return parsed_json

    def register_match(self, db_match: Match) -> Match:
        """Register a new replay."""
        logger.info(f"Registering {db_match=}")
        existing = self.session.get(Match, db_match.match_id)
        if existing is not None:
            logger.warning(f"Match already exists! {db_match.match_id=}")
            return existing
        self.session.add(db_match)
        if self.auto_commit:
            self.session.commit()
        if self.notify:
            notify(f"Registered Match {db_match}")
        return db_match

    def update_match(self, db_match: Match) -> Match:
        """Register a new replay."""
        logger.info(f"updating {db_match=}")
        db_match.created_at = datetime.now(UTC)
        self.session.merge(db_match)
        if self.auto_commit:
            self.session.commit()
        if self.notify:
            notify(f"Update Match {db_match}")
        return db_match

    def list_files(self) -> list[ReplayFile]:
        """List all files."""
        query = self.session.query(ReplayFile)
        return self.session.execute(query).scalars().all()

    def list_jsons(self, date: date | None = None) -> list[ParsedReplayJson]:
        """List all jsons or filter by date."""
        stmt = (
            select(ParsedReplayJson)
            .order_by(ParsedReplayJson.game_timestamp.desc())
            .options(selectinload(ParsedReplayJson.match).selectinload(Match.players))
        )

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

    def get_overrides(self) -> dict[int, WinnerOverride]:
        """Get winner overrides."""

        stmt = select(WinnerOverride)
        overrides = self.session.execute(stmt).scalars().all()
        return {o.match_id: o for o in overrides}

    def set_override(
        self, match_id: int, winner: Literal[1, 2, 3, 4, -1] | None
    ) -> WinnerOverride:
        """Get winner overrides."""
        logger.info(f"Setting override {match_id} {winner}")

        new_override = WinnerOverride(
            match_id=match_id,
            winning_team_id=winner,
        )

        self.session.merge(new_override)
        if self.auto_commit:
            self.session.commit()
        if self.notify:
            notify(f"Saved override {new_override}")
        return new_override

        stmt = select(WinnerOverride)
        overrides = self.session.execute(stmt).scalars().all()
        return {o.match_id: o for o in overrides}

    def list_jsons_without_num_timestamps(self) -> Iterator[ParsedReplayJson]:
        stmt = (
            select(ParsedReplayJson)
            .where(
                or_(
                    ParsedReplayJson.num_time_stamps.is_(None),
                    ParsedReplayJson.has_enhanced_stats.is_(None),
                )
            )
            .order_by(desc(ParsedReplayJson.match_id))
        )
        for result in self.session.execute(stmt).scalars().all():
            yield result

    def list_jsons_without_player_stats(self, limit: int) -> Iterator[int]:
        exclude_terms = ["HardAI", "MediAI", "EasyAI", "1v1v"]
        ranked_subq = select(
            ParsedReplayJson.match_id,
            ParsedReplayJson.replay_file_url,
            ParsedReplayJson.has_enhanced_stats,
            ParsedReplayJson.created_at,
            ParsedReplayJson.num_time_stamps,
            func.row_number()
            .over(
                partition_by=ParsedReplayJson.match_id,
                order_by=[
                    ParsedReplayJson.num_time_stamps.desc(),
                    ParsedReplayJson.created_at.desc(),  # Tiebreaker: most recent
                ],
            )
            .label("rn"),
        ).subquery()

        stmt = (
            select(ranked_subq.c.match_id, ranked_subq.c.replay_file_url)
            .where(
                and_(
                    ranked_subq.c.rn == 1,
                    ranked_subq.c.has_enhanced_stats == False,
                    ~or_(
                        *[
                            ranked_subq.c.replay_file_url.contains(term)
                            for term in exclude_terms
                        ]
                    ),
                    ranked_subq.c.num_time_stamps > 5000,
                )
            )
            .order_by(ranked_subq.c.created_at.desc())
            .limit(limit)
        )
        for match_id, url in self.session.execute(stmt):
            yield {"match_id": match_id, "url": url}

    def update_parsed_json(
        self,
        json_s3_uri: str,  # Primary key
        num_time_stamps: int,
        has_player_stats: bool,
    ) -> bool:
        """Update the file_size_bytes for a ParsedReplayJson record.

        Returns:
            bool: True if updated, False if not found
        """
        statement = (
            update(ParsedReplayJson)
            .where(ParsedReplayJson.json_s3_uri == json_s3_uri)
            .values(
                num_time_stamps=num_time_stamps, has_enhanced_stats=has_player_stats
            )
        )

        result = self.session.execute(statement)
        self.session.commit()

        return result.rowcount > 0
