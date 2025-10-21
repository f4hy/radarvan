from sqlalchemy import (
    Column,
    Integer,
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
from enum import IntEnum

Base = declarative_base()


# Enums (keep your existing ones)
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


class Team(IntEnum):
    NONE = 0
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    OBSERVER = -1


class Faction(IntEnum):
    ANYUSA = 0
    ANYCHINA = 1
    ANYGLA = 2
    UNRECOGNIZED = -1


# Lookup Tables
class GeneralModel(Base):
    __tablename__ = "generals"

    id = Column(SmallInteger, primary_key=True)
    name = Column(String(50), nullable=False, unique=True)
    faction = Column(String(20), nullable=False)

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


# Main Tables
class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    map = Column(String(100), nullable=False)
    winning_team_id = Column(SmallInteger, ForeignKey("teams.id"))
    duration_minutes = Column(Float, nullable=False)
    filename = Column(String(255), nullable=False)
    incomplete = Column(String(255))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    winning_team = relationship(
        "TeamModel", foreign_keys=[winning_team_id], back_populates="matches_won"
    )
    players = relationship(
        "MatchPlayer", back_populates="match", cascade="all, delete-orphan"
    )
    apm_data = relationship(
        "MatchPlayerAPM", back_populates="match", cascade="all, delete-orphan"
    )
    objects = relationship(
        "MatchPlayerObject", back_populates="match", cascade="all, delete-orphan"
    )
    upgrade_events = relationship(
        "MatchUpgradeEvent", back_populates="match", cascade="all, delete-orphan"
    )
    spending_timeline = relationship(
        "MatchSpendingTimeline", back_populates="match", cascade="all, delete-orphan"
    )
    money_timeline = relationship(
        "MatchMoneyTimeline", back_populates="match", cascade="all, delete-orphan"
    )
    powers = relationship(
        "MatchPlayerPower", back_populates="match", cascade="all, delete-orphan"
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
        Integer, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False
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


class MatchPlayerAPM(Base):
    __tablename__ = "match_player_apm"

    match_id = Column(
        Integer, ForeignKey("matches.id", ondelete="CASCADE"), primary_key=True
    )
    player_name = Column(String(100), primary_key=True)
    action_count = Column(Integer, nullable=False)
    minutes = Column(Float, nullable=False)
    apm = Column(Float, nullable=False)

    # Relationships
    match = relationship("Match", back_populates="apm_data")

    __table_args__ = (Index("idx_apm_player", "player_name"),)


class ObjectType(Base):
    __tablename__ = "object_types"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    category = Column(String(20), nullable=False)

    # Relationships
    match_objects = relationship("MatchPlayerObject", back_populates="object_type")

    __table_args__ = (
        CheckConstraint(
            "category IN ('UNIT', 'BUILDING', 'UPGRADE', 'POWER')",
            name="check_object_category",
        ),
    )


class MatchPlayerObject(Base):
    __tablename__ = "match_player_objects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(
        Integer, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False
    )
    player_name = Column(String(100), nullable=False)
    object_type_id = Column(Integer, ForeignKey("object_types.id"), nullable=False)
    count = Column(Integer, nullable=False)
    total_spent = Column(Integer, nullable=False)

    # Relationships
    match = relationship("Match", back_populates="objects")
    object_type = relationship("ObjectType", back_populates="match_objects")

    __table_args__ = (
        CheckConstraint("count >= 0", name="check_count_positive"),
        CheckConstraint("total_spent >= 0", name="check_spent_positive"),
        UniqueConstraint(
            "match_id", "player_name", "object_type_id", name="uq_match_player_object"
        ),
        Index("idx_objects_match_player", "match_id", "player_name"),
        Index("idx_objects_type", "object_type_id"),
    )


class MatchUpgradeEvent(Base):
    __tablename__ = "match_upgrade_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(
        Integer, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False
    )
    player_name = Column(String(100), nullable=False)
    upgrade_name = Column(String(100), nullable=False)
    timecode = Column(Integer, nullable=False)
    cost = Column(Integer, nullable=False)
    at_minute = Column(Float, nullable=False)

    # Relationships
    match = relationship("Match", back_populates="upgrade_events")

    __table_args__ = (
        Index("idx_upgrade_events_match", "match_id"),
        Index("idx_upgrade_events_player", "player_name"),
        Index("idx_upgrade_events_time", "match_id", "at_minute"),
    )


class MatchSpendingTimeline(Base):
    __tablename__ = "match_spending_timeline"

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(
        Integer, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False
    )
    player_name = Column(String(100), nullable=False)
    at_minute = Column(Float, nullable=False)
    category = Column(String(20), nullable=False)
    accumulated_cost = Column(Integer, nullable=False)

    # Relationships
    match = relationship("Match", back_populates="spending_timeline")

    __table_args__ = (
        CheckConstraint(
            "category IN ('BUILDINGS', 'UNITS', 'UPGRADES', 'TOTAL')",
            name="check_spending_category",
        ),
        Index("idx_spending_match_player", "match_id", "player_name", "category"),
        Index("idx_spending_time", "match_id", "at_minute"),
    )


class MatchMoneyTimeline(Base):
    __tablename__ = "match_money_timeline"

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(
        Integer, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False
    )
    timecode = Column(Integer, nullable=False)
    player_name = Column(String(100), nullable=False)
    money_value = Column(Integer, nullable=False)

    # Relationships
    match = relationship("Match", back_populates="money_timeline")

    __table_args__ = (
        Index("idx_money_match_time", "match_id", "timecode"),
        Index("idx_money_player", "player_name"),
    )


class MatchPlayerPower(Base):
    __tablename__ = "match_player_powers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(
        Integer, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False
    )
    player_name = Column(String(100), nullable=False)
    power_name = Column(String(100), nullable=False)
    use_count = Column(Integer, nullable=False)

    # Relationships
    match = relationship("Match", back_populates="powers")

    __table_args__ = (
        CheckConstraint("use_count >= 0", name="check_use_count_positive"),
        UniqueConstraint(
            "match_id", "player_name", "power_name", name="uq_match_player_power"
        ),
        Index("idx_powers_match_player", "match_id", "player_name"),
    )
