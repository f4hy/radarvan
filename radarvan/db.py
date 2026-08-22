"""SQLAlchemy ORM models - the database schema (``Match``, ``MatchPlayer``,
``ReplayFile``, ``ParsedReplayJson``, ``MatchDetailsCache``, ``User``, ``MapData``, …)
and the ``Base`` declarative class shared across the backend."""

# Needed so forward references (e.g. ReplayFile.parsed_replay_json -> ParsedReplayJson,
# defined later in this file) resolve under Python < 3.14, which evaluates annotations
# eagerly unless deferred like this. 3.14+ defers by default (PEP 649) so this is a
# no-op there - required for the ml/ 3.13 training venv (see pyproject.toml's ml group).
from __future__ import annotations

from datetime import UTC, datetime, date
import enum
from enum import IntEnum
from sqlalchemy import (
    ARRAY,
    CheckConstraint,
    Date,
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
    existing-stored-value semantics - i.e. wall-clock UTC).
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
    parsed_replay_json: Mapped[ParsedReplayJson | None] = relationship(
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
    match: Mapped[Match | None] = relationship(
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
    replay_json: Mapped[ParsedReplayJson | None] = relationship(back_populates="match")
    players: Mapped[list[MatchPlayer]] = relationship(
        back_populates="match",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    composition: Mapped[MatchCompostion | None] = relationship(back_populates="match")

    def __repr__(self) -> str:
        return (
            f"<Match(match_id=`{self.match_id}` game_version=`{self.game_version}` \n"
            f"`winner={self.winning_team_id}`\n"
            f" updated_at=`{self.updated_at}` created_at=`{self.created_at}` players=\n{self.players})>"
        )


# Identity of a match_players row within its match, as written by
# matches.replay_to_db_match: (player_name, color, team_id, general_id). Used
# to line stored rows up against freshly parsed replay players without
# depending on row order.
PlayerKey = tuple[str, str, int, int]


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
    # player_role.PlayerRole. Nullable for rows written before the column
    # existed; readers fall back to a name-based guess until the backfill
    # completes, after which this can be tightened to NOT NULL.
    role: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

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

    stats: Mapped[list[TournamentStat]] = relationship(
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


class Tournament(Base):
    """A tournament that was (or will be) run - the durable identity every
    tournament game hangs off.

    Deliberately separate from ``BracketTournament``: that table is a
    singleton whose reset deletes the row and cascades away its players,
    match states and predictions, so nothing anchored there survives the next
    bracket. This row does, which is what makes "every tournament game ever"
    answerable. ``BracketTournament.tournament_id`` points here.

    Structure lives elsewhere on purpose - the round-robin team list and
    games-per-team stay in ``tournament.TOURNAMENTS`` (the report needs them
    to enumerate *unplayed* pairings, which linked games can't tell you), and
    the bracket topology stays in ``bracket.py``. This table owns identity;
    ``TournamentGame`` owns membership.
    """

    __tablename__ = "tournaments"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    # "2v2_round_robin" | "1v1_double_elim" - see tournament_membership.py,
    # which switches detection strategy on this.
    format: Mapped[str] = mapped_column(String(32))
    start_date: Mapped[date | None] = mapped_column(nullable=True)
    end_date: Mapped[date | None] = mapped_column(nullable=True)
    # "upcoming" | "active" | "complete"
    status: Mapped[str] = mapped_column(String(16), default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    games: Mapped[list[TournamentGame]] = relationship(
        back_populates="tournament", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Tournament {self.slug} ({self.format})>"


class TournamentGame(Base):
    """A played match that counted as part of a tournament.

    ``match_id`` deliberately carries **no foreign key** to ``matches``:
    ``MatchRepo.reset_match`` deletes the Match row and a reparse re-inserts
    it under the same id, so ON DELETE CASCADE would silently destroy curated
    links during an ops reparse and RESTRICT would break the reset outright.
    Match ids are replay-derived and stable, so the plain indexed column is
    safe; readers skip ids with no current match (same shape as
    ``BracketPrediction.match_id``).

    ``stage``/``round_name`` are the bracket topology id ("WB2-2") and its
    human label, denormalized so they outlive a bracket reset; both are NULL
    for round-robin games. ``series_index`` is the game's position within a
    best-of series. ``source`` records how the link was made - a re-run of
    the auto-detector must never overwrite a "manual" row.
    """

    __tablename__ = "tournament_games"

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(
        ForeignKey("tournaments.id", ondelete="CASCADE"), index=True
    )
    match_id: Mapped[int] = mapped_column(index=True)
    stage: Mapped[str | None] = mapped_column(String(16), nullable=True)
    round_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    series_index: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    source: Mapped[str] = mapped_column(String(8), default="auto")
    # A tombstone: "the detector will keep finding this match, and it still
    # doesn't count" (warmups, a game replayed after a disconnect). Deleting
    # the row can't express that - the next detector run would just recreate
    # it - so an exclusion is a manual row that reads skip. This replaced a
    # hard-coded match id in tournament.tournament_games().
    excluded: Mapped[bool] = mapped_column(
        default=False, server_default="false", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index(
            "uq_tournament_games_tournament_match",
            "tournament_id",
            "match_id",
            unique=True,
        ),
        CheckConstraint("source in ('auto', 'manual')", name="check_link_source"),
    )

    tournament: Mapped[Tournament] = relationship(back_populates="games")

    def __repr__(self) -> str:
        return f"<TournamentGame match={self.match_id} stage={self.stage}>"


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


class PlayerProfileCache(Base):
    """Durable, versioned per-player profile deep stats.

    One JSONB row per profiled player holding the serialized
    PlayerProfileComputed (by_alias). `version` is the
    `player_profile.PROFILE_VERSION` that produced the row; a read only trusts
    a matching version, so bumping the derivation invalidates every row.
    Profiles are always recomputed as a whole batch (percentiles are relative
    to the profiled population), never per player.
    """

    __tablename__ = "player_profiles"

    player: Mapped[str] = mapped_column(String, primary_key=True)
    version: Mapped[str] = mapped_column(String(64), index=True)
    data: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<PlayerProfileCache(player={self.player}, version={self.version})>"


class MatchupCommentaryCache(Base):
    """Durable cache of AI-generated pre-game matchup commentary.

    Keyed on (player1, player2, round_name) - the exact identifiers a
    matchup commentary request carries (see MatchupCommentaryRequest).
    Generation is a real, billed LLM call (radarvan.commentary), so once a
    row exists for a triple it's served on every later request instead of
    regenerating. No version/invalidation scheme here unlike
    MatchDetailsCache/PlayerProfileCache - if the prompt changes and old
    commentary should be regenerated, delete the affected rows by hand.
    """

    __tablename__ = "matchup_commentary_cache"

    player1: Mapped[str] = mapped_column(String, primary_key=True)
    player2: Mapped[str] = mapped_column(String, primary_key=True)
    round_name: Mapped[str] = mapped_column(String, primary_key=True)
    commentary: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<MatchupCommentaryCache(player1={self.player1!r}, "
            f"player2={self.player2!r}, round_name={self.round_name!r})>"
        )


class BracketSummaryCache(Base):
    """Durable cache of the AI-generated post-game recap of one bracket set.

    Keyed on (tournament_id, stage) - the *durable* Tournament the bracket
    writes its game links to, plus the bracket match id ("WB1-1"). Not the
    BracketTournament row: that one is deleted and recreated on every bracket
    reset, which would throw away recaps of sets that were actually played.
    The pair is also exactly the key TournamentGame links use, so a row and
    the games it describes are identified the same way.

    Generation is a real, billed LLM call (radarvan.commentary), so once a
    row exists it's served on every later request. Same no-version policy as
    MatchupCommentaryCache: if the prompt changes and old recaps should be
    regenerated, delete the affected rows (or use the route's admin-only
    force_refresh).
    """

    __tablename__ = "bracket_summary_cache"

    tournament_id: Mapped[int] = mapped_column(
        ForeignKey("tournaments.id", ondelete="CASCADE"), primary_key=True
    )
    stage: Mapped[str] = mapped_column(String(16), primary_key=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<BracketSummaryCache(tournament_id={self.tournament_id}, "
            f"stage={self.stage!r})>"
        )


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
    be voted OR vetoed but not both - one row per (user, player_count, map_name),
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
    # Game map CRC as an uppercase hex string (e.g. "5BB89B36"), matching the
    # replay header MapCRC. Used to register/look the map up on cncstats.
    crc: Mapped[str | None] = mapped_column(String, nullable=True)
    # When set, cncstats is known to have this map (we pushed it, or /map_exists
    # confirmed it). Used to skip maps already registered on the next push run.
    cncstats_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # SHA-256 of the local `mapparse` binary that produced `data`. NULL for rows
    # from before this column existed. Compared against the current binary's hash
    # (missing_maps.mapparse_bin_hash()) to find rows that predate a binary
    # rebuild and need `POST /api/reparse_maps` - see missing_maps.reparse_stored_map.
    mapparse_bin_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class BracketTournament(Base):
    """Singleton row for the current 1v1 double-elimination bracket.

    Only one row exists at a time - creating/resetting a bracket deletes the
    existing row (BracketPlayer/BracketMatchState cascade with it) and
    inserts a fresh one. See radarvan/bracket.py for the 9-16 entrant
    topology (a fixed 16-slot bracket with byes for smaller fields); this
    table (plus BracketPlayer/BracketMatchState) only stores the seeding and
    per-match results, not the bracket shape itself.
    """

    __tablename__ = "bracket_tournaments"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # When the bracket becomes visible to non-admins (players/matchups shown;
    # before this only the roster and blank bracket structure are visible).
    # NULL = already revealed (no gate). Compared against the server clock in
    # routes/bracket.py, never trusted from the client.
    reveal_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # The durable Tournament this bracket belongs to. Nullable because
    # brackets created before the tournaments registry existed have none, and
    # because the bracket stays usable without one. Nothing cascades from
    # here - deleting/resetting the bracket must not take the tournament (or
    # its TournamentGame links) with it; that's the whole point of the split.
    tournament_id: Mapped[int | None] = mapped_column(
        ForeignKey("tournaments.id"), nullable=True
    )

    players: Mapped[list[BracketPlayer]] = relationship(
        back_populates="tournament", cascade="all, delete-orphan"
    )
    match_states: Mapped[list[BracketMatchState]] = relationship(
        back_populates="tournament", cascade="all, delete-orphan"
    )


class BracketPlayer(Base):
    """One seeded entrant in the current bracket tournament."""

    __tablename__ = "bracket_players"

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(
        ForeignKey("bracket_tournaments.id", ondelete="CASCADE"), index=True
    )
    seed: Mapped[int] = mapped_column(SmallInteger)
    player_name: Mapped[str] = mapped_column(String(100))

    __table_args__ = (
        Index(
            "uq_bracket_players_tournament_seed",
            "tournament_id",
            "seed",
            unique=True,
        ),
    )

    tournament: Mapped[BracketTournament] = relationship(back_populates="players")


class BracketMatchState(Base):
    """Mutable per-match state (date/best-of/score) for a bracket match.

    ``match_id`` is one of the static ids from radarvan/bracket.py's
    TOPOLOGY (e.g. "WB1-1", "LB2a-1", "GF-2") - the bracket shape/routing
    lives in code; this table only stores what an admin entered.
    """

    __tablename__ = "bracket_match_state"

    tournament_id: Mapped[int] = mapped_column(
        ForeignKey("bracket_tournaments.id", ondelete="CASCADE"), primary_key=True
    )
    match_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    # An admin-set instant the match is expected to be played, independent of
    # whether it's actually been played yet (see best_of/score_a/score_b
    # below) - same idiom as BracketTournament.reveal_at.
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    best_of: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    score_a: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    score_b: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    # The Discord Guild Scheduled Event mirroring `scheduled_at`, so a
    # reschedule PATCHes that event instead of creating a duplicate. NULL
    # when discord_events isn't configured or the match isn't scheduled.
    discord_event_id: Mapped[str | None] = mapped_column(String(32), nullable=True)

    tournament: Mapped[BracketTournament] = relationship(back_populates="match_states")


class BracketPrediction(Base):
    """A logged-in user's "who wins this match" pick - a community hype
    feature, not authoritative (``BracketMatchState.score_a/b`` via
    ``resolve_bracket`` is the real result). One row per (tournament, match,
    user); relies on the FK's ``ondelete="CASCADE"`` to clear out with the
    tournament on reset, same as BracketPlayer/BracketMatchState.
    """

    __tablename__ = "bracket_predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(
        ForeignKey("bracket_tournaments.id", ondelete="CASCADE"), index=True
    )
    match_id: Mapped[str] = mapped_column(String(16))
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    predicted_winner: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    __table_args__ = (
        Index(
            "uq_bracket_predictions_tournament_match_user",
            "tournament_id",
            "match_id",
            "user_id",
            unique=True,
        ),
    )


class GameNightSummaryCache(Base):
    """Durable store of the once-a-night, LLM-written game-night recap.

    Keyed on the game-night date (``utils.game_night_date``, US Eastern with a
    5am rollover) - not a calendar UTC date, so a row lines up with exactly the
    set of matches the recap page shows for that night.

    Unlike every other cache table here, this one is never populated to serve a
    request. The nightly scheduler job writes at most one row per run, for the
    most recently *closed* night, and the read path returns null on a miss (see
    routes/game_night.py). That is what keeps the spend bounded and predictable:
    a night that predates the feature has no row and never gets one, so browsing
    back through the archive can't trigger generation.

    ``match_count`` records how many matches the summary was written from, so a
    row can be recognised as describing a night that has since gained games
    (a late upload) without re-reading the text.
    """

    __tablename__ = "game_night_summary_cache"

    night_date: Mapped[date] = mapped_column(Date, primary_key=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    match_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<GameNightSummaryCache(night_date={self.night_date!r}, "
            f"match_count={self.match_count!r})>"
        )
