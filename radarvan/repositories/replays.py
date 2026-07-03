"""ReplayFile + ParsedReplayJson repository.

The original .rep file (ReplayFile) and its parsed JSON (ParsedReplayJson) are
almost always queried together, so they share a repo.
"""

from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, date
import structlog

from pydantic import BaseModel

from sqlalchemy import and_, desc, func, nulls_last, or_, select, update
from sqlalchemy.orm import joinedload

from ..cncstats_model.zhreplay import EnhancedReplayV2
from ..db import Match, ParsedReplayJson, ProcessingStatus, ReplayFile
from ..utils import game_night_date

from .base import BaseRepo

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class AllFilesForId:
    replay_files: list[ReplayFile]
    parsed_files: list[ParsedReplayJson]


@dataclass(frozen=True)
class ReplayToProcess:
    match_id: int
    url: str
    s3_path: str
    version: str | None
    all_replay_urls: list[str]


class FileListing(BaseModel):
    original_path: str
    match_id: int


class ReplayRepo(BaseRepo):
    """Operations on ReplayFile and ParsedReplayJson."""

    def get_replay_file(self, url: str) -> ReplayFile | None:
        return self.session.get(ReplayFile, url)

    def get_parsed_file(self, json_uri: str) -> ParsedReplayJson | None:
        return self.session.get(ParsedReplayJson, json_uri)

    def all_files_for_id(self, match_id: int) -> AllFilesForId:
        stmt = (
            select(ParsedReplayJson)
            .where(ParsedReplayJson.match_id == match_id)
            .options(joinedload(ParsedReplayJson.replay_file))
        )

        parsed_files = list(self.session.execute(stmt).scalars().all())
        replay_files = [p.replay_file for p in parsed_files]
        return AllFilesForId(replay_files=replay_files, parsed_files=parsed_files)

    def get_replay_json_by_match_id(self, match_id: int) -> ParsedReplayJson | None:
        statement = (
            select(ParsedReplayJson)
            .where(ParsedReplayJson.match_id == match_id)
            .order_by(
                desc(ParsedReplayJson.json_s3_uri.like("%upload%")),
                nulls_last(desc(ParsedReplayJson.num_time_stamps)),
            )
            .limit(1)
        )
        return self.session.scalar(statement)

    def get_replay_by_hash(self, file_hash: str) -> ReplayFile | None:
        """Look up a replay file by its SHA-256 hash."""
        return self.session.scalar(
            select(ReplayFile).where(ReplayFile.file_hash == file_hash)
        )

    def register_replay(self, from_url: str, s3_uri: str, file_hash: str) -> ReplayFile:
        """Register a new replay scraped from a known source URL."""
        logger.info("registering replay", from_url=from_url, s3_uri=s3_uri)
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
        source_date = datetime.strptime(date_str, "%Y_%m_%B").date()  # noqa: DTZ007 (date has no strptime of its own)
        replay_file = ReplayFile(
            original_url=from_url,
            s3_uri=s3_uri,
            source_date=source_date,
            player_id=player_id,
            file_hash=file_hash,
        )
        self.session.add(replay_file)
        if self.auto_commit:
            self.session.flush()
            self.session.commit()
        return replay_file

    def register_uploaded_replay(
        self,
        original_url: str,
        s3_uri: str,
        file_hash: str,
        source_date: date,
        mac_id: str | None = None,
        board_id: str | None = None,
        uploader_name: str | None = None,
        client_version: str | None = None,
        source_tag: str | None = None,
        zulu_build: str | None = None,
        is_dev: bool = False,
    ) -> ReplayFile:
        """Register a replay that was uploaded directly (not fetched from a URL)."""
        logger.info(
            "registering uploaded replay", original_url=original_url, s3_uri=s3_uri
        )
        replay_file = ReplayFile(
            original_url=original_url,
            s3_uri=s3_uri,
            source_date=source_date,
            player_id="upload",
            file_hash=file_hash,
            mac_id=mac_id,
            board_id=board_id,
            uploader_name=uploader_name,
            client_version=client_version,
            source_tag=source_tag,
            zulu_build=zulu_build,
            is_dev=is_dev,
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
        parsed_replay: EnhancedReplayV2,
    ) -> ParsedReplayJson:
        """Save the result of parsing."""
        hdr = parsed_replay.header
        ts_begin = (hdr.time_stamp_begin if hdr else None) or 0
        game_timestamp = datetime.fromtimestamp(ts_begin, tz=UTC)
        replay_id = parsed_replay.replay_id
        has_enhanced_stats = parsed_replay.stats is not None
        logger.info(
            "saving parsed json",
            replay_id=replay_id,
            original_replay_file_url=original_replay_file_url,
            json_s3_uri=json_s3_uri,
            game_timestamp=game_timestamp,
        )
        game_date = game_night_date(ts_begin)
        parsed_json = ParsedReplayJson(
            json_s3_uri=json_s3_uri,
            match_id=replay_id,
            replay_file_url=original_replay_file_url,
            game_timestamp=game_timestamp,
            game_date=game_date,
            game_version=((hdr.version if hdr else None) or "").replace("Version ", "")[
                :8
            ],
            num_time_stamps=(hdr.frame_count if hdr else None) or 0,
            has_enhanced_stats=has_enhanced_stats,
            is_v2=(parsed_replay.version == 2),
            updated_at=datetime.now(UTC),
        )
        self.session.merge(parsed_json)
        replay_file = self.session.get(ReplayFile, original_replay_file_url)
        if replay_file is not None:
            replay_file.status = ProcessingStatus.PARSED
        if self.auto_commit:
            self.session.flush()
            self.session.commit()
        return parsed_json

    def update_parsed_json(
        self,
        json_s3_uri: str,  # Primary key
        num_time_stamps: int,
        has_player_stats: bool,
    ) -> bool:
        """Update the time-stamp count and stats flag for a ParsedReplayJson row.

        Returns True if the row existed and was updated, False if not found.
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

        # SQLAlchemy stubs type Session.execute() as Result[Any], but DML
        # statements always return CursorResult which has rowcount.
        return result.rowcount > 0  # type: ignore[attr-defined, no-any-return]

    def list_files(self) -> list[ReplayFile]:
        query = self.session.query(ReplayFile)
        return list(self.session.execute(query).scalars().all())

    def list_jsons(
        self,
        match_id: int | None = None,
        game_date: date | None = None,
    ) -> list[ParsedReplayJson]:
        """List parsed jsons, optionally filtered by match_id and/or game_date."""
        from sqlalchemy.orm import selectinload

        stmt = (
            select(ParsedReplayJson)
            .order_by(ParsedReplayJson.game_timestamp.desc())
            .options(
                selectinload(ParsedReplayJson.match).selectinload(Match.players),
                selectinload(ParsedReplayJson.replay_file),
            )
        )
        if match_id is not None:
            stmt = stmt.where(ParsedReplayJson.match_id == match_id)
        if game_date is not None:
            stmt = stmt.where(ParsedReplayJson.game_date == game_date)

        return list(self.session.scalars(stmt).all())

    def list_pending_without_parsed(self) -> list[ReplayFile]:
        """Return ReplayFiles in PENDING status that have no ParsedReplayJson."""
        stmt = (
            select(ReplayFile)
            .outerjoin(ReplayFile.parsed_replay_json)
            .where(
                ReplayFile.status == ProcessingStatus.PENDING,
                ParsedReplayJson.json_s3_uri.is_(None),
            )
        )
        return list(self.session.scalars(stmt).all())

    def already_scraped(self) -> set[str]:
        query = self.session.query(ReplayFile.original_url)
        return set(self.session.execute(query).scalars().all())

    def list_dates_with_games(self) -> list[date]:
        """Get the set of dates which have games."""
        stmt = (
            select(ParsedReplayJson.game_date)
            .distinct()
            .order_by(ParsedReplayJson.game_date.desc())
        )
        return list(self.session.scalars(stmt))

    def list_jsons_without_match(self) -> list[ParsedReplayJson]:
        """Return ParsedReplayJson rows that have no corresponding Match row."""
        stmt = select(ParsedReplayJson).where(
            ParsedReplayJson.match_id.not_in(select(Match.match_id))
        )
        return list(self.session.scalars(stmt).all())

    def list_jsons_non_v2(self, limit: int) -> list[ParsedReplayJson]:
        stmt = (
            select(ParsedReplayJson)
            .where(ParsedReplayJson.is_v2.is_not(True))
            .order_by(ParsedReplayJson.created_at.desc())
            .limit(limit)
        )

        return list(self.session.scalars(stmt).all())

    def list_jsons_since_date(self, since: date) -> list[ParsedReplayJson]:
        """Return one ParsedReplayJson per match_id where the game_date is on or after `since`."""
        stmt = (
            select(ParsedReplayJson)
            .where(ParsedReplayJson.game_date >= since)
            .distinct(ParsedReplayJson.match_id)
            .order_by(
                ParsedReplayJson.match_id,
                ParsedReplayJson.num_time_stamps.desc(),
            )
        )
        return list(self.session.scalars(stmt).all())

    def list_jsons_parsed_before(
        self, before: date, limit: int
    ) -> list[ParsedReplayJson]:
        """Return one ParsedReplayJson per match_id where no record for that match
        has been updated at or after `before`, picking the most recently updated."""
        recently_updated_match_ids = select(ParsedReplayJson.match_id).where(
            func.coalesce(ParsedReplayJson.updated_at, ParsedReplayJson.created_at)
            >= before
        )
        stmt = (
            select(ParsedReplayJson)
            .where(
                and_(
                    ParsedReplayJson.match_id.not_in(recently_updated_match_ids),
                    ParsedReplayJson.num_time_stamps > 5000,
                )
            )
            .distinct(ParsedReplayJson.match_id)
            .order_by(
                ParsedReplayJson.match_id,
                func.coalesce(
                    ParsedReplayJson.updated_at, ParsedReplayJson.created_at
                ).desc(),
            )
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

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
        yield from self.session.execute(stmt).scalars().all()

    def list_jsons_without_player_stats(self, limit: int) -> Iterator[ReplayToProcess]:
        exclude_terms = ["HardAI_HardAI", "MediAI", "EasyAI", "1v1v"]
        ranked_subq = select(
            ParsedReplayJson.match_id,
            ParsedReplayJson.replay_file_url,
            ParsedReplayJson.has_enhanced_stats,
            ParsedReplayJson.created_at,
            ParsedReplayJson.num_time_stamps,
            ParsedReplayJson.game_version,
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
            select(
                ranked_subq.c.match_id,
                ranked_subq.c.replay_file_url,
                ReplayFile.s3_uri,
                ranked_subq.c.game_version,
            )
            .join(ReplayFile, ReplayFile.original_url == ranked_subq.c.replay_file_url)
            .where(
                and_(
                    ranked_subq.c.rn == 1,
                    ranked_subq.c.has_enhanced_stats.is_(False),
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
        rows = list(self.session.execute(stmt))

        match_ids = [row.match_id for row in rows]
        urls_by_match: defaultdict[int, list[str]] = defaultdict(list)
        if match_ids:
            url_rows = self.session.execute(
                select(
                    ParsedReplayJson.match_id, ParsedReplayJson.replay_file_url
                ).where(ParsedReplayJson.match_id.in_(match_ids))
            )
            for mid, replay_url in url_rows:
                urls_by_match[mid].append(replay_url)

        for row in rows:
            yield ReplayToProcess(
                match_id=row.match_id,
                url=row.replay_file_url,
                s3_path=row.s3_uri,
                version=row.game_version,
                all_replay_urls=urls_by_match[row.match_id],
            )

    def parsed_replay_updated_at(self, match_id: int) -> datetime | None:
        return self.session.scalar(
            select(ParsedReplayJson.updated_at)
            .where(ParsedReplayJson.match_id == match_id)
            .limit(1)
        )
