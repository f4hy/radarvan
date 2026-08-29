"""Aggregate per-player statistics."""

# See radarvan/api_types/__init__.py for why this package is split by context.
# Needed so forward/self references resolve under Python < 3.14 (PEP 649 defers
# by default on 3.14+); required for the ml/ 3.13 training venv.
from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict
from .common import (
    DateMessage,
    Faction,
    General,
    WinLoss,
)


class GeneralWL(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    general: General
    win_loss: WinLoss = Field(alias="winLoss")


class PlayerRateOverTime(BaseModel):
    date: DateMessage
    wl: GeneralWL


class PlayerStatFactionWL(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    faction: Faction = Faction.ANYUSA
    win_loss: WinLoss | None = Field(default=None, alias="winLoss")


class PlayerStat(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    player_name: str = Field(alias="playerName")
    stats: dict[General, WinLoss]
    faction_stats: list[PlayerStatFactionWL] = Field(alias="factionStats")
    over_time: list[PlayerRateOverTime] = Field(alias="overTime")
    game_counts: dict[str, int] = Field(default_factory=dict, alias="gameCounts")


class PlayerStats(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    player_stats: list[PlayerStat] = Field(alias="playerStats")


class PlayerGameCount(BaseModel):
    name: str
    count: int
