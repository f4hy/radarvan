from datetime import datetime, date
import enum
from enum import IntEnum
from sqlalchemy import (
    ARRAY,
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    Float,
    DateTime,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


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

    # Timestamps
    discovered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
    game_timestamp: Mapped[datetime] = mapped_column(DateTime)
    game_date: Mapped[date | None] = mapped_column(index=True)
    game_version: Mapped[str | None] = mapped_column(String(10))
    has_enhanced_stats: Mapped[bool | None] = mapped_column()

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
    incomplete: Mapped[str | None] = mapped_column(String, default=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
    game_version: Mapped[str | None] = mapped_column(String(10))

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
    incomplete: Mapped[str | None] = mapped_column(String, default=False)


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

    tournament_report_id: Mapped[int] = mapped_column(
        ForeignKey("tournament_reports.id")
    )
    tournament_report: Mapped[TournamentReport] = relationship(back_populates="stats")


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
