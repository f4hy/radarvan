"""Team and teammate-pair statistics."""

from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict
from .common import (
    DateMessage,
    Faction,
    General,
    Team,
    WinLoss,
)


class TeamStat(BaseModel):
    date: DateMessage | None = None
    team: Team = Team.NONE
    wins: int = 0


class TeamStats(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    team_stats: list[TeamStat] = Field(alias="teamStats")


class TeamRecord(BaseModel):
    players: list[str]
    wins: int
    losses: int


class TeamSizeGroup(BaseModel):
    size: int
    teams: list[TeamRecord]


class TeamStatsResponse(BaseModel):
    groups: list[TeamSizeGroup]


class PairWinLoss(BaseModel):
    general1: General
    general2: General
    winloss: WinLoss | None


class PairFactionWinLoss(BaseModel):
    faction1: Faction = Faction.ANYUSA
    faction2: Faction = Faction.ANYUSA
    winloss: WinLoss | None


class PairsWinLosses(BaseModel):
    pairwl: list[PairWinLoss]


class PairFactionWinLosses(BaseModel):
    pairwl: list[PairFactionWinLoss]


class TeamPairs(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    team_pairs: dict[str, PairsWinLosses] = Field(alias="teamPairs")
    faction_pairs: dict[str, PairFactionWinLosses] = Field(alias="factionPairs")
