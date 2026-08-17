"""Free-for-all statistics."""

# See radarvan/api_types/__init__.py for why this package is split by context.
# Needed so forward/self references resolve under Python < 3.14 (PEP 649 defers
# by default on 3.14+); required for the ml/ 3.13 training venv.
from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict
from .common import General


class FFAPlayerStat(BaseModel):
    """Per-player record across free-for-all games."""

    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    name: str
    games: int
    wins: int
    win_rate: float = Field(alias="winRate")
    # Expected wins if every player in each FFA were equally likely (sum of 1/N
    # over the player's games). Lets us judge a win rate against the field size.
    expected_wins: float = Field(alias="expectedWins")
    # Actual wins divided by expected wins: 1.0 == exactly average, >1 over-performing.
    dominance: float


class FFAGeneralStat(BaseModel):
    """Per-general win record across free-for-all games."""

    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    general: General
    games: int
    wins: int
    win_rate: float = Field(alias="winRate")


class FFAMapStat(BaseModel):
    """Per-map activity across free-for-all games."""

    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    map: str
    games: int
    avg_players: float = Field(alias="avgPlayers")


class FFARecentMatch(BaseModel):
    """Pointer to the most recently played FFA game."""

    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    match_id: int = Field(alias="matchId")
    winner: str


class FFAStats(BaseModel):
    """Everything the FFA page renders, computed over human free-for-all games."""

    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    total_games: int = Field(alias="totalGames")
    distinct_players: int = Field(alias="distinctPlayers")
    avg_players_per_game: float = Field(alias="avgPlayersPerGame")
    most_recent: FFARecentMatch | None = Field(default=None, alias="mostRecent")
    player_stats: list[FFAPlayerStat] = Field(alias="playerStats")
    general_stats: list[FFAGeneralStat] = Field(alias="generalStats")
    map_stats: list[FFAMapStat] = Field(alias="mapStats")
