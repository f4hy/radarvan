from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from enum import IntEnum


class General(IntEnum):
    USA = 0
    AIR = 1
    LASER = 2
    SUPER = 3
    CHINA = 4
    NUKE = 5
    TANK = 6
    INFANTRY = 7
    GLA = 8
    TOXIN = 9
    STEALTH = 10
    DEMO = 11
    UNRECOGNIZED = -1


class Faction(IntEnum):
    ANYUSA = 0
    ANYCHINA = 1
    ANYGLA = 2
    UNRECOGNIZED = -1


class Team(IntEnum):
    NONE = 0
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    OBSERVER = -1


class Player(BaseModel):
    name: str
    general: General
    team: Team
    color: str


class MatchInfo(BaseModel):
    id: int
    timestamp: datetime
    map: str
    winning_team: Team
    players: List[Player]
    duration_minutes: float
    filename: str
    incomplete: str
    notes: str

    class Config:
        populate_by_name = True


class Matches(BaseModel):
    matches: List[MatchInfo]


class WinLoss(BaseModel):
    wins: int
    losses: int


class GeneralWL(BaseModel):
    general: General
    win_loss: WinLoss = Field(alias="winLoss")

    class Config:
        populate_by_name = True


class DateMessage(BaseModel):
    year: int = Field(alias="Year")
    month: int = Field(alias="Month")
    day: int = Field(alias="Day")

    class Config:
        populate_by_name = True


class PlayerRateOverTime(BaseModel):
    date: DateMessage
    wl: GeneralWL


class PlayerStatFactionWL(BaseModel):
    faction: Faction = Faction.ANYUSA
    win_loss: Optional[WinLoss] = Field(default=None, alias="winLoss")

    class Config:
        populate_by_name = True


class PlayerStat(BaseModel):
    player_name: str = Field(alias="playerName")
    stats: dict[General, WinLoss]
    faction_stats: List[PlayerStatFactionWL] = Field(alias="factionStats")
    over_time: List[PlayerRateOverTime] = Field(alias="overTime")

    class Config:
        populate_by_name = True


class PlayerStats(BaseModel):
    player_stats: List[PlayerStat] = Field(alias="playerStats")

    class Config:
        populate_by_name = True


class GeneralStatPlayerWL(BaseModel):
    player_name: str = Field(alias="playerName")
    win_loss: Optional[WinLoss] = Field(default=None, alias="winLoss")

    class Config:
        populate_by_name = True


class GeneralStat(BaseModel):
    general: General
    stats: List[GeneralStatPlayerWL]
    total: WinLoss


class GeneralStats(BaseModel):
    general_stats: List[GeneralStat] = Field(alias="generalStats")

    class Config:
        populate_by_name = True


class TeamStat(BaseModel):
    date: Optional[DateMessage] = None
    team: Team = Team.NONE
    wins: int = 0


class TeamStats(BaseModel):
    team_stats: List[TeamStat] = Field(alias="teamStats")

    class Config:
        populate_by_name = True


class MapStat(BaseModel):
    map: str = ""
    team: Team = Team.NONE
    wins: int = 0


class MapResult(BaseModel):
    map: str = ""
    date: Optional[DateMessage] = None
    winner: Team = Team.NONE


class MapResults(BaseModel):
    results: List[MapResult]


class MapStats(BaseModel):
    map_stats: List[MapStat] = Field(alias="mapStats")
    over_time: Dict[str, MapResults] = Field(alias="overTime")

    class Config:
        populate_by_name = True


class SaveResponse(BaseModel):
    success: bool = False


class CostsBuiltObject(BaseModel):
    name: str
    count: int
    total_spent: int = Field(alias="totalSpent")

    class Config:
        populate_by_name = True


class Costs(BaseModel):
    player: Optional[Player]
    buildings: List[CostsBuiltObject]
    units: List[CostsBuiltObject]
    upgrades: List[CostsBuiltObject]


class APM(BaseModel):
    player_name: str = Field(alias="playerName")
    action_count: int = Field(alias="actionCount")
    minutes: float
    apm: float

    class Config:
        populate_by_name = True


class UpgradeEvent(BaseModel):
    player_name: str = Field(alias="playerName")
    timecode: int = 0
    upgrade_name: str = Field(alias="upgradeName")
    cost: int
    at_minute: float = Field(alias="atMinute")

    class Config:
        populate_by_name = True


class Spent(BaseModel):
    player_name: str = Field(alias="playerName")
    acc_cost: int = Field(alias="accCost")
    at_minute: float = Field(alias="atMinute")

    class Config:
        populate_by_name = True


class Upgrades(BaseModel):
    upgrades: List[UpgradeEvent]


class SpentOverTime(BaseModel):
    buildings: List[Spent]
    units: List[Spent]
    upgrades: List[Spent]
    total: List[Spent]


class ObjectSummary(BaseModel):
    Count: int
    TotalSpent: int


class PlayerSummary(BaseModel):
    Name: str
    Side: str
    Team: int
    Win: bool
    Color: str
    MoneySpent: int
    UnitsCreated: dict[str, ObjectSummary]
    BuildingsBuilt: dict[str, ObjectSummary]
    UpgradesBuilt: dict[str, ObjectSummary]
    PowersUsed: dict[str, int]


class MatchDetails(BaseModel):
    match_id: int = Field(alias="matchId")
    costs: List[Costs]
    apms: List[APM]
    upgrade_events: dict[str, Upgrades] = Field(alias="upgradeEvents")
    spent: SpentOverTime
    money_values: dict[int, dict[str, int]] = Field(
        description="at a time value (int) map each player to the value"
    )
    player_summary: list[PlayerSummary]

    class Config:
        populate_by_name = True


class PairWinLoss(BaseModel):
    general1: General
    general2: General
    winloss: Optional[WinLoss]


class PairFactionWinLoss(BaseModel):
    faction1: Faction = Faction.ANYUSA
    faction2: Faction = Faction.ANYUSA
    winloss: Optional[WinLoss]


class PairsWinLosses(BaseModel):
    pairwl: List[PairWinLoss]


class PairFactionWinLosses(BaseModel):
    pairwl: List[PairFactionWinLoss]


class TeamPairs(BaseModel):
    team_pairs: dict[str, PairsWinLosses] = Field(alias="teamPairs")
    faction_pairs: dict[str, PairFactionWinLosses] = Field(alias="factionPairs")

    class Config:
        populate_by_name = True
