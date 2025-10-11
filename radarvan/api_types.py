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
    name: str = ""
    general: General = General.USA
    team: Team = Team.NONE


class MatchInfo(BaseModel):
    id: int = 0
    timestamp: Optional[datetime] = None
    map: str = ""
    winning_team: Team = Field(default=Team.NONE, alias="winningTeam")
    players: List[Player] = []
    duration_minutes: float = Field(default=0.0, alias="durationMinutes")
    filename: str = ""
    incomplete: str = ""
    notes: str = ""

    class Config:
        populate_by_name = True


class Matches(BaseModel):
    matches: List[MatchInfo] = []


class WinLoss(BaseModel):
    wins: int = 0
    losses: int = 0


class GeneralWL(BaseModel):
    general: General = General.USA
    win_loss: Optional[WinLoss] = Field(default=None, alias="winLoss")

    class Config:
        populate_by_name = True


class DateMessage(BaseModel):
    year: int = Field(default=0, alias="Year")
    month: int = Field(default=0, alias="Month")
    day: int = Field(default=0, alias="Day")

    class Config:
        populate_by_name = True


class PlayerRateOverTime(BaseModel):
    date: Optional[DateMessage] = None
    wl: Optional[GeneralWL] = None


class PlayerStatFactionWL(BaseModel):
    faction: Faction = Faction.ANYUSA
    win_loss: Optional[WinLoss] = Field(default=None, alias="winLoss")

    class Config:
        populate_by_name = True


class PlayerStat(BaseModel):
    player_name: str = Field(default="", alias="playerName")
    stats: List[GeneralWL] = []
    faction_stats: List[PlayerStatFactionWL] = Field(default=[], alias="factionStats")
    over_time: List[PlayerRateOverTime] = Field(default=[], alias="overTime")

    class Config:
        populate_by_name = True


class PlayerStats(BaseModel):
    player_stats: List[PlayerStat] = Field(default=[], alias="playerStats")

    class Config:
        populate_by_name = True


class GeneralStatPlayerWL(BaseModel):
    player_name: str = Field(default="", alias="playerName")
    win_loss: Optional[WinLoss] = Field(default=None, alias="winLoss")

    class Config:
        populate_by_name = True


class GeneralStat(BaseModel):
    general: General = General.USA
    stats: List[GeneralStatPlayerWL] = []
    total: Optional[WinLoss] = None


class GeneralStats(BaseModel):
    general_stats: List[GeneralStat] = Field(default=[], alias="generalStats")

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
    name: str = ""
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
    player_name: str = Field(default="", alias="playerName")
    action_count: int = Field(default=0, alias="actionCount")
    minutes: float = 0.0
    apm: float = 0.0

    class Config:
        populate_by_name = True


class UpgradeEvent(BaseModel):
    player_name: str = Field(default="", alias="playerName")
    timecode: int = 0
    upgrade_name: str = Field(default="", alias="upgradeName")
    cost: int = 0
    at_minute: float = Field(default=0.0, alias="atMinute")

    class Config:
        populate_by_name = True


class Spent(BaseModel):
    player_name: str = Field(default="", alias="playerName")
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
    general1: General = General.USA
    general2: General = General.USA
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


class Wrapped(BaseModel):
    games_played: int = Field(default=0, alias="gamesPlayed")
    hours_played: float = Field(default=0.0, alias="hoursPlayed")
    most_played: General = Field(default=General.USA, alias="mostPlayed")
    most_played_winrate: float = Field(default=0.0, alias="mostPlayedWinrate")
    most_built: str = Field(default="", alias="mostBuilt")
    most_built_spent: float = Field(default=0.0, alias="mostBuiltSpent")
    most_built_count: int = Field(default=0, alias="mostBuiltCount")
    most_built_more: int = Field(default=0, alias="mostBuiltMore")
    best_general: General = Field(default=General.USA, alias="bestGeneral")
    best_winrate: float = Field(default=0.0, alias="bestWinrate")
    best_average: float = Field(default=0.0, alias="bestAverage")

    class Config:
        populate_by_name = True
