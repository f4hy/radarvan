"""Free-for-all statistics."""

from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict
from .common import General


class FFAPlayerStat(BaseModel):
    """Per-player record across free-for-all games."""

    model_config = ConfigDict(populate_by_name=True)

    name: str
    games: int
    wins: int
    win_rate: float = Field(alias="winRate")
    # Expected wins if every player in each FFA were equally likely (sum of 1/N
    # over the player's games). Lets us judge a win rate against the field size.
    expected_wins: float = Field(alias="expectedWins")
    # Actual wins divided by expected wins: 1.0 == exactly average, >1 over-performing.
    dominance: float
    # True for an AI row, which only appears when the caller asked for CPU games.
    # The page marks these instead of linking them to a player profile.
    is_cpu: bool = Field(default=False, alias="isCpu")


class FFAGeneralStat(BaseModel):
    """Per-general win record across free-for-all games."""

    model_config = ConfigDict(populate_by_name=True)

    general: General
    games: int
    wins: int
    win_rate: float = Field(alias="winRate")


class FFAMapStat(BaseModel):
    """Per-map activity across free-for-all games."""

    model_config = ConfigDict(populate_by_name=True)

    map: str
    games: int
    avg_players: float = Field(alias="avgPlayers")


class FFARecentMatch(BaseModel):
    """Pointer to the most recently played FFA game."""

    model_config = ConfigDict(populate_by_name=True)

    match_id: int = Field(alias="matchId")
    winner: str


class FFAStats(BaseModel):
    """Everything the FFA page renders, computed over human free-for-all games."""

    model_config = ConfigDict(populate_by_name=True)

    total_games: int = Field(alias="totalGames")
    distinct_players: int = Field(alias="distinctPlayers")
    avg_players_per_game: float = Field(alias="avgPlayersPerGame")
    most_recent: FFARecentMatch | None = Field(default=None, alias="mostRecent")
    player_stats: list[FFAPlayerStat] = Field(alias="playerStats")
    general_stats: list[FFAGeneralStat] = Field(alias="generalStats")
    map_stats: list[FFAMapStat] = Field(alias="mapStats")
