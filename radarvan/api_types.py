from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, date
from enum import IntEnum
from typing import Literal
from .game_composition import GameComposition

_SLOTS: ConfigDict = ConfigDict(slots=True)  # type: ignore[typeddict-unknown-key]
_SLOTS_FA: ConfigDict = ConfigDict(from_attributes=True, slots=True)  # type: ignore[typeddict-unknown-key]
# Classes with field aliases must use an inline ConfigDict so the pydantic mypy plugin
# can statically resolve populate_by_name=True. _SLOTS and _SLOTS_FA are safe to share
# because none of those classes have aliases.


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
    model_config = _SLOTS

    name: str
    general: General
    team: Team
    color: str
    won: bool = False
    starting_position: int | None = None

    @property
    def Type(self) -> Literal["H", "C"]:
        if self.name.lower() in ["cpu", "hardai", "hardarmy", "mediai", "easyai"]:
            return "C"
        return "H"

    @property
    def Team(self) -> Team:
        return self.team

    def __repr__(self) -> str:
        return f"{self.name}[{self.general.name} {'W' if self.won else 'L'}]"


class MatchInfo(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    id: int
    timestamp: datetime
    date: date
    map: str
    winning_team: Team
    players: list[Player]
    duration_minutes: float
    filename: str
    incomplete: str = ""
    notes: str = ""
    game_version: str | None = None
    composition: GameComposition | None = None


class Matches(BaseModel):
    model_config = _SLOTS

    matches: list[MatchInfo]


class WinLoss(BaseModel):
    model_config = _SLOTS

    wins: int
    losses: int


class GeneralWL(BaseModel):
    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    general: General
    win_loss: WinLoss = Field(alias="winLoss")


class DateMessage(BaseModel):
    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    year: int = Field(alias="Year")
    month: int = Field(alias="Month")
    day: int = Field(alias="Day")


class PlayerRateOverTime(BaseModel):
    model_config = _SLOTS

    date: DateMessage
    wl: GeneralWL


class PlayerStatFactionWL(BaseModel):
    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    faction: Faction = Faction.ANYUSA
    win_loss: WinLoss | None = Field(default=None, alias="winLoss")


class PlayerStat(BaseModel):
    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    player_name: str = Field(alias="playerName")
    stats: dict[General, WinLoss]
    faction_stats: list[PlayerStatFactionWL] = Field(alias="factionStats")
    over_time: list[PlayerRateOverTime] = Field(alias="overTime")
    game_counts: dict[str, int] = Field(default_factory=dict, alias="gameCounts")


class PlayerStats(BaseModel):
    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    player_stats: list[PlayerStat] = Field(alias="playerStats")


class GeneralStatPlayerWL(BaseModel):
    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    player_name: str = Field(alias="playerName")
    win_loss: WinLoss | None = Field(default=None, alias="winLoss")


class GeneralStat(BaseModel):
    model_config = _SLOTS

    general: General
    stats: list[GeneralStatPlayerWL]
    total: WinLoss


class GeneralStats(BaseModel):
    model_config = _SLOTS

    general_stats: list[GeneralStat]


class TeamStat(BaseModel):
    model_config = _SLOTS

    date: DateMessage | None = None
    team: Team = Team.NONE
    wins: int = 0


class TeamStats(BaseModel):
    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    team_stats: list[TeamStat] = Field(alias="teamStats")


class TeamRecord(BaseModel):
    model_config = _SLOTS

    players: list[str]
    wins: int
    losses: int


class TeamSizeGroup(BaseModel):
    model_config = _SLOTS

    size: int
    teams: list[TeamRecord]


class TeamStatsResponse(BaseModel):
    model_config = _SLOTS

    groups: list[TeamSizeGroup]


class MapPlayerWL(BaseModel):
    model_config = _SLOTS

    player: str
    wins: int
    losses: int


class MapGeneralWL(BaseModel):
    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    general: General
    wins: int
    losses: int
    win_rate_delta: float = Field(default=0.0, alias="winRateDelta")


class MapData(BaseModel):
    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    map_name: str = Field(alias="mapName")
    total_games: int = Field(alias="totalGames")
    player_stats: list[MapPlayerWL] = Field(alias="playerStats")
    general_stats: list[MapGeneralWL] = Field(alias="generalStats")


class MapStatsResponse(BaseModel):
    model_config = _SLOTS

    maps: list[MapData]


class MapStat(BaseModel):
    model_config = _SLOTS

    map: str = ""
    team: Team = Team.NONE
    wins: int = 0


class MapResult(BaseModel):
    model_config = _SLOTS

    map: str = ""
    date: DateMessage | None = None
    winner: Team = Team.NONE


class MapResults(BaseModel):
    model_config = _SLOTS

    results: list[MapResult]


class MapStats(BaseModel):
    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    map_stats: list[MapStat] = Field(alias="mapStats")
    over_time: dict[str, MapResults] = Field(alias="overTime")


class SaveResponse(BaseModel):
    model_config = _SLOTS

    success: bool = False


class KillEventOutput(BaseModel):
    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    at_minute: float = Field(alias="atMinute")
    killer_player: str = Field(alias="killerPlayer")
    victim_player: str = Field(alias="victimPlayer")
    x: float
    y: float
    killer: str
    victim: str
    damage_type: str = Field(alias="damageType")


class CostsBuiltObject(BaseModel):
    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    name: str
    count: int
    total_spent: int = Field(alias="totalSpent")


class Costs(BaseModel):
    model_config = _SLOTS

    player: Player | None
    buildings: list[CostsBuiltObject]
    units: list[CostsBuiltObject]
    upgrades: list[CostsBuiltObject]


class APM(BaseModel):
    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    player_name: str = Field(alias="playerName")
    action_count: int = Field(alias="actionCount")
    minutes: float
    apm: float


class UpgradeEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    player_name: str = Field(alias="playerName")
    timecode: int = 0
    upgrade_name: str = Field(alias="upgradeName")
    cost: int
    at_minute: float = Field(alias="atMinute")


class Spent(BaseModel):
    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    player_name: str = Field(alias="playerName")
    acc_cost: int = Field(alias="accCost")
    at_minute: float = Field(alias="atMinute")


class Upgrades(BaseModel):
    model_config = _SLOTS

    upgrades: list[UpgradeEvent]


class SpentOverTime(BaseModel):
    model_config = _SLOTS

    buildings: list[Spent]
    units: list[Spent]
    upgrades: list[Spent]
    total: list[Spent]


class ObjectSummary(BaseModel):
    model_config = _SLOTS

    Count: int
    TotalSpent: int


class PlayerSummary(BaseModel):
    model_config = _SLOTS

    Name: str
    Side: str
    Team: int
    Win: bool
    Color: str
    MoneySpent: int = 0
    UnitsCreated: dict[str, ObjectSummary]
    BuildingsBuilt: dict[str, ObjectSummary]
    UpgradesBuilt: dict[str, ObjectSummary]
    PowersUsed: dict[str, int]


class FirstBlood(BaseModel):
    model_config = _SLOTS

    attacker: str
    victim: str
    atMinute: float


class SuperlativePlayerSummary(BaseModel):
    model_config = _SLOTS

    name: str
    color: str
    won: bool
    money_spent: int
    units_created_count: int
    buildings_built_count: int


class SuperlativeData(BaseModel):
    model_config = _SLOTS

    match_id: int
    first_blood: FirstBlood | None = None
    building_first_blood: FirstBlood | None = None
    apms: list[APM]
    player_summary: list[SuperlativePlayerSummary]
    upgrade_counts: dict[str, int]
    total_units_killed: int
    total_buildings_killed: int
    total_xp: int
    match_money_spent: int
    player_money_collected: dict[str, int]


class MatchDetails(BaseModel):
    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    match_id: int = Field(alias="matchId")
    game_version: str | None = Field(None)
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
    player_money_spent: dict[str, int] = Field(
        default_factory=dict,
        alias="playerMoneySpent",
        description="end-of-game money spent per player name",
    )
    map_name: str = Field(default="", alias="mapName")
    first_blood: FirstBlood | None = None
    building_first_blood: FirstBlood | None = None
    player_summary: list[PlayerSummary]
    kill_events: list[KillEventOutput] = Field(default_factory=list, alias="killEvents")


class PairWinLoss(BaseModel):
    model_config = _SLOTS

    general1: General
    general2: General
    winloss: WinLoss | None


class PairFactionWinLoss(BaseModel):
    model_config = _SLOTS

    faction1: Faction = Faction.ANYUSA
    faction2: Faction = Faction.ANYUSA
    winloss: WinLoss | None


class PairsWinLosses(BaseModel):
    model_config = _SLOTS

    pairwl: list[PairWinLoss]


class PairFactionWinLosses(BaseModel):
    model_config = _SLOTS

    pairwl: list[PairFactionWinLoss]


class TeamPairs(BaseModel):
    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    team_pairs: dict[str, PairsWinLosses] = Field(alias="teamPairs")
    faction_pairs: dict[str, PairFactionWinLosses] = Field(alias="factionPairs")


# listing


class PlayerListing(BaseModel):
    model_config = _SLOTS_FA

    id: int
    player_name: str
    team_id: int
    is_winner: bool
    general_id: int
    match_id: int
    color: str


class MatchListing(BaseModel):
    model_config = _SLOTS_FA

    match_id: int
    map: str
    duration_minutes: float
    incomplete: str | None = None
    created_at: datetime
    json_s3_uri: str
    timestamp: datetime
    winning_team_id: int
    filename: str
    notes: str | None = None
    players: list[PlayerListing]


class GameRecord(BaseModel):
    model_config = _SLOTS_FA

    json_s3_uri: str
    file_size_bytes: int | None = None
    game_timestamp: datetime
    match_id: int
    replay_file_url: str
    created_at: datetime
    game_date: date
    game_version: str | None = None
    match: MatchListing | None = None


class Tournament(BaseModel):
    model_config = ConfigDict(frozen=True, slots=True)  # type: ignore[typeddict-unknown-key]

    name: str
    start_date: date
    end_date: date
    teams: list[tuple[str, ...]]
    total_games_played_per_team: int


class MatchupResult(BaseModel):
    model_config = _SLOTS

    tournament_name: str
    matches: list[MatchInfo]
    outcome: dict[tuple[str, ...], WinLoss]
    override: str | None = None


class Matchup(BaseModel):
    model_config = _SLOTS

    team1: tuple[str, ...]
    team2: tuple[str, ...]
    played: bool


class TournamentResult(BaseModel):
    model_config = _SLOTS

    tournament: Tournament
    matchups: list[MatchupResult]

    records: dict[tuple[str, ...], WinLoss]
    complete: bool


class Statistic(BaseModel):
    model_config = ConfigDict(frozen=True, slots=True)  # type: ignore[typeddict-unknown-key]

    stat_name: str
    date_computed: date
    value: float | str | None = None
    player: str | None = None
    match_id: int | None = None


class TournamentReport(BaseModel):
    model_config = ConfigDict(frozen=True, slots=True)  # type: ignore[typeddict-unknown-key]

    name: str
    stats: list[Statistic]


class WinnerOverride(BaseModel):
    model_config = _SLOTS

    match_id: int
    winning_team_id: Team
    incomplete: str | None = None


class ReplayFileSchema(BaseModel):
    """Public API representation of ReplayFile"""

    model_config = _SLOTS_FA

    original_url: str
    s3_uri: str
    status: str
    player_id: str
    discovered_at: datetime
    source_date: date


class ParsedReplayJsonSchema(BaseModel):
    """Public API representation of ParsedReplayJson"""

    model_config = _SLOTS_FA

    json_s3_uri: str
    match_id: int
    replay_file_url: str
    num_time_stamps: int | None = None
    created_at: datetime
    game_timestamp: datetime
    game_date: date
    updated_at: datetime | None = None
    has_enhanced_stats: bool | None = None


class PlayerGameCount(BaseModel):
    model_config = _SLOTS

    name: str
    count: int


class PlayerRatings(BaseModel):
    model_config = _SLOTS_FA

    name: str
    ordinal: float
    mu: float
    sigma: float
    game_count: int
    atdate: date | None = None


class ShortPlayerRating(BaseModel):
    model_config = _SLOTS_FA

    mu: float
    sigma: float
    atdate: date | None = None


class PlayerRatingData(BaseModel):
    model_config = _SLOTS_FA

    player_rating: list[PlayerRatings]
    player_rating_overtime: dict[str, list[ShortPlayerRating]] = {}


class MapExtent(BaseModel):
    model_config = _SLOTS

    width: float
    height: float
    grid_width: float
    grid_height: float
    border_size: float


class MapPoint(BaseModel):
    model_config = _SLOTS

    name: str
    x: float
    y: float


class MapPlayerStart(BaseModel):
    model_config = _SLOTS

    player_number: int
    x: float
    y: float


class MapDataPayload(BaseModel):
    model_config = _SLOTS

    extent: MapExtent
    player_starts: list[MapPlayerStart]
    supply: list[MapPoint]
    tech: list[MapPoint]
    waypoints: list[MapPoint]


class MapsByPlayerCount(BaseModel):
    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    player_count: int = Field(alias="playerCount")
    maps: list[str]


class DraftPlayerRequest(BaseModel):
    model_config = _SLOTS

    name: str
    team: int  # 1-4


class DraftRequest(BaseModel):
    model_config = _SLOTS

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
