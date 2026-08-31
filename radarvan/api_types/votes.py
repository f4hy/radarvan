"""Map voting."""

from __future__ import annotations

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal


MapVoteChoice = Literal["vote", "veto"]


class MapVoteOption(BaseModel):
    map_name: str
    game_count: int
    last_played: datetime | None = None
    days_since_last_played: int | None = None
    # The logged-in viewer's pick for this map (None if unset or logged out).
    my_choice: MapVoteChoice | None = None


class MapVotePage(BaseModel):
    player_count: int
    logged_in: bool
    vote_limit: int
    veto_limit: int
    votes_used: int
    vetoes_used: int
    # Maps for this player count, ordered by total games played (desc).
    maps: list[MapVoteOption] = Field(default_factory=list)


class SetMapVoteRequest(BaseModel):
    map_name: str
    # None clears the viewer's pick for this map.
    choice: MapVoteChoice | None = None
