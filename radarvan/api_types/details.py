"""``MatchDetails`` - the per-match derived projection - and its component shapes."""

from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict
from .common import (
    General,
    Minute,
    Rate,
)
from .matches import Player


class KillEventOutput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    at_minute: Minute = Field(alias="atMinute")
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

    model_config = ConfigDict(populate_by_name=True)

    at_minute: Minute = Field(alias="atMinute")
    x: float
    y: float
    player_name: str = Field(alias="playerName")
    kind: str
    name: str


class CostsBuiltObject(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    count: int
    total_spent: int = Field(alias="totalSpent")


class Costs(BaseModel):
    player: Player | None
    buildings: list[CostsBuiltObject]
    units: list[CostsBuiltObject]
    upgrades: list[CostsBuiltObject]


class APM(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    player_name: str = Field(alias="playerName")
    action_count: int = Field(alias="actionCount")
    minutes: Minute
    apm: Rate


class UpgradeEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    player_name: str = Field(alias="playerName")
    timecode: int = 0
    upgrade_name: str = Field(alias="upgradeName")
    cost: int
    at_minute: Minute = Field(alias="atMinute")


class Spent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    player_name: str = Field(alias="playerName")
    acc_cost: int = Field(alias="accCost")
    at_minute: float = Field(alias="atMinute")


class Upgrades(BaseModel):
    upgrades: list[UpgradeEvent]


class ObjectSummary(BaseModel):
    Count: int
    TotalSpent: int


class AcademyStats(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

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
    attacker: str
    victim: str
    atMinute: Minute


class TimelineEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    player_name: str = Field(alias="playerName")
    at_minute: Minute = Field(alias="atMinute")
    event_name: str = Field(alias="eventName")
    # One of: "upgrade", "rank_up", "generals_power",
    # "superweapon_built", "superweapon_activated".
    event_type: str = Field(alias="eventType")
    cost: int = 0


class PowerPick(BaseModel):
    """One `PurchaseScience` order: a generals point spent.

    Deliberately just the raw id and when it was bought. The *name* of a
    science is a property of the game's science list, not of this match, and
    `generals_powers` resolves it at read time - so identifying an id we
    currently can't name is a one-line table edit rather than a
    DETAILS_VERSION bump and a re-derivation of every cached match.
    """

    model_config = ConfigDict(populate_by_name=True)

    at_minute: Minute = Field(alias="atMinute")
    science_id: int = Field(alias="scienceId")


class PowerUse(BaseModel):
    """How often one power was activated, by one player, in one match."""

    model_config = ConfigDict(populate_by_name=True)

    name: str
    count: int
    # Absent when the replay ships no body stream to time the first activation.
    first_minute: Minute | None = Field(default=None, alias="firstMinute")


class PlayerPowers(BaseModel):
    """One player's powers in one match: what they bought and what they fired."""

    model_config = ConfigDict(populate_by_name=True)

    # Alias-resolved (see player_ids.resolve_player_name), so this is directly
    # comparable to a name written canonically anywhere else in the app. The
    # replay's raw spelling is not kept - nothing downstream wants it, and
    # keeping both is how two rows for one player happen.
    player_name: str = Field(alias="playerName")
    # The replay's own spelling, e.g. "FactionAmericaLaserGeneral".
    faction: str
    general: General
    # Minutes this player was in the game - their elimination if they were
    # eliminated, else the match length. The denominator for a per-minute rate,
    # so someone wiped out at 4 minutes isn't averaged over a 25-minute game.
    minutes: Minute
    picks: list[PowerPick] = Field(default_factory=list)
    uses: list[PowerUse] = Field(default_factory=list)


class MatchPowers(BaseModel):
    """Per-player generals-power picks and activations for one match."""

    model_config = ConfigDict(populate_by_name=True)

    players: list[PlayerPowers] = Field(default_factory=list)


class BuildOrderEntry(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    at_minute: Minute = Field(alias="atMinute")
    name: str
    cost: int
    # Number of consecutive identical builds collapsed into this row (>=1).
    count: int = 1
    # End of the collapsed run; None for single (count==1) entries.
    end_minute: Minute | None = Field(default=None, alias="endMinute")
    # Economy/non-combat unit (worker, dozer, supply). UI dims these. Always
    # False for buildings and upgrades.
    is_economy: bool = Field(default=False, alias="isEconomy")


class BuildOrder(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    buildings: list[BuildOrderEntry]
    units: list[BuildOrderEntry]
    upgrades: list[BuildOrderEntry]


class MatchDetails(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    match_id: int = Field(alias="matchId")
    game_version: str | None = Field(None)
    costs: list[Costs]
    apms: list[APM]
    upgrade_events: dict[str, Upgrades] = Field(alias="upgradeEvents")
    stats_data: dict[str, dict[Minute, dict[str, int]]] = Field(
        description="at a time map each player to xp"
    )
    # Cumulative income broken down by source ("supply", "oil_derrick", ...),
    # as {source: {minute: {player: value}}}. Sparse: an all-zero source, a
    # player who never earned from a source, and unchanged timesteps are all
    # omitted - absent means "zero"/"unchanged". Empty for replays predating
    # cncstats incomeBySource support.
    income_by_source: dict[str, dict[Minute, dict[str, int]]] = Field(
        default_factory=dict, alias="incomeBySource"
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
    time_to_rank_5: dict[str, Minute] = Field(default_factory=dict, alias="timeToRank5")
    # Minute at which each player first activated USA Search & Destroy battle plan.
    time_to_search_destroy: dict[str, Minute] = Field(
        default_factory=dict, alias="timeToSearchDestroy"
    )
    # Minute at which each player first went "hunted" - the engine state a
    # player enters with no dozer/worker left and no way to produce one.
    # Absent for every replay parsed before cncstats statsVersion 3.
    time_to_hunted: dict[str, Minute] = Field(
        default_factory=dict, alias="timeToHunted"
    )
    # Per-player first-10 build order: buildings, units, upgrades.
    build_orders: dict[str, BuildOrder] = Field(
        default_factory=dict, alias="buildOrders"
    )
    # Per-minute APM time series: {minute: {player_name: apm}}.
    apm_over_time: dict[Minute, dict[str, Rate]] = Field(
        default_factory=dict, alias="apmOverTime"
    )
    # All player-driven timeline markers (upgrades, rank ups, generals
    # powers, superweapon builds & activations). Front-end renders them as
    # per-player horizontal-lane scatter dots with per-type shapes.
    timeline_events: list[TimelineEvent] = Field(
        default_factory=list, alias="timelineEvents"
    )
    # Generals-power picks and activations, per player. A compact projection so
    # the powers page can aggregate the whole corpus from one JSONB column
    # instead of pulling every match's timeline. None for replays that predate
    # the field or carry no player summary.
    powers: MatchPowers | None = None
