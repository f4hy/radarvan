"""Head-to-head records between two players."""

# See radarvan/api_types/__init__.py for why this package is split by context.
# Needed so forward/self references resolve under Python < 3.14 (PEP 649 defers
# by default on 3.14+); required for the ml/ 3.13 training venv.
from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, date
from .common import General, _FROM_ATTRIBUTES


class HeadToHead(BaseModel):
    model_config = _FROM_ATTRIBUTES

    wins: int
    losses: int


class HeadToHeadGame(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    match_id: int = Field(alias="matchId")
    timestamp: datetime
    date: date
    map: str
    duration_minutes: float = Field(alias="durationMinutes")
    game_format: str | None = Field(default=None, alias="gameFormat")
    player1_general: General = Field(alias="player1General")
    player2_general: General = Field(alias="player2General")
    player1_won: bool = Field(alias="player1Won")
    player1_team: list[str] = Field(alias="player1Team")
    player2_team: list[str] = Field(alias="player2Team")
    # Value (build cost) of each other's stuff destroyed in this game - the
    # damage-dealt proxy, since replays don't carry raw HP. 0 when neither
    # killed anything of the other's (or MatchDetails wasn't available).
    player1_value_destroyed: int = Field(default=0, alias="player1ValueDestroyed")
    player2_value_destroyed: int = Field(default=0, alias="player2ValueDestroyed")


class HeadToHeadGeneralRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    general: General
    wins: int
    losses: int


class HeadToHeadMapRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    map: str
    player1_wins: int = Field(alias="player1Wins")
    player2_wins: int = Field(alias="player2Wins")


class HeadToHeadDetail(BaseModel):
    """Detailed head-to-head record between two players in opposite-team games,
    plus how often they've been teammates instead."""

    model_config = ConfigDict(populate_by_name=True)

    player1: str
    player2: str
    player1_wins: int = Field(alias="player1Wins")
    player2_wins: int = Field(alias="player2Wins")
    games: list[HeadToHeadGame]
    player1_by_general: list[HeadToHeadGeneralRecord] = Field(alias="player1ByGeneral")
    player2_by_general: list[HeadToHeadGeneralRecord] = Field(alias="player2ByGeneral")
    by_map: list[HeadToHeadMapRecord] = Field(alias="byMap")
    player1_value_destroyed: int = Field(default=0, alias="player1ValueDestroyed")
    player2_value_destroyed: int = Field(default=0, alias="player2ValueDestroyed")
    # Same-team games between these two, over the same `games` pool - a
    # symmetric, always-available count unlike PlayerProfile.favorite_teammate
    # (which is synergy-ranked and one-directional: it only surfaces a pair
    # when one player happens to be the *other's* top-synergy partner).
    teammate_games: int = Field(alias="teammateGames")
    teammate_wins: int = Field(alias="teammateWins")
