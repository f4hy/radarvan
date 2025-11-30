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
    match = relationship("Match", back_populates="replay_json", uselist=False)

    def __repr__(self):
        return (
            f"<ParsedReplayJson(s3_uri={self.json_s3_uri}, match_id={self.match_id})>"
        )


class General(enum.IntEnum):
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


class Team(enum.IntEnum):
    NONE = 0
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    OBSERVER = -1


# Lookup Tables
class GeneralModel(Base):
    __tablename__ = "generals"

    id = Column(SmallInteger, primary_key=True)
    name = Column(String(50), nullable=False, unique=True)

    # Relationships
    match_players = relationship("MatchPlayer", back_populates="general")


class TeamModel(Base):
    __tablename__ = "teams"

    id = Column(SmallInteger, primary_key=True)
    name = Column(String(20), nullable=False, unique=True)

    # Relationships
    matches_won = relationship(
        "Match", foreign_keys="Match.winning_team_id", back_populates="winning_team"
    )
    match_players = relationship("MatchPlayer", back_populates="team")


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
    winning_team_id = Column(SmallInteger, ForeignKey("teams.id"))
    duration_minutes = Column(Float, nullable=False)
    filename = Column(String(255), nullable=False)
    incomplete = Column(Boolean, default=False)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    replay_json = relationship("ParsedReplayJson", back_populates="match")
    winning_team = relationship(
        "TeamModel", foreign_keys=[winning_team_id], back_populates="matches_won"
    )
    players = relationship(
        "MatchPlayer", back_populates="match", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("duration_minutes >= 0", name="check_duration_positive"),
        Index("idx_matches_timestamp", "timestamp"),
        Index("idx_matches_map", "map"),
        Index("idx_matches_winning_team", "winning_team_id"),
    )


class MatchPlayer(Base):
    __tablename__ = "match_players"

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(
        Integer, ForeignKey("matches.match_id", ondelete="CASCADE"), nullable=False
    )
    player_name = Column(String(100), nullable=False)
    general_id = Column(SmallInteger, ForeignKey("generals.id"), nullable=False)
    team_id = Column(SmallInteger, ForeignKey("teams.id"), nullable=False)
    color = Column(String(20), nullable=False)
    is_winner = Column(Boolean, nullable=False)

    # Relationships
    match = relationship("Match", back_populates="players")
    general = relationship("GeneralModel", back_populates="match_players")
    team = relationship("TeamModel", back_populates="match_players")

    __table_args__ = (
        UniqueConstraint("match_id", "player_name", name="uq_match_player"),
        Index("idx_match_players_match", "match_id"),
        Index("idx_match_players_player", "player_name"),
        Index("idx_match_players_general", "general_id"),
        Index("idx_match_players_team", "team_id"),
    )
