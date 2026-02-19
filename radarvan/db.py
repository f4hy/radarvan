from sqlalchemy import Column, Integer, String, Boolean, ARRAY, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import (
    Date,
    Float,
    Text,
    DateTime,
    CheckConstraint,
    Index,
    SmallInteger,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime
import enum
from sqlalchemy import Enum

Base = declarative_base()


class ProcessingStatus(enum.Enum):
    PENDING = "pending"
    SKIPPED = "skipped"
    PARSED = "parsed"
    FAILED = "failed"


class ReplayFile(Base):
    """Original replay files from HTTP URIs"""

    __tablename__ = "replay_files"

    original_url = Column(
        String, unique=True, primary_key=True, nullable=False, index=True
    )
    s3_uri = Column(String, unique=True, nullable=False, index=True)
    status = Column(
        Enum(ProcessingStatus),
        default=ProcessingStatus.PENDING,
        nullable=False,
        index=True,
    )
    player_id = Column(String, nullable=False, index=True)

    # Timestamps
    discovered_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    source_date = Column(Date, nullable=False, index=True)

    # Relationships
    parsed_replay_json = relationship(
        "ParsedReplayJson", back_populates="replay_file", uselist=False
    )

    def __repr__(self):
        return f"<ReplayFile(url={self.original_url}, status={self.status})>"


class ParsedReplayJson(Base):
    """Parsed replay data stored in S3"""

    __tablename__ = "parsed_replay_json"

    json_s3_uri = Column(String, primary_key=True, nullable=False)
    match_id = Column(Integer, nullable=False, index=True)
    replay_file_url = Column(
        String,
        ForeignKey("replay_files.original_url", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # File info
    num_time_stamps = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    game_timestamp = Column(DateTime, nullable=False)
    game_date = Column(Date, index=True)
    game_version = Column(String(10))
    has_enhanced_stats = Column(Boolean, nullable=True)
    # Relationships
    replay_file = relationship("ReplayFile", back_populates="parsed_replay_json")
    match = relationship(
        "Match", back_populates="replay_json", uselist=False, lazy="joined"
    )

    def __repr__(self):
        return (
            f"<ParsedReplayJson(s3_uri={self.json_s3_uri}, match_id={self.match_id})>"
        )


class Match(Base):
    __tablename__ = "matches"

    match_id = Column(
        Integer,
        primary_key=True,
        nullable=False,
    )
    json_s3_uri = Column(
        String,
        ForeignKey("parsed_replay_json.json_s3_uri", ondelete="CASCADE"),
        nullable=False,
    )
    timestamp = Column(DateTime(timezone=True), nullable=False)
    map = Column(String(100), nullable=False)
    winning_team_id = Column(SmallInteger)
    duration_minutes = Column(Float, nullable=False)
    filename = Column(String(255), nullable=False)
    incomplete = Column(String, default=False)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    game_version = Column(String(10))

    # Relationships
    replay_json = relationship("ParsedReplayJson", back_populates="match")
    players = relationship(
        "MatchPlayer",
        back_populates="match",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint("duration_minutes >= 0", name="check_duration_positive"),
        Index("idx_matches_timestamp", "timestamp"),
        Index("idx_matches_map", "map"),
        Index("idx_matches_winning_team", "winning_team_id"),
    )

    composition = relationship("MatchCompostion", back_populates="match", uselist=False)

    def __repr__(self):
        return f"<Match(match_id=`{self.match_id}` game_version=`{self.game_version}` \n`winner={self.winning_team_id}`\n updated_at=`{self.updated_at}` created_at=`{self.created_at}` players=\n{self.players})>"


class MatchPlayer(Base):
    __tablename__ = "match_players"

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(
        Integer, ForeignKey("matches.match_id", ondelete="CASCADE"), nullable=False
    )
    player_name = Column(String(100), nullable=False)
    general_id = Column(SmallInteger, nullable=False)
    team_id = Column(SmallInteger, nullable=False)
    color = Column(String(20), nullable=False)
    is_winner = Column(Boolean, nullable=False)

    match = relationship("Match", back_populates="players")

    __table_args__ = (
        Index("idx_match_players_match", "match_id"),
        Index("idx_match_players_player", "player_name"),
    )

    def __repr__(self):
        return f"<Player(name={self.player_name} general={self.general_id} team={self.team_id} winner={self.is_winner}) >\n"


class WinnerOverride(Base):
    __tablename__ = "winner_overrides"

    match_id = Column(
        Integer,
        primary_key=True,
        nullable=False,
    )
    winning_team_id = Column(SmallInteger, nullable=True)
    incomplete = Column(String, default=False)


class TournamentReport(Base):
    __tablename__ = "tournament_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    # Relationship to stats
    stats: Mapped[list["TournamentStat"]] = relationship(
        back_populates="tournament_report", cascade="all, delete-orphan"
    )


class TournamentStat(Base):
    __tablename__ = "tournament_stats"

    id: Mapped[int] = mapped_column(primary_key=True)
    stat_name: Mapped[str] = mapped_column(String, nullable=False)
    value_float: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_str: Mapped[str | None] = mapped_column(String, nullable=True)
    player: Mapped[str | None] = mapped_column(String, nullable=True)
    match_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Foreign key to tournament_report
    tournament_report_id: Mapped[int] = mapped_column(
        ForeignKey("tournament_reports.id"), nullable=False
    )

    # Relationship back to report
    tournament_report: Mapped["TournamentReport"] = relationship(back_populates="stats")


class MatchCompostion(Base):
    __tablename__ = "match_compostion"

    match_id = Column(
        Integer, ForeignKey("matches.match_id", ondelete="CASCADE"), primary_key=True
    )
    category = Column(String)
    is_comp_stomp = Column(Boolean)
    is_ffa = Column(Boolean)
    num_teams = Column(Integer)
    team_sizes = Column(ARRAY(Integer))
    total_players = Column(Integer)
    num_humans = Column(Integer)
    num_computers = Column(Integer)
    is_balanced = Column(Boolean)
    is_1v1 = Column(Boolean)
    is_team_game = Column(Boolean)

    # Optional: relationship back to game
    match = relationship("Match", back_populates="composition")
