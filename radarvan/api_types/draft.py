"""Draft / team-assignment requests and results."""

from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class DraftPlayerRequest(BaseModel):
    name: str
    team: int  # 1-4


class DraftRequest(BaseModel):
    map_name: str
    players: list[DraftPlayerRequest]


class DraftAssignment(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    player_name: str = Field(alias="playerName")
    team: int
    position_number: int = Field(alias="positionNumber")
    general: int


class DraftResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    assignments: list[DraftAssignment]
    randomized_at: datetime = Field(alias="randomizedAt")
