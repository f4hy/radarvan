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
    UNRECOGNIZED = -1


class Player(BaseModel):
    name: str
    general: General
    team: Team


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
    stats: List[GeneralWL] 
    faction_stats: List[PlayerStatFactionWL] = Field(default=[], alias="factionStats")
    over_time: List[PlayerRateOverTime] = Field(default=[], alias="overTime")

    class Config:
        populate_by_name = True


class PlayerStats(BaseModel):
    player_stats: List[PlayerStat] = Field(default=[], alias="playerStats")

    class Config:
        populate_by_name = True


class GeneralStatPlayerWL(BaseModel):
    player_name: str = Field(alias="playerName")
    win_loss: Optional[WinLoss] = Field(default=None, alias="winLoss")

    class Config:
        populate_by_name = True


class GeneralStat(BaseModel):
    general: General
    stats: List[GeneralStatPlayerWL] = []
    total: Optional[WinLoss] = None


class GeneralStats(BaseModel):
    general_stats: List[GeneralStat] = Field(alias="generalStats")

    class Config:
        populate_by_name = True


class TeamStat(BaseModel):
    date: Optional[DateMessage] = None
    team: Team = Team.NONE
    wins: int = 0


class TeamStats(BaseModel):
    team_stats: List[TeamStat] = Field(default=[], alias="teamStats")

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
    results: List[MapResult] = []


class MapStats(BaseModel):
    map_stats: List[MapStat] = Field(default=[], alias="mapStats")
    over_time: Dict[str, MapResults] = Field(default={}, alias="overTime")

    class Config:
        populate_by_name = True


class SaveResponse(BaseModel):
    success: bool = False


class CostsBuiltObject(BaseModel):
    name: str
    count: int = 0
    total_spent: int = Field(default=0, alias="totalSpent")

    class Config:
        populate_by_name = True


class Costs(BaseModel):
    player: Optional[Player] = None
    buildings: List[CostsBuiltObject] = []
    units: List[CostsBuiltObject] = []
    upgrades: List[CostsBuiltObject] = []


class APM(BaseModel):
    player_name: str = Field(alias="playerName")
    action_count: int = Field(default=0, alias="actionCount")
    minutes: float = 0.0
    apm: float = 0.0

    class Config:
        populate_by_name = True


class UpgradeEvent(BaseModel):
    player_name: str = Field(alias="playerName")
    timecode: int = 0
    upgrade_name: str = Field(alias="upgradeName")
    cost: int = 0
    at_minute: float = Field(default=0.0, alias="atMinute")

    class Config:
        populate_by_name = True


class Spent(BaseModel):
    player_name: str = Field(alias="playerName")
    acc_cost: int = Field(default=0, alias="accCost")
    at_minute: float = Field(default=0.0, alias="atMinute")

    class Config:
        populate_by_name = True


class Upgrades(BaseModel):
    upgrades: List[UpgradeEvent] = []


class SpentOverTime(BaseModel):
    buildings: List[Spent] = []
    units: List[Spent] = []
    upgrades: List[Spent] = []
    total: List[Spent] = []


class MatchDetails(BaseModel):
    match_id: int = Field(default=0, alias="matchId")
    costs: List[Costs] = []
    apms: List[APM] = []
    upgrade_events: Dict[str, Upgrades] = Field(default={}, alias="upgradeEvents")
    spent: Optional[SpentOverTime] = None

    class Config:
        populate_by_name = True


class PairWinLoss(BaseModel):
    general1: General
    general2: General
    winloss: Optional[WinLoss] = None


class PairFactionWinLoss(BaseModel):
    faction1: Faction = Faction.ANYUSA
    faction2: Faction = Faction.ANYUSA
    winloss: Optional[WinLoss] = None


class PairsWinLosses(BaseModel):
    pairwl: List[PairWinLoss] = []


class PairFactionWinLosses(BaseModel):
    pairwl: List[PairFactionWinLoss] = []


class TeamPairs(BaseModel):
    team_pairs: Dict[str, PairsWinLosses] = Field(default={}, alias="teamPairs")
    faction_pairs: Dict[str, PairFactionWinLosses] = Field(
        default={}, alias="factionPairs"
    )

    class Config:
        populate_by_name = True


