from .cncstats_model.zhreplay import EnhancedReplayV2
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from collections import defaultdict
from collections.abc import Generator, Iterator
from sqlalchemy import create_engine, func, and_, update, or_
from sqlalchemy import desc, nulls_last
from sqlalchemy.orm import sessionmaker, Session, joinedload
from contextlib import contextmanager
from datetime import datetime, timedelta, date
from .notify import notify
from .db import (
    Base,
    ComputedStatistic,
    MapData,
    ReplayFile,
    ParsedReplayJson,
    Match,
    MatchCompostion,
    ProcessingStatus,
    WinnerOverride,
    TournamentReport,
    TournamentStat,
    MatchPlayer,
)
from .game_composition import GameComposition, compute_match_composition
from .api_types import (
    MapDataPayload,
    TournamentReport as PydanticTournamentReport,
    Statistic as PydanticStatistic,
)
import logging
from pydantic import BaseModel
from dataclasses import dataclass

logger = logging.getLogger(__name__)


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


@dataclass(frozen=True)
class MatchDebugData:
    matches: Match | None
    match_players: list[MatchPlayer]
    match_compostion: MatchCompostion | None
    winner_overrides: WinnerOverride | None
    parsed_replay_json: list[ParsedReplayJson]
    replay_files: list[ReplayFile]


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

    def create_all_tables(self) -> None:
        """Create all tables in the database."""
        Base.metadata.create_all(self.engine)

    # def drop_all_tables(self) -> None:
    #     """Drop all tables - USE WITH CAUTION!"""
    #     Base.metadata.drop_all(self.engine)

    @contextmanager
    def get_session(self) -> Generator[Session]:
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

    @contextmanager
    def get_replay_manager(self, notify: bool = False) -> Generator["ReplayManager"]:
        with self.get_session() as session:
            yield ReplayManager(session, notify=notify)


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

    def latest_match_created_at(self) -> datetime | None:
        return self.session.scalar(select(func.max(Match.created_at)))

    def parsed_replay_updated_at(self, match_id: int) -> datetime | None:
        return self.session.scalar(
            select(ParsedReplayJson.updated_at)
            .where(ParsedReplayJson.match_id == match_id)
            .limit(1)
        )

    def get_match(self, match_id: int) -> Match | None:
        return self.session.get(Match, match_id)

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

        parsed_files = list(self.session.execute(stmt).scalars().all())
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

    def get_replay_by_hash(self, file_hash: str) -> ReplayFile | None:
        """Look up a replay file by its SHA-256 hash."""
        return self.session.scalar(
            select(ReplayFile).where(ReplayFile.file_hash == file_hash)
        )

    def register_replay(self, from_url: str, s3_uri: str, file_hash: str) -> ReplayFile:
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
    ) -> ReplayFile:
        """Register a replay that was uploaded directly (not fetched from a URL)."""
        logger.info(f"Registering uploaded replay {original_url=} {s3_uri=}")
        replay_file = ReplayFile(
            original_url=original_url,
            s3_uri=s3_uri,
            source_date=source_date,
            player_id="upload",
            file_hash=file_hash,
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
        game_timestamp = datetime.fromtimestamp(ts_begin)
        replay_id = parsed_replay.replay_id
        has_enhanced_stats = parsed_replay.stats is not None
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
            game_version=((hdr.version if hdr else None) or "").replace("Version ", "")[
                :8
            ],
            num_time_stamps=(hdr.frame_count if hdr else None) or 0,
            has_enhanced_stats=has_enhanced_stats,
            is_v2=(parsed_replay.version == 2),
            updated_at=datetime.utcnow(),
        )
        self.session.merge(parsed_json)
        replay_file = self.session.get(ReplayFile, original_replay_file_url)
        if replay_file is not None:
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

    def update_match(self, new_match: Match) -> Match | None:
        """Replace the existing match record with data from new_match."""
        existing = self.session.get(Match, new_match.match_id)
        if existing is None:
            return None
        if (
            new_match.winning_team_id is not None
            and existing.winning_team_id != new_match.winning_team_id
        ):
            notify(
                f"Update to Match id {new_match.match_id} is changing the winner"
                f" from {existing.winning_team_id} to {new_match.winning_team_id}"
            )
        # Preserve the original creation timestamp since new_match won't have it set.
        new_match.created_at = existing.created_at
        # Clear players before merge: new MatchPlayer objects have no id, so merge
        # would insert duplicates rather than replace the existing rows.
        existing.players.clear()
        self.session.flush()
        merged = self.session.merge(new_match)
        if self.auto_commit:
            self.session.commit()
        if self.notify:
            notify(f"Update Match {merged}")
        return merged

    def compute_and_save_composition(self, match_id: int) -> GameComposition | None:
        """Compute match composition and persist to match_compostion table."""
        match = self.session.get(Match, match_id)
        if match is None:
            return None
        comp = compute_match_composition(match.players)
        db_comp = MatchCompostion(
            match_id=match_id,
            category=comp.category,
            is_comp_stomp=comp.is_comp_stomp,
            is_ffa=comp.is_ffa,
            num_teams=comp.num_teams,
            team_sizes=comp.team_sizes,
            total_players=comp.total_players,
            num_humans=comp.num_humans,
            num_computers=comp.num_computers,
            is_balanced=comp.is_balanced,
            is_1v1=comp.is_1v1,
            is_team_game=comp.is_team_game,
        )
        self.session.merge(db_comp)
        if self.auto_commit:
            self.session.commit()
        return comp

    def list_files(self) -> list[ReplayFile]:
        """List all files."""
        query = self.session.query(ReplayFile)
        return list(self.session.execute(query).scalars().all())

    def list_jsons(self, date: date | None = None) -> list[ParsedReplayJson]:
        """List all jsons or filter by date."""
        stmt = (
            select(ParsedReplayJson)
            .order_by(ParsedReplayJson.game_timestamp.desc())
            .options(selectinload(ParsedReplayJson.match).selectinload(Match.players))
        )

        if date:
            stmt = stmt.where(ParsedReplayJson.game_date == date)

        return list(self.session.scalars(stmt).all())

    def list_matches(self, duration_cutoff: float) -> list[Match]:
        """List all files."""
        stmt = (
            select(Match)
            .where(Match.duration_minutes > duration_cutoff)
            .options(selectinload(Match.composition))
            .options(selectinload(Match.players))
            .options(selectinload(Match.replay_json))
        )
        return list(self.session.scalars(stmt).all())

    def list_matches_without_game_version(self, limit: int = 10) -> list[Match]:
        """List all files."""
        stmt = select(Match).where(Match.game_version.is_(None)).limit(limit)
        return list(self.session.scalars(stmt).all())

    def list_matches_with_winner_but_incomplete(
        self, limit: int = 10
    ) -> list[tuple[Match, bool | None]]:
        stmt = (
            select(Match, ParsedReplayJson.has_enhanced_stats)
            .join(Match.replay_json)
            .where(
                Match.incomplete.isnot(None),
                Match.incomplete != "",
                Match.incomplete != "Too Short",
                Match.winning_team_id > 0,
                # ParsedReplayJson.has_enhanced_stats is True,
            )
            .limit(limit)
        )
        # Row[tuple[...]] is a tuple subclass at runtime but SQLAlchemy stubs
        # don't express this, so the Sequence[Row[...]] → list[tuple[...]] conversion
        # isn't accepted without an ignore.
        return list(self.session.execute(stmt).all())  # type: ignore[arg-type]

    def list_matches_with_player_unk(self, limit: int = 10) -> list[int]:
        stmt = (
            select(MatchPlayer.match_id)
            .where(
                MatchPlayer.general_id < 0,
                MatchPlayer.team_id > 0,
            )
            .limit(limit)
            .distinct()
        )
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

    def get_overrides(self) -> dict[int, WinnerOverride]:
        """Get winner overrides."""

        stmt = select(WinnerOverride)
        overrides = self.session.execute(stmt).scalars().all()
        return {o.match_id: o for o in overrides}

    def set_override(
        self, match_id: int, winner: int | None, incomplete: str | None = None
    ) -> WinnerOverride:
        """Set winner and/or incomplete override for a match."""
        logger.info(f"Setting override {match_id} {winner} incomplete={incomplete}")

        existing = self.session.get(WinnerOverride, match_id)
        new_override = WinnerOverride(
            match_id=match_id,
            winning_team_id=winner
            if winner is not None
            else (existing.winning_team_id if existing else None),
            incomplete=incomplete
            if incomplete is not None
            else (existing.incomplete if existing else None),
        )

        self.session.merge(new_override)
        if self.auto_commit:
            self.session.commit()
        if self.notify:
            notify(f"Saved override {new_override}")
        return new_override

    def delete_override(self, match_id: int) -> bool:
        """Delete a winner override for a match. Returns True if deleted, False if not found."""
        override = self.session.get(WinnerOverride, match_id)
        if override is None:
            return False
        self.session.delete(override)
        if self.auto_commit:
            self.session.commit()
        return True

    def reset_match(self, match_id: int) -> dict[str, int]:
        """Delete all data for a match except the ReplayFile; reset ReplayFile status to PENDING.

        Deletion order respects FK constraints:
          1. WinnerOverride (no FK dependency)
          2. MatchCompostion (FK → matches, deleted before Match)
          3. Match (ORM cascade deletes MatchPlayers)
          4. ParsedReplayJson (FK ← Match now gone)
          5. ReplayFile status reset to PENDING
        """
        counts: dict[str, int] = {
            "winner_overrides": 0,
            "match_composition": 0,
            "match": 0,
            "parsed_replay_json": 0,
            "replay_files_reset": 0,
        }

        override = self.session.get(WinnerOverride, match_id)
        if override:
            self.session.delete(override)
            counts["winner_overrides"] = 1

        composition = self.session.get(MatchCompostion, match_id)
        if composition:
            self.session.delete(composition)
            counts["match_composition"] = 1

        match = self.session.get(Match, match_id)
        if match:
            self.session.delete(match)
            counts["match"] = 1

        # Flush so the Match delete is visible before we touch ParsedReplayJson
        self.session.flush()

        parsed_jsons = list(
            self.session.scalars(
                select(ParsedReplayJson).where(ParsedReplayJson.match_id == match_id)
            ).all()
        )
        replay_file_urls = [p.replay_file_url for p in parsed_jsons]
        for p in parsed_jsons:
            self.session.delete(p)
        counts["parsed_replay_json"] = len(parsed_jsons)

        self.session.flush()

        replay_files_to_reset = list(
            self.session.scalars(
                select(ReplayFile).where(ReplayFile.original_url.in_(replay_file_urls))
            ).all()
        )
        for rf in replay_files_to_reset:
            rf.status = ProcessingStatus.PENDING
            counts["replay_files_reset"] += 1

        if self.auto_commit:
            self.session.commit()
        return counts

    def list_matches_without_composition(self) -> Iterator[int]:
        """Yield match_ids for matches with no MatchCompostion row or an Unknown category."""
        stmt = (
            select(Match.match_id)
            .outerjoin(MatchCompostion, MatchCompostion.match_id == Match.match_id)
            .where(
                or_(
                    MatchCompostion.match_id.is_(None),
                    MatchCompostion.category == "Unknown",
                )
            )
        )
        yield from self.session.scalars(stmt).all()

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

        # SQLAlchemy stubs type Session.execute() as Result[Any], but DML
        # statements always return CursorResult which has rowcount.
        return result.rowcount > 0  # type: ignore[attr-defined, no-any-return]

    def save_tournament_report(
        self,
        pydantic_report: PydanticTournamentReport,
    ) -> None:
        """
        Save a Pydantic TournamentReport to the database.

        Args:
            session: SQLAlchemy session
            pydantic_report: Pydantic TournamentReport object

        Returns:
            The saved SQLAlchemy TournamentReport instance
        """
        stmt = select(TournamentReport).where(
            TournamentReport.name == pydantic_report.name
        )
        db_report = self.session.scalar(stmt)
        if db_report is not None:
            # Update existing report - remove old stats
            db_report.stats.clear()
        else:
            # Create new report
            db_report = TournamentReport(name=pydantic_report.name)

        # Create and associate stats
        for pydantic_stat in pydantic_report.stats:
            db_stat = TournamentStat(
                stat_name=pydantic_stat.stat_name,
                player=pydantic_stat.player,
                match_id=pydantic_stat.match_id,
                date_computed=pydantic_stat.date_computed,
                tournament_report=db_report,
            )

            # Handle the value field - determine if it's float or str
            if pydantic_stat.value is not None:
                if isinstance(pydantic_stat.value, (int, float)):
                    db_stat.value_float = float(pydantic_stat.value)
                else:
                    db_stat.value_str = str(pydantic_stat.value)

        # Add to session and commit
        self.session.add(db_report)
        self.session.commit()
        return None

    def get_all_data_for_match(self, match_id: int) -> MatchDebugData:
        """Fetch every row related to a match_id across all tables."""
        match = self.session.get(Match, match_id)
        players = list(
            self.session.scalars(
                select(MatchPlayer).where(MatchPlayer.match_id == match_id)
            ).all()
        )
        composition = self.session.get(MatchCompostion, match_id)
        override = self.session.get(WinnerOverride, match_id)
        parsed_jsons = list(
            self.session.scalars(
                select(ParsedReplayJson).where(ParsedReplayJson.match_id == match_id)
            ).all()
        )
        replay_file_urls = [p.replay_file_url for p in parsed_jsons]
        replay_files = (
            list(
                self.session.scalars(
                    select(ReplayFile).where(
                        ReplayFile.original_url.in_(replay_file_urls)
                    )
                ).all()
            )
            if replay_file_urls
            else []
        )
        return MatchDebugData(
            matches=match,
            match_players=players,
            match_compostion=composition,
            winner_overrides=override,
            parsed_replay_json=parsed_jsons,
            replay_files=replay_files,
        )

    def clear_computed_stats(self) -> int:
        """Delete all computed statistics. Returns the number of rows deleted."""
        from sqlalchemy import delete as sa_delete

        result = self.session.execute(sa_delete(ComputedStatistic))
        if self.auto_commit:
            self.session.commit()
        return result.rowcount  # type: ignore[attr-defined, no-any-return]

    def save_computed_stats(self, stats: list[PydanticStatistic]) -> None:
        """Persist a batch of computed statistics using each stat's date_computed."""
        for stat in stats:
            db_stat = ComputedStatistic(
                stat_name=stat.stat_name,
                player=stat.player,
                match_id=stat.match_id,
                date_computed=stat.date_computed,
            )
            if stat.value is not None:
                if isinstance(stat.value, (int, float)):
                    db_stat.value_float = float(stat.value)
                else:
                    db_stat.value_str = str(stat.value)
            self.session.add(db_stat)
        if self.auto_commit:
            self.session.commit()

    def get_computed_stats(self) -> list[PydanticStatistic]:
        """Return all persisted computed statistics, ordered by id."""
        stmt = select(ComputedStatistic).order_by(ComputedStatistic.id)
        rows = list(self.session.scalars(stmt).all())
        return [
            PydanticStatistic(
                stat_name=row.stat_name,
                date_computed=row.date_computed,
                value=row.value_float if row.value_float is not None else row.value_str,
                player=row.player,
                match_id=row.match_id,
            )
            for row in rows
        ]

    def computed_stats_are_stale(self, days: int = 3) -> bool:
        """Return True if no computed stats exist or the newest is older than `days` days."""
        latest = self.session.scalar(select(func.max(ComputedStatistic.date_computed)))
        if latest is None:
            return True
        return (date.today() - latest).days > days

    def save_map_data(self, map_name: str, payload: MapDataPayload) -> None:
        """Upsert map geometry data for the given map name."""
        row = MapData(map_name=map_name, data=payload.model_dump())
        self.session.merge(row)
        if self.auto_commit:
            self.session.commit()

    def get_map_data(self, map_name: str) -> MapDataPayload | None:
        """Return the map geometry payload for the given map name (case-insensitive), or None."""
        stmt = select(MapData).where(MapData.map_name.ilike(map_name))
        row = self.session.scalar(stmt)
        if row is None:
            return None
        return MapDataPayload.model_validate(row.data)

    def list_maps_by_player_count(self) -> dict[int, list[str]]:
        """Return all known maps grouped by number of player starting positions."""
        rows = self.session.scalars(select(MapData)).all()
        result: dict[int, list[str]] = {}
        for row in rows:
            starts = row.data.get("player_starts")
            count = len(starts) if isinstance(starts, list) else 0
            result.setdefault(count, []).append(row.map_name)
        return {k: sorted(v) for k, v in sorted(result.items())}

    def get_tournament_report_by_name(
        self, name: str
    ) -> PydanticTournamentReport | None:  # Returns Pydantic model
        """
        Retrieve a TournamentReport by name and convert to Pydantic model.

        Args:
            session: SQLAlchemy session
            name: Name of the tournament report

        Returns:
            Pydantic TournamentReport object or None if not found
        """
        # Query the database
        stmt = select(TournamentReport).where(TournamentReport.name == name)
        db_report = self.session.scalar(stmt)

        if db_report is None:
            return None

        # Convert SQLAlchemy model to Pydantic model
        pydantic_stats = []
        for db_stat in db_report.stats:
            # Determine which value field to use
            value = (
                db_stat.value_float
                if db_stat.value_float is not None
                else db_stat.value_str
            )

            pydantic_stat = PydanticStatistic(
                stat_name=db_stat.stat_name,
                date_computed=db_stat.date_computed or date.today(),
                value=value,
                player=db_stat.player,
                match_id=db_stat.match_id,
            )
            pydantic_stats.append(pydantic_stat)

        pydantic_report = PydanticTournamentReport(
            name=db_report.name, stats=pydantic_stats
        )

        return pydantic_report
