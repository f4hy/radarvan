from sqlalchemy import (
    Column,
    Integer,
    Date,
    String,
    Float,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    Index,
    SmallInteger,
)
from sqlalchemy.orm import declarative_base, relationship
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
    parsed_at = Column(DateTime, nullable=True)

    # Error tracking
    error_message = Column(Text, nullable=True)

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
    file_size_bytes = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    game_timestamp = Column(DateTime, nullable=False)
    game_date = Column(Date, index=True)
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

    def __repr__(self):
        date = self.updated_at or self.created_at
        return f"<Match(match_id=`{self.match_id}` \n`winner={self.winning_team_id}`\n `{date}` players=\n{self.players})>"


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
        return f"<Player(name={self.player_name} general={self.general_id.name} team={self.team_id.name} winner={self.is_winner}) >\n"


class WinnerOverride(Base):
    __tablename__ = "winner_overrides"

    match_id = Column(
        Integer,
        primary_key=True,
        nullable=False,
    )
    winning_team_id = Column(SmallInteger, nullable=True)
    incomplete = Column(String, default=False)
