"""Pydantic models defining every REST request/response shape — the canonical wire
schema (``MatchInfo``, ``PlayerStat``, ``MatchDetails``, the ``General``/``Team``/
``Faction`` enums, …) from which the TypeScript API client is generated."""

from pydantic import (
    AfterValidator,
    BaseModel,
    Field,
    ConfigDict,
    computed_field,
    model_validator,
)
from datetime import datetime, date
from enum import IntEnum
from typing import Annotated, Literal
from .game_composition import GameComposition
from .player_ids import (
    is_admin as _is_admin_player,
    is_tournament_admin as _is_tournament_admin_player,
    resolve_player_name,
)

_SLOTS: ConfigDict = ConfigDict(slots=True)  # type: ignore[typeddict-unknown-key]
_SLOTS_FA: ConfigDict = ConfigDict(from_attributes=True, slots=True)  # type: ignore[typeddict-unknown-key]
# Classes with field aliases must use an inline ConfigDict so the pydantic mypy plugin
# can statically resolve populate_by_name=True. _SLOTS and _SLOTS_FA are safe to share
# because none of those classes have aliases.


def _resolve_player_name(name: str) -> str:
    # Single-arg wrapper so pydantic's AfterValidator doesn't try to pass its
    # second positional (ValidationInfo) as resolve_player_name's `color`.
    return resolve_player_name(name)


# Type for any request field carrying a player name: alias→canonical resolution
# happens automatically at request validation, so endpoints can't forget it.
# Wire/OpenAPI type stays a plain string. See CLAUDE.md (player name resolution).
PlayerName = Annotated[str, AfterValidator(_resolve_player_name)]


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

    def is_real(self) -> bool:
        """Return True if this is a real (non-observer, recognized) player."""
        return self.team != Team.OBSERVER and self.general != General.UNRECOGNIZED

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
    is_dev: bool = False


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


class FFAPlayerStat(BaseModel):
    """Per-player record across free-for-all games."""

    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    name: str
    games: int
    wins: int
    win_rate: float = Field(alias="winRate")
    # Expected wins if every player in each FFA were equally likely (sum of 1/N
    # over the player's games). Lets us judge a win rate against the field size.
    expected_wins: float = Field(alias="expectedWins")
    # Actual wins divided by expected wins: 1.0 == exactly average, >1 over-performing.
    dominance: float


class FFAGeneralStat(BaseModel):
    """Per-general win record across free-for-all games."""

    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    general: General
    games: int
    wins: int
    win_rate: float = Field(alias="winRate")


class FFAMapStat(BaseModel):
    """Per-map activity across free-for-all games."""

    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    map: str
    games: int
    avg_players: float = Field(alias="avgPlayers")


class FFAStats(BaseModel):
    """Everything the FFA page renders, computed over human free-for-all games."""

    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    total_games: int = Field(alias="totalGames")
    distinct_players: int = Field(alias="distinctPlayers")
    avg_players_per_game: float = Field(alias="avgPlayersPerGame")
    biggest_game_players: int = Field(alias="biggestGamePlayers")
    player_stats: list[FFAPlayerStat] = Field(alias="playerStats")
    general_stats: list[FFAGeneralStat] = Field(alias="generalStats")
    map_stats: list[FFAMapStat] = Field(alias="mapStats")


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
    # Build cost of the destroyed object (0 when unknown). Used to size kill
    # markers in the replay view by value destroyed.
    value: int = 0


class MapEventOutput(BaseModel):
    """A single map-positioned, time-stamped event for replay playback.

    `kind` is one of "build" (structure completed) or "capture" (neutral/enemy
    structure taken). `player_name` is the owner after the event; `name` is the
    cleaned object name. Kill events are served separately via `kill_events`.
    """

    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    at_minute: float = Field(alias="atMinute")
    x: float
    y: float
    player_name: str = Field(alias="playerName")
    kind: str
    name: str


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


class ObjectSummary(BaseModel):
    model_config = _SLOTS

    Count: int
    TotalSpent: int


class AcademyStats(BaseModel):
    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    cleared_garrisoned_buildings: int = Field(alias="clearedGarrisonedBuildings")
    control_groups_used: int = Field(alias="controlGroupsUsed")
    double_click_attack_move_orders_given: int = Field(
        alias="doubleClickAttackMoveOrdersGiven"
    )
    firestorms_created: int = Field(alias="firestormsCreated")
    gatherers_built: int = Field(alias="gatherersBuilt")
    generals_points_spent: int = Field(alias="generalsPointsSpent")
    guard_ability_used_count: int = Field(alias="guardAbilityUsedCount")
    heroes_built: int = Field(alias="heroesBuilt")
    mines_cleared: int = Field(alias="minesCleared")
    peons_built: int = Field(alias="peonsBuilt")
    salvage_collected: int = Field(alias="salvageCollected")
    secondary_income_units_built: int = Field(alias="secondaryIncomeUnitsBuilt")
    special_powers_used: int = Field(alias="specialPowersUsed")
    structures_captured: int = Field(alias="structuresCaptured")
    structures_garrisoned: int = Field(alias="structuresGarrisoned")
    supply_centers_built: int = Field(alias="supplyCentersBuilt")
    upgrades_purchased: int = Field(alias="upgradesPurchased")
    vehicles_disguised: int = Field(alias="vehiclesDisguised")


class PlayerSummary(BaseModel):
    model_config = _SLOTS

    Name: str
    Side: str
    Team: int
    Win: bool
    Color: str
    UnitsCreated: dict[str, ObjectSummary]
    BuildingsBuilt: dict[str, ObjectSummary]
    UpgradesBuilt: dict[str, ObjectSummary]
    PowersUsed: dict[str, int]
    UnitsDestroyed: dict[str, ObjectSummary] = Field(default_factory=dict)
    BuildingsDestroyed: dict[str, ObjectSummary] = Field(default_factory=dict)
    UnitsLost: dict[str, ObjectSummary] = Field(default_factory=dict)
    BuildingsLost: dict[str, ObjectSummary] = Field(default_factory=dict)
    Academy: AcademyStats | None = None


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
    player_xp_final: dict[str, int] = Field(default_factory=dict)
    time_to_rank_5: dict[str, float] = Field(default_factory=dict)
    time_to_search_destroy: dict[str, float] = Field(default_factory=dict)


class TimelineEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    player_name: str = Field(alias="playerName")
    at_minute: float = Field(alias="atMinute")
    event_name: str = Field(alias="eventName")
    # One of: "upgrade", "rank_up", "generals_power",
    # "superweapon_built", "superweapon_activated".
    event_type: str = Field(alias="eventType")
    cost: int = 0


class BuildOrderEntry(BaseModel):
    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    at_minute: float = Field(alias="atMinute")
    name: str
    cost: int
    # Number of consecutive identical builds collapsed into this row (>=1).
    count: int = 1
    # End of the collapsed run; None for single (count==1) entries.
    end_minute: float | None = Field(default=None, alias="endMinute")
    # Economy/non-combat unit (worker, dozer, supply). UI dims these. Always
    # False for buildings and upgrades.
    is_economy: bool = Field(default=False, alias="isEconomy")


class BuildOrder(BaseModel):
    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    buildings: list[BuildOrderEntry]
    units: list[BuildOrderEntry]
    upgrades: list[BuildOrderEntry]


class MatchDetails(BaseModel):
    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    match_id: int = Field(alias="matchId")
    game_version: str | None = Field(None)
    costs: list[Costs]
    apms: list[APM]
    upgrade_events: dict[str, Upgrades] = Field(alias="upgradeEvents")
    stats_data: dict[str, dict[float, dict[str, int]]] = Field(
        description="at a time map each player to xp"
    )
    map_name: str = Field(default="", alias="mapName")
    first_blood: FirstBlood | None = None
    building_first_blood: FirstBlood | None = None
    player_summary: list[PlayerSummary]
    kill_events: list[KillEventOutput] = Field(default_factory=list, alias="killEvents")
    # Map-positioned structure builds & captures, sorted by time, for the
    # replay-playback view (kills are in `kill_events`).
    map_events: list[MapEventOutput] = Field(default_factory=list, alias="mapEvents")
    player_money_spent: dict[str, int] = Field(default_factory=dict)
    player_money_collected: dict[str, int] = Field(default_factory=dict)
    # Minute at which each player first hit generals rank 5.
    time_to_rank_5: dict[str, float] = Field(default_factory=dict, alias="timeToRank5")
    # Minute at which each player first activated USA Search & Destroy battle plan.
    time_to_search_destroy: dict[str, float] = Field(
        default_factory=dict, alias="timeToSearchDestroy"
    )
    # Per-player first-10 build order: buildings, units, upgrades.
    build_orders: dict[str, BuildOrder] = Field(
        default_factory=dict, alias="buildOrders"
    )
    # Per-minute APM time series: {minute: {player_name: apm}}.
    apm_over_time: dict[float, dict[str, float]] = Field(
        default_factory=dict, alias="apmOverTime"
    )
    # All player-driven timeline markers (upgrades, rank ups, generals
    # powers, superweapon builds & activations). Front-end renders them as
    # per-player horizontal-lane scatter dots with per-type shapes.
    timeline_events: list[TimelineEvent] = Field(
        default_factory=list, alias="timelineEvents"
    )


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
    replay_presigned_url: str | None = None
    json_presigned_url: str | None = None
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


class BracketPlayerEntry(BaseModel):
    model_config = _SLOTS

    seed: int
    player_name: PlayerName


class CreateBracketRequest(BaseModel):
    model_config = _SLOTS

    players: list[BracketPlayerEntry]

    @model_validator(mode="after")
    def _validate_seeds(self) -> "CreateBracketRequest":
        seeds = sorted(p.seed for p in self.players)
        if seeds != list(range(1, 13)):
            raise ValueError("players must have exactly 12 unique seeds numbered 1-12")
        return self


class SetBracketMatchRequest(BaseModel):
    model_config = _SLOTS

    scheduled_date: date | None = None
    best_of: Literal[3, 5, 7, 9] | None = None
    score_a: int | None = None
    score_b: int | None = None


class BracketMatchOutput(BaseModel):
    model_config = _SLOTS

    match_id: str
    bracket: Literal["W", "L", "GF"]
    round_number: int
    round_name: str
    player_a: str | None = None
    player_b: str | None = None
    scheduled_date: date | None = None
    best_of: int | None = None
    score_a: int | None = None
    score_b: int | None = None
    winner: str | None = None
    status: Literal["pending", "ready", "completed", "not_applicable"]


class BracketTournamentOutput(BaseModel):
    model_config = _SLOTS

    players: list[BracketPlayerEntry]
    matches: list[BracketMatchOutput]
    bye_advances: list[BracketPlayerEntry]
    champion: str | None = None
    runner_up: str | None = None
    needs_reset: bool


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


class ReplayWithoutPlayerStats(BaseModel):
    """A parsed replay still missing player stats (backfill work item)."""

    model_config = _SLOTS_FA

    match_id: int
    url: str
    s3_path: str
    version: str | None = None
    presigned_url: str
    all_replay_urls: list[str]


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
    recent_deltas: dict[int, float] = Field(default_factory=dict)
    high_ordinal: float | None = None
    low_ordinal: float | None = None


class ShortPlayerRating(BaseModel):
    model_config = _SLOTS_FA

    mu: float
    sigma: float
    atdate: date | None = None


class PlayerRatingData(BaseModel):
    model_config = _SLOTS_FA

    player_rating: list[PlayerRatings]
    player_rating_overtime: dict[str, list[ShortPlayerRating]] = {}
    player_form: dict[str, list[bool]] = {}


class PlayerSkill(BaseModel):
    model_config = _SLOTS_FA

    name: str
    skill: float
    game_count: int


class PlayerSynergy(BaseModel):
    """Whether a pair of players over- or under-performs their combined ratings.

    ``synergy`` is the extra log-odds the pair's team gets purely because the two
    are paired, beyond what their individual ratings predict (positive = chemistry,
    negative = anti-synergy). ``win_prob_delta`` expresses the same effect as a
    win-probability shift at an even (50/50) matchup. See
    ``SYNERGY_METHODOLOGY.md``.
    """

    model_config = _SLOTS_FA

    player_a: str
    player_b: str
    synergy: float
    win_prob_delta: float
    games_together: int
    wins_together: int
    expected_wins: float
    std_error: float
    z_score: float
    games_apart: int
    main_a: float
    main_b: float
    adjusted_expected_wins: float


class HeadToHead(BaseModel):
    model_config = _SLOTS_FA

    wins: int
    losses: int


class HeadToHeadGame(BaseModel):
    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    match_id: int = Field(alias="matchId")
    timestamp: datetime
    date: date
    map: str
    duration_minutes: float = Field(alias="durationMinutes")
    game_format: str | None = Field(default=None, alias="gameFormat")
    player1_general: General = Field(alias="player1General")
    player2_general: General = Field(alias="player2General")
    player1_won: bool = Field(alias="player1Won")
    player1_team: list[str] = Field(alias="player1Team")
    player2_team: list[str] = Field(alias="player2Team")


class HeadToHeadGeneralRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    general: General
    wins: int
    losses: int


class HeadToHeadMapRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    map: str
    player1_wins: int = Field(alias="player1Wins")
    player2_wins: int = Field(alias="player2Wins")


class HeadToHeadDetail(BaseModel):
    """Detailed head-to-head record between two players in opposite-team games."""

    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    player1: str
    player2: str
    player1_wins: int = Field(alias="player1Wins")
    player2_wins: int = Field(alias="player2Wins")
    games: list[HeadToHeadGame]
    player1_by_general: list[HeadToHeadGeneralRecord] = Field(alias="player1ByGeneral")
    player2_by_general: list[HeadToHeadGeneralRecord] = Field(alias="player2ByGeneral")
    by_map: list[HeadToHeadMapRecord] = Field(alias="byMap")


class PlayerRatingDailyChange(BaseModel):
    model_config = _SLOTS_FA

    name: str
    delta: float


class RatingUpset(BaseModel):
    """A game where the rating model's favored team lost.

    Win probabilities are the model's pre-game prediction for each team using the
    converged ratings; ``surprise`` is the favorite's edge over the actual winner.
    """

    model_config = _SLOTS_FA

    match_id: int
    atdate: date
    favored_team: int
    favored_players: list[str]
    favored_win_prob: float
    winning_team: int
    winner_players: list[str]
    winner_win_prob: float
    surprise: float


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


class MapMatchCount(BaseModel):
    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    map: str
    match_count: int = Field(alias="matchCount")


class MissingMapInfo(BaseModel):
    model_config = _SLOTS

    map_name: str
    sample_match_id: int
    map_crc_hex: str | None = None


class FetchMissingMapResult(BaseModel):
    model_config = _SLOTS

    map_name: str
    base_name: str | None = None
    tga_s3_uri: str | None = None
    webp_s3_uri: str | None = None
    map_s3_uri: str | None = None
    map_data_saved: bool = False
    error: str | None = None


class FetchMissingMapsResponse(BaseModel):
    model_config = _SLOTS

    requested: int
    fetched: int
    results: list[FetchMissingMapResult]


class DraftPlayerRequest(BaseModel):
    model_config = _SLOTS

    name: str
    team: int  # 1-4


class DraftRequest(BaseModel):
    model_config = _SLOTS

    map_name: str
    players: list[DraftPlayerRequest]


class MapRenderPlayer(BaseModel):
    model_config = _SLOTS

    name: str
    general: General
    team: int
    position_number: int


class MapRenderRequest(BaseModel):
    model_config = _SLOTS

    map_name: str
    players: list[MapRenderPlayer]


class MapSummaryPlayer(BaseModel):
    model_config = _SLOTS

    name: PlayerName
    general: General
    team: int = 0


class MapSummaryRequest(BaseModel):
    model_config = _SLOTS

    map_name: str
    players: list[MapSummaryPlayer]


class MapSummaryRanking(BaseModel):
    model_config = _SLOTS

    name: str
    wins: int
    losses: int


class MapSummaryTeamH2H(BaseModel):
    model_config = _SLOTS

    team1: list[str]
    team2: list[str]
    team1_wins: int
    team2_wins: int


class MapSummaryPlayerGeneralRecord(BaseModel):
    model_config = _SLOTS

    name: str
    general: General
    wins: int
    losses: int


class MapSummaryDuration(BaseModel):
    model_config = _SLOTS

    avg_minutes: float
    shortest_minutes: float
    longest_minutes: float


class MapSummaryRecentResult(BaseModel):
    model_config = _SLOTS

    date: date
    winners: list[str]
    losers: list[str]
    duration_minutes: float


class MapSummaryStreak(BaseModel):
    model_config = _SLOTS

    name: str
    streak: int


class MapSummaryResponse(BaseModel):
    model_config = _SLOTS

    map_name: str
    total_games: int
    best_general: MapSummaryRanking | None = None
    best_player: MapSummaryRanking | None = None
    team_h2h: MapSummaryTeamH2H | None = None
    team_general_h2h: MapSummaryTeamH2H | None = None
    team_h2h_overall: MapSummaryTeamH2H | None = None
    team_general_h2h_overall: MapSummaryTeamH2H | None = None
    player_general_records: list[MapSummaryPlayerGeneralRecord] = Field(
        default_factory=list
    )
    player_general_overall: list[MapSummaryPlayerGeneralRecord] = Field(
        default_factory=list
    )
    duration: MapSummaryDuration | None = None
    recent_results: list[MapSummaryRecentResult] = Field(default_factory=list)
    streaks: list[MapSummaryStreak] = Field(default_factory=list)


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


class CurrentUser(BaseModel):
    model_config = _SLOTS_FA

    discord_id: str
    discord_username: str
    discord_avatar: str | None = None
    player_name: str | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def needs_player_selection(self) -> bool:
        """True until the user has claimed an in-game name from PLAYER_NAMES."""
        return self.player_name is None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_admin(self) -> bool:
        """True if the claimed in-game name is in player_ids.ADMIN_PLAYERS."""
        return _is_admin_player(self.player_name)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_tournament_admin(self) -> bool:
        """True if the claimed in-game name is in player_ids.TOURNAMENT_ADMINS."""
        return _is_tournament_admin_player(self.player_name)


class AuthStatus(BaseModel):
    model_config = _SLOTS

    logged_in: bool
    user: CurrentUser | None = None
    # The in-game names a logged-in user may claim (sorted PLAYER_NAMES).
    available_players: list[str] = Field(default_factory=list)


class SelectPlayerRequest(BaseModel):
    model_config = _SLOTS

    player_name: str


MapVoteChoice = Literal["vote", "veto"]


class MapVoteOption(BaseModel):
    model_config = _SLOTS

    map_name: str
    game_count: int
    last_played: datetime | None = None
    days_since_last_played: int | None = None
    # The logged-in viewer's pick for this map (None if unset or logged out).
    my_choice: MapVoteChoice | None = None


class MapVotePage(BaseModel):
    model_config = _SLOTS

    player_count: int
    logged_in: bool
    vote_limit: int
    veto_limit: int
    votes_used: int
    vetoes_used: int
    # Maps for this player count, ordered by total games played (desc).
    maps: list[MapVoteOption] = Field(default_factory=list)


class SetMapVoteRequest(BaseModel):
    model_config = _SLOTS

    map_name: str
    # None clears the viewer's pick for this map.
    choice: MapVoteChoice | None = None


class ChooseMapRequest(BaseModel):
    model_config = _SLOTS

    # In-game names of the players in this game; only their votes count.
    # PlayerName auto-resolves aliases (e.g. "skp" -> "Skip") at validation.
    players: list[PlayerName] = Field(default_factory=list)


class ChooseMapCandidate(BaseModel):
    model_config = _SLOTS

    map_name: str
    votes: int
    vetoes: int
    # Selection weight (net score if eligible, else 0).
    weight: int
    # In the draw pool: net score (votes - penalties) is positive.
    eligible: bool
    # Played within the recency window, so docked RECENT_PLAY_PENALTY votes.
    recently_played: bool = False


class ChooseMapResult(BaseModel):
    model_config = _SLOTS

    player_count: int
    # The backend's authoritative weighted-random pick (None if no eligible map).
    chosen_map: str | None = None
    # The chosen map's CRC (uppercase hex), if we have it stored; None otherwise.
    chosen_map_crc: str | None = None
    # Every map with at least one vote or veto, for the reveal animation,
    # ordered by votes desc then name.
    candidates: list[ChooseMapCandidate] = Field(default_factory=list)


class MapUploadItem(BaseModel):
    model_config = _SLOTS

    base_name: str
    # WebP data URL of the converted .tga — set in preview, omitted on commit.
    image: str | None = None
    # Number of player start positions (from parsed geometry), if available.
    player_count: int | None = None
    # True if a map with this name already has assets in S3.
    already_exists: bool = False
    # True once the assets have actually been saved (commit response).
    saved: bool = False
    # The computed map CRC (uppercase hex), available in preview and commit.
    crc: str | None = None
    # True once the map was registered with cncstats (commit only).
    pushed_to_cncstats: bool = False


class MapUploadResponse(BaseModel):
    model_config = _SLOTS

    committed: bool
    maps: list[MapUploadItem] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class BackfillMapCrcsResponse(BaseModel):
    model_config = _SLOTS

    processed: int
    resolved: int
    # (map_name, crc) per row touched; crc is None when no match could supply it.
    results: list[tuple[str, str | None]] = Field(default_factory=list)


class PushMapResult(BaseModel):
    model_config = _SLOTS

    map_name: str
    crc: str | None = None
    # True if we POSTed it to cncstats this run.
    pushed: bool = False
    # True if cncstats already had it (/map_exists), so we skipped the push.
    already_present: bool = False
    error: str | None = None


class PushMapsResponse(BaseModel):
    model_config = _SLOTS

    requested: int
    pushed: int
    # Maps cncstats already had, so we skipped the push.
    already_present: int = 0
    results: list[PushMapResult] = Field(default_factory=list)


# --- ML match-outcome prediction -------------------------------------------


class PredictPlayer(BaseModel):
    model_config = _SLOTS

    # PlayerName auto-resolves aliases (e.g. "skp" -> "Skip") at validation, so
    # the model sees the same canonical names it was trained on.
    name: PlayerName
    general: General
    team: int  # 1-based team id; players with the same id are on the same team


class PredictRequest(BaseModel):
    model_config = _SLOTS

    map_name: str
    players: list[PredictPlayer]


class MatchPrediction(BaseModel):
    """Win prediction from the exported ONNX model.

    Teams are labelled A/B by ascending team id (the model's canonical ordering);
    ``prob_team_a_wins`` is the calibrated probability that team A wins.
    """

    model_config = _SLOTS

    match_id: int | None = None
    map_name: str
    team_a: int
    team_b: int
    team_a_players: list[str]
    team_b_players: list[str]
    prob_team_a_wins: float
    favored_team: int
    favored_win_prob: float
    # Players not in the model's training vocab — their contribution falls back
    # to UNK, so the prediction for them is weak. Surfaced so callers can judge.
    unknown_players: list[str] = Field(default_factory=list)


class WinProbPoint(BaseModel):
    model_config = _SLOTS

    at_minute: float
    prob_team_a: float


class WinProbOverTime(BaseModel):
    """Win-probability-over-time for one match (sequence ONNX model).

    ``points`` is ordered by time; ``prob_team_a`` is P(team A wins) given the
    game up to that window. Team A is the lower team id (the model's canonical
    ordering).
    """

    model_config = _SLOTS

    match_id: int
    team_a_players: list[str]
    team_b_players: list[str]
    actual_winner: str | None = None  # "team_a" | "team_b" | None
    points: list[WinProbPoint]
