from datetime import UTC, datetime, date
import enum
from enum import IntEnum
from sqlalchemy import (
    ARRAY,
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    SmallInteger,
    String,
    Text,
    Float,
    DateTime,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


def _utcnow() -> datetime:
    """Replacement for the deprecated datetime.utcnow() used as a column default.

    Returns an aware UTC datetime. SQLAlchemy will store it as-is on tz-aware
    columns and silently strip the tzinfo on naive columns (preserving the
    existing-stored-value semantics — i.e. wall-clock UTC).
    """
    return datetime.now(UTC)


class General(IntEnum):
    USA = 0
    AIR = 1
    LASER = 2
    SUPER = 3
    CHINA = 4
    NUKE = 5
    TANK = 6
    INFANTRY = 7
    GLA = 8
    TOXIN = 9
    STEALTH = 10
    DEMO = 11
    UNRECOGNIZED = -1


class Base(DeclarativeBase):
    pass


class ProcessingStatus(enum.Enum):
    PENDING = "pending"
    SKIPPED = "skipped"
    PARSED = "parsed"
    FAILED = "failed"


class ReplayFile(Base):
    """Original replay files from HTTP URIs"""

    __tablename__ = "replay_files"

    original_url: Mapped[str] = mapped_column(
        String, primary_key=True, unique=True, index=True
    )
    s3_uri: Mapped[str] = mapped_column(String, unique=True, index=True)
    status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus),
        default=ProcessingStatus.PENDING,
        index=True,
    )
    player_id: Mapped[str] = mapped_column(String, index=True)
    file_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True, index=True
    )

    # Optional uploader-supplied identifiers (set by /api/upload_replay).
    mac_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    board_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    uploader_name: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    client_version: Mapped[str | None] = mapped_column(String, nullable=True)
    source_tag: Mapped[str | None] = mapped_column(String, nullable=True)

    # Value of the X-Zulu-Build header sent to /api/upload_replay (if any).
    zulu_build: Mapped[str | None] = mapped_column(String, nullable=True)
    # True when the uploader's zulu_build started with "dev-" (a dev client).
    is_dev: Mapped[bool] = mapped_column(
        default=False, server_default="false", index=True
    )

    # Timestamps
    discovered_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    source_date: Mapped[date] = mapped_column(index=True)

    # Relationships
    parsed_replay_json: Mapped["ParsedReplayJson | None"] = relationship(
        back_populates="replay_file"
    )

    def __repr__(self) -> str:
        return f"<ReplayFile(url={self.original_url}, status={self.status})>"


class ParsedReplayJson(Base):
    """Parsed replay data stored in S3"""

    __tablename__ = "parsed_replay_json"

    json_s3_uri: Mapped[str] = mapped_column(String, primary_key=True)
    match_id: Mapped[int] = mapped_column(index=True)
    replay_file_url: Mapped[str] = mapped_column(
        ForeignKey("replay_files.original_url", ondelete="CASCADE"),
        unique=True,
    )

    # File info
    num_time_stamps: Mapped[int | None] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
    game_timestamp: Mapped[datetime] = mapped_column(DateTime)
    game_date: Mapped[date | None] = mapped_column(index=True)
    game_version: Mapped[str | None] = mapped_column(String(10))
    has_enhanced_stats: Mapped[bool | None] = mapped_column()
    is_v2: Mapped[bool | None] = mapped_column()

    # Relationships
    replay_file: Mapped[ReplayFile] = relationship(back_populates="parsed_replay_json")
    match: Mapped["Match | None"] = relationship(
        back_populates="replay_json", lazy="joined"
    )

    def __repr__(self) -> str:
        return (
            f"<ParsedReplayJson(s3_uri={self.json_s3_uri}, match_id={self.match_id})>"
        )


class Match(Base):
    __tablename__ = "matches"

    match_id: Mapped[int] = mapped_column(primary_key=True)
    json_s3_uri: Mapped[str] = mapped_column(
        ForeignKey("parsed_replay_json.json_s3_uri", ondelete="CASCADE"),
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    map: Mapped[str] = mapped_column(String(100))
    winning_team_id: Mapped[int | None] = mapped_column(SmallInteger)
    duration_minutes: Mapped[float] = mapped_column(Float)
    filename: Mapped[str] = mapped_column(String(255))
    incomplete: Mapped[str | None] = mapped_column(String, default=None)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
    game_version: Mapped[str | None] = mapped_column(String(10))
    # Mirrors ReplayFile.is_dev: True when sourced from a "dev-" zulu build.
    is_dev: Mapped[bool] = mapped_column(
        default=False, server_default="false", index=True
    )

    __table_args__ = (
        CheckConstraint("duration_minutes >= 0", name="check_duration_positive"),
        Index("idx_matches_timestamp", "timestamp"),
        Index("idx_matches_map", "map"),
        Index("idx_matches_winning_team", "winning_team_id"),
    )

    # Relationships
    replay_json: Mapped["ParsedReplayJson | None"] = relationship(
        back_populates="match"
    )
    players: Mapped[list["MatchPlayer"]] = relationship(
        back_populates="match",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    composition: Mapped["MatchCompostion | None"] = relationship(back_populates="match")

    def __repr__(self) -> str:
        return (
            f"<Match(match_id=`{self.match_id}` game_version=`{self.game_version}` \n"
            f"`winner={self.winning_team_id}`\n"
            f" updated_at=`{self.updated_at}` created_at=`{self.created_at}` players=\n{self.players})>"
        )


class MatchPlayer(Base):
    __tablename__ = "match_players"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.match_id", ondelete="CASCADE")
    )
    player_name: Mapped[str] = mapped_column(String(100))
    general_id: Mapped[int] = mapped_column(SmallInteger)
    team_id: Mapped[int] = mapped_column(SmallInteger)
    color: Mapped[str] = mapped_column(String(20))
    is_winner: Mapped[bool] = mapped_column()
    starting_position: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    __table_args__ = (
        Index("idx_match_players_match", "match_id"),
        Index("idx_match_players_player", "player_name"),
    )

    match: Mapped[Match] = relationship(back_populates="players")

    def __repr__(self) -> str:
        return f"<{self.player_name}[{General(self.general_id).name}] team={self.team_id} {'W🏆' if self.is_winner else 'L❌'}>\n"


class WinnerOverride(Base):
    __tablename__ = "winner_overrides"

    match_id: Mapped[int] = mapped_column(primary_key=True)
    winning_team_id: Mapped[int | None] = mapped_column(SmallInteger)
    incomplete: Mapped[str | None] = mapped_column(String, default=None)


class TournamentReport(Base):
    __tablename__ = "tournament_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)

    stats: Mapped[list["TournamentStat"]] = relationship(
        back_populates="tournament_report", cascade="all, delete-orphan"
    )


class TournamentStat(Base):
    __tablename__ = "tournament_stats"

    id: Mapped[int] = mapped_column(primary_key=True)
    stat_name: Mapped[str] = mapped_column(String)
    value_float: Mapped[float | None] = mapped_column(Float)
    value_str: Mapped[str | None] = mapped_column(String)
    player: Mapped[str | None] = mapped_column(String)
    match_id: Mapped[int | None] = mapped_column()
    date_computed: Mapped[date | None] = mapped_column()

    tournament_report_id: Mapped[int] = mapped_column(
        ForeignKey("tournament_reports.id")
    )
    tournament_report: Mapped[TournamentReport] = relationship(back_populates="stats")


class ComputedStatistic(Base):
    """A single statistic computed in bulk and persisted for fast serving."""

    __tablename__ = "computed_statistics"

    id: Mapped[int] = mapped_column(primary_key=True)
    stat_name: Mapped[str] = mapped_column(String)
    value_float: Mapped[float | None] = mapped_column(Float)
    value_str: Mapped[str | None] = mapped_column(String)
    player: Mapped[str | None] = mapped_column(String)
    match_id: Mapped[int | None] = mapped_column()
    date_computed: Mapped[date] = mapped_column(index=True)


# NOTE: "compostion" is a misspelling baked into the table name from an early
# migration. Renaming requires a Postgres ALTER TABLE + alembic revision; the
# typo is intentionally preserved everywhere it appears (model, attrs, debug
# payload keys) to avoid touching production. Do not "fix" without migrating.
class MatchCompostion(Base):
    __tablename__ = "match_compostion"

    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.match_id", ondelete="CASCADE"), primary_key=True
    )
    category: Mapped[str | None] = mapped_column(String)
    is_comp_stomp: Mapped[bool | None] = mapped_column()
    is_ffa: Mapped[bool | None] = mapped_column()
    num_teams: Mapped[int | None] = mapped_column()
    team_sizes: Mapped[list[int] | None] = mapped_column(ARRAY(Integer))
    total_players: Mapped[int | None] = mapped_column()
    num_humans: Mapped[int | None] = mapped_column()
    num_computers: Mapped[int | None] = mapped_column()
    is_balanced: Mapped[bool | None] = mapped_column()
    is_1v1: Mapped[bool | None] = mapped_column()
    is_team_game: Mapped[bool | None] = mapped_column()

    match: Mapped[Match] = relationship(back_populates="composition")


class MatchDetailsCache(Base):
    """Durable, versioned cache of the derived MatchDetails wire shape.

    The raw (multi-MB, cncstats-owned, format-volatile) parsed replay stays in
    S3. This table stores only the small, *we-own-it* projection served by
    `/api/details/{match_id}`, so the request path doesn't re-read and
    re-validate the giant blob on every hit (and survives process restarts,
    unlike the in-process LRU in `cache.py`).

    `data` is the JSON-serialized MatchDetails (by_alias, so keys match the wire
    shape). `version` is the `match_details.DETAILS_VERSION` that produced the
    row; a read only trusts a row whose version equals the current version, so
    bumping the derivation logic transparently invalidates every row. Rows are
    refreshed lazily on read (and explicitly deleted on reparse, when the raw
    replay changed but the version did not).
    """

    __tablename__ = "match_details_cache"

    match_id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[str] = mapped_column(String(64), index=True)
    data: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<MatchDetailsCache(match_id={self.match_id}, version={self.version})>"


class User(Base):
    """A community member authenticated via Discord OAuth2.

    `discord_id` is the stable Discord snowflake (the login identity).
    `player_name` is the in-game name the user claims from
    `player_ids.PLAYER_NAMES`; it is NULL until the user picks one on first
    login, and is unique so two Discord accounts can't claim the same player.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    discord_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    discord_username: Mapped[str] = mapped_column(String)
    discord_avatar: Mapped[str | None] = mapped_column(String, nullable=True)
    player_name: Mapped[str | None] = mapped_column(
        String, unique=True, index=True, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<User(id={self.id}, discord_id={self.discord_id}, "
            f"player_name={self.player_name})>"
        )


class MapVote(Base):
    """A logged-in user's vote or veto for a map, scoped to a player count.

    Votes and vetoes are per (user, player_count): a user may cast up to a
    fixed number of each (enforced in the repository, not the schema). A map can
    be voted OR vetoed but not both — one row per (user, player_count, map_name),
    with `choice` flipping between 'vote' and 'veto'.
    """

    __tablename__ = "map_votes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    player_count: Mapped[int] = mapped_column(SmallInteger, index=True)
    map_name: Mapped[str] = mapped_column(String)
    choice: Mapped[str] = mapped_column(String(8))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("choice in ('vote', 'veto')", name="check_vote_choice"),
        Index("idx_map_votes_user_count", "user_id", "player_count"),
        Index(
            "uq_map_votes_user_count_map",
            "user_id",
            "player_count",
            "map_name",
            unique=True,
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<MapVote(user_id={self.user_id}, player_count={self.player_count}, "
            f"map_name={self.map_name!r}, choice={self.choice})>"
        )


class MapData(Base):
    """Parsed map geometry data keyed by map name."""

    __tablename__ = "map_data"

    map_name: Mapped[str] = mapped_column(String, primary_key=True)
    data: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
