"""Draft / team-assignment requests and results."""

# See radarvan/api_types/__init__.py for why this package is split by context.
# Needed so forward/self references resolve under Python < 3.14 (PEP 649 defers
# by default on 3.14+); required for the ml/ 3.13 training venv.
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
    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    player_name: str = Field(alias="playerName")
    team: int
    position_number: int = Field(alias="positionNumber")
    general: int


class DraftResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    assignments: list[DraftAssignment]
    randomized_at: datetime = Field(alias="randomizedAt")
