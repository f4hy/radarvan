from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, date
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


class MatchInfo(BaseModel, frozen=True):
    id: int
    timestamp: datetime
    map: str
    winning_team: Team
    players: list[Player]
    duration_minutes: float
    filename: str
    incomplete: str = ""
    notes: str

    class Config:
        populate_by_name = True


class Matches(BaseModel):
    matches: list[MatchInfo]


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
    win_loss: WinLoss | None = Field(default=None, alias="winLoss")

    class Config:
        populate_by_name = True


class PlayerStat(BaseModel):
    player_name: str = Field(alias="playerName")
    stats: dict[General, WinLoss]
    faction_stats: list[PlayerStatFactionWL] = Field(alias="factionStats")
    over_time: list[PlayerRateOverTime] = Field(alias="overTime")

    class Config:
        populate_by_name = True


class PlayerStats(BaseModel):
    player_stats: list[PlayerStat] = Field(alias="playerStats")

    class Config:
        populate_by_name = True


class GeneralStatPlayerWL(BaseModel):
    player_name: str = Field(alias="playerName")
    win_loss: WinLoss | None = Field(default=None, alias="winLoss")

    class Config:
        populate_by_name = True


class GeneralStat(BaseModel):
    general: General
    stats: list[GeneralStatPlayerWL]
    total: WinLoss


class GeneralStats(BaseModel):
    general_stats: list[GeneralStat]

    class Config:
        populate_by_name = True


class TeamStat(BaseModel):
    date: DateMessage | None = None
    team: Team = Team.NONE
    wins: int = 0


class TeamStats(BaseModel):
    team_stats: list[TeamStat] = Field(alias="teamStats")

    class Config:
        populate_by_name = True


class MapStat(BaseModel):
    map: str = ""
    team: Team = Team.NONE
    wins: int = 0


class MapResult(BaseModel):
    map: str = ""
    date: DateMessage | None = None
    winner: Team = Team.NONE


class MapResults(BaseModel):
    results: list[MapResult]


class MapStats(BaseModel):
    map_stats: list[MapStat] = Field(alias="mapStats")
    over_time: dict[str, MapResults] = Field(alias="overTime")

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
    player: Player | None
    buildings: list[CostsBuiltObject]
    units: list[CostsBuiltObject]
    upgrades: list[CostsBuiltObject]


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
    upgrades: list[UpgradeEvent]


class SpentOverTime(BaseModel):
    buildings: list[Spent]
    units: list[Spent]
    upgrades: list[Spent]
    total: list[Spent]


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


class FirstBlood(BaseModel):
    attacker: str
    victim: str
    atMinute: float


class MatchDetails(BaseModel):
    match_id: int = Field(alias="matchId")
    costs: list[Costs]
    apms: list[APM]
    upgrade_events: dict[str, Upgrades] = Field(alias="upgradeEvents")
    spent: SpentOverTime
    money_values: dict[float, dict[str, int]] = Field(
        description="at a time value (int) map each player to the value"
    )
    money_collected_values: dict[float, dict[str, int]] = Field(
        description="at a time value (int) map each player to the value"
    )
    stats_data: dict[str, dict[float, dict[str, int]]] = Field(
        description="at a time map each player to xp"
    )
    first_blood: FirstBlood | None = None
    building_first_blood: FirstBlood | None = None
    player_summary: list[PlayerSummary]

    class Config:
        populate_by_name = True


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
    team_pairs: dict[str, PairsWinLosses] = Field(alias="teamPairs")
    faction_pairs: dict[str, PairFactionWinLosses] = Field(alias="factionPairs")

    class Config:
        populate_by_name = True


# listing


class PlayerListing(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    player_name: str
    team_id: int
    is_winner: bool
    general_id: int
    match_id: int
    color: str


class MatchListing(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    match_id: int
    map: str
    duration_minutes: float
    incomplete: str | None = None
    created_at: datetime
    json_s3_uri: str
    timestamp: datetime
    winning_team_id: int
    filename: str
    notes: str
    players: list[PlayerListing]


class GameRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    json_s3_uri: str
    file_size_bytes: int | None = None
    game_timestamp: datetime
    match_id: int
    replay_file_url: str
    created_at: datetime
    game_date: date
    match: MatchListing | None = None


class Tournament(BaseModel, frozen=True):
    name: str
    start_date: date
    end_date: date
    teams: list[tuple[str, ...]]
    total_games_played_per_team: int


class MatchupResult(BaseModel):
    tournament_name: str
    matches: list[MatchInfo]
    outcome: dict[tuple[str, ...], WinLoss]
    override: str | None = None


class Matchup(BaseModel):
    team1: tuple[str, ...]
    team2: tuple[str, ...]
    played: bool


class TournamentResult(BaseModel):
    tournament: Tournament
    matchups: list[MatchupResult]

    records: dict[tuple[str, ...], WinLoss]
    complete: bool


class TournamentStat(BaseModel, frozen=True):
    stat_name: str
    value: float | str | None = None
    player: str | None = None
    match_id: int | None = None


class TournamentReport(BaseModel, frozen=True):
    name: str
    stats: list[TournamentStat]


class WinnerOverride(BaseModel):
    match_id: int
    winning_team_id: Team
    incomplete: str | None = None


class ReplayFileSchema(BaseModel):
    """Public API representation of ReplayFile"""

    original_url: str
    s3_uri: str
    status: str
    player_id: str
    discovered_at: datetime
    source_date: date

    model_config = ConfigDict(from_attributes=True)  # Allows ORM mode


class ParsedReplayJsonSchema(BaseModel):
    """Public API representation of ParsedReplayJson"""

    json_s3_uri: str
    match_id: int
    replay_file_url: str
    num_time_stamps: int | None = None
    created_at: datetime
    game_timestamp: datetime
    game_date: date
    updated_at: datetime | None = None
    has_enhanced_stats: bool | None = None

    model_config = ConfigDict(from_attributes=True)


class PlayerRatings(BaseModel):
    name: str
    ordinal: float
    mu: float
    sigma: float
    game_count: int
    model_config = ConfigDict(from_attributes=True)
