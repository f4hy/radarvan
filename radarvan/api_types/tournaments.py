"""Tournament reports and their match listings."""

# See radarvan/api_types/__init__.py for why this package is split by context.
# Needed so forward/self references resolve under Python < 3.14 (PEP 649 defers
# by default on 3.14+); required for the ml/ 3.13 training venv.
from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, date
from .common import WinLoss, _FROM_ATTRIBUTES
from .matches import MatchInfo


# listing


class PlayerListing(BaseModel):
    model_config = _FROM_ATTRIBUTES

    id: int
    player_name: str
    team_id: int
    is_winner: bool
    general_id: int
    match_id: int
    color: str


class MatchListing(BaseModel):
    model_config = _FROM_ATTRIBUTES

    match_id: int
    map: str
    duration_minutes: float
    incomplete: str | None = None
    created_at: datetime
    json_s3_uri: str
    timestamp: datetime
    winning_team_id: int
    filename: str
    notes: str | None = None
    players: list[PlayerListing]


class GameRecord(BaseModel):
    model_config = _FROM_ATTRIBUTES

    json_s3_uri: str
    file_size_bytes: int | None = None
    game_timestamp: datetime
    match_id: int
    replay_file_url: str
    replay_presigned_url: str | None = None
    json_presigned_url: str | None = None
    created_at: datetime
    game_date: date
    game_version: str | None = None
    match: MatchListing | None = None


class Tournament(BaseModel):
    model_config = ConfigDict(frozen=True, slots=True)  # type: ignore[typeddict-unknown-key]

    name: str
    start_date: date
    end_date: date
    teams: list[tuple[str, ...]]
    total_games_played_per_team: int


class MatchupResult(BaseModel):
    tournament_name: str
    matches: list[MatchInfo]
    outcome: dict[tuple[str, ...], WinLoss]
    override: str | None = None


class Matchup(BaseModel):
    team1: tuple[str, ...]
    team2: tuple[str, ...]
    played: bool


class TournamentResult(BaseModel):
    tournament: Tournament
    matchups: list[MatchupResult]

    records: dict[tuple[str, ...], WinLoss]
    complete: bool


class Statistic(BaseModel):
    model_config = ConfigDict(frozen=True, slots=True)  # type: ignore[typeddict-unknown-key]

    stat_name: str
    date_computed: date
    value: float | str | None = None
    player: str | None = None
    match_id: int | None = None


class TournamentInfo(BaseModel):
    """A tournament in the registry, with how many games are linked to it."""

    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    slug: str
    name: str
    format: str
    status: str
    start_date: date | None = Field(default=None, alias="startDate")
    end_date: date | None = Field(default=None, alias="endDate")
    game_count: int = Field(default=0, alias="gameCount")


class TournamentReport(BaseModel):
    model_config = ConfigDict(frozen=True, slots=True)  # type: ignore[typeddict-unknown-key]

    name: str
    stats: list[Statistic]
