"""A match and its players, plus the raw replay/override rows behind it."""

from __future__ import annotations

from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    computed_field,
)
import functools
from datetime import datetime, date
from ..game_composition import GameComposition, MatchRoster
from ..player_role import PlayerRole, resolve_role
from .common import (
    General,
    Team,
    _FROM_ATTRIBUTES,
)


class Player(BaseModel):
    name: str
    general: General
    team: Team
    color: str
    won: bool = False
    starting_position: int | None = None
    # None for match_players rows written before the column existed; consumers
    # go through `role_or_guess()` rather than reading this directly.
    role: PlayerRole | None = None

    def role_or_guess(self) -> PlayerRole:
        """The recorded role, or a name-based guess for un-backfilled rows.

        Prefer going through ``MatchInfo.roster()`` - this exists for the two
        places that hold a lone Player with no match around it.
        """
        return resolve_role(
            self.role, self.name, self.color, is_observer=self.team == Team.OBSERVER
        )

    def __repr__(self) -> str:
        return f"{self.name}[{self.general.name} {'W' if self.won else 'L'}]"


class TournamentTag(BaseModel):
    """The tournament a match counted toward, if any.

    Denormalized onto MatchInfo from the ``tournament_games`` link so callers
    can tell tournament games apart without a second query. ``stage`` is the
    bracket match id ("WB2-2") and is None for round-robin games. Identity
    only - the display name lives on the tournament (``/api/tournaments``)
    rather than being copied onto every match of every listing.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    slug: str
    stage: str | None = None
    round_name: str | None = Field(default=None, alias="roundName")
    series_index: int | None = Field(default=None, alias="seriesIndex")


class MatchInfo(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    id: int
    timestamp: datetime
    date: date
    map: str
    winning_team: Team
    players: list[Player]
    duration_minutes: float
    filename: str
    incomplete: str = ""
    notes: str = ""
    game_version: str | None = None
    composition: GameComposition | None = None
    is_dev: bool = False
    tournament: TournamentTag | None = None

    @functools.cached_property
    def _roster(self) -> MatchRoster:
        # Cached because has_ai is a computed_field (so this runs on every
        # serialization) and the stats modules re-derive the same match's
        # roster several times per pass - map_summary alone asked ~5x per
        # match. Safe to cache: MatchInfo is frozen and nothing mutates
        # .players.
        return MatchRoster.from_players(self.players)

    def roster(self) -> MatchRoster:
        """This match's players, partitioned by role.

        **The** way to ask who observed, who played, and who was AI. Do not
        write a bare `team`/name check at a call site - see CLAUDE.md.
        """
        return self._roster

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_ai(self) -> bool:
        """True if any player is a CPU/AI opponent (see player_role.PlayerRole)."""
        return self.roster().has_cpu


class Matches(BaseModel):
    matches: list[MatchInfo]


class WinnerOverride(BaseModel):
    match_id: int
    winning_team_id: Team
    incomplete: str | None = None


class ReplayFileSchema(BaseModel):
    """Public API representation of ReplayFile"""

    model_config = _FROM_ATTRIBUTES

    original_url: str
    s3_uri: str
    status: str
    player_id: str
    discovered_at: datetime
    source_date: date


class ParsedReplayJsonSchema(BaseModel):
    """Public API representation of ParsedReplayJson"""

    model_config = _FROM_ATTRIBUTES

    json_s3_uri: str
    match_id: int
    replay_file_url: str
    num_time_stamps: int | None = None
    created_at: datetime
    game_timestamp: datetime
    game_date: date
    updated_at: datetime | None = None
    has_enhanced_stats: bool | None = None


class ReplayWithoutPlayerStats(BaseModel):
    """A parsed replay still missing player stats (backfill work item)."""

    model_config = _FROM_ATTRIBUTES

    match_id: int
    url: str
    s3_path: str
    version: str | None = None
    presigned_url: str
    all_replay_urls: list[str]


class ReplayDownload(BaseModel):
    """A presigned .rep URL plus the name the browser should save it under.

    The name travels with the URL because it is derived from the match (date,
    sides, map) rather than from the S3 key, which is a content hash.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    url: str
    filename: str
