"""Wire shapes for the generals-powers breakdown (`/api/power_stats/`)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .common import General, Minute, SmallRate


class PowerRow(BaseModel):
    """One power, for one player, on one general - against the group baseline.

    The baseline is every *other* player on the same general, not the whole
    group including this player. With a roster this small, leaving someone in
    their own comparison flattens exactly the signal the row exists to show.
    """

    model_config = ConfigDict(populate_by_name=True)

    power: str
    # True when this power is bought with a generals point. False for the ones
    # a building grants (Spy Satellite, Particle Cannon, Scud Storm), which
    # have usage but can never have a pick rate.
    purchasable: bool
    # True for a generals point that unlocks a *unit* (Paladin Tank, Red Guard
    # Training) rather than a panel button. Bought like a power, never fired.
    unlocks_unit: bool = Field(alias="unlocksUnit")
    games_picked: int = Field(alias="gamesPicked")
    pick_rate: SmallRate = Field(alias="pickRate")
    group_pick_rate: SmallRate = Field(alias="groupPickRate")
    # Mean minute at which this player buys it, over the games they bought it.
    avg_pick_minute: Minute | None = Field(default=None, alias="avgPickMinute")
    group_avg_pick_minute: Minute | None = Field(
        default=None, alias="groupAvgPickMinute"
    )
    # Mean number of levels bought in the games this was taken (1.0 = never
    # upgraded past the first). None when never taken.
    avg_levels: SmallRate = Field(alias="avgLevels")
    group_avg_levels: SmallRate = Field(alias="groupAvgLevels")
    uses: int
    uses_per_minute: SmallRate = Field(alias="usesPerMinute")
    group_uses_per_minute: SmallRate = Field(alias="groupUsesPerMinute")


class GeneralPowers(BaseModel):
    """One player's power habits on one general."""

    model_config = ConfigDict(populate_by_name=True)

    general: General
    games: int
    minutes: Minute
    # Games the rest of the group has on this general - the weight behind every
    # `group_*` figure in `rows`.
    group_games: int = Field(alias="groupGames")
    # Spy Drone + Spy Satellite + Radar Van Scan per minute: the scouting
    # cadence, which is split across several power names.
    recon_per_minute: SmallRate = Field(alias="reconPerMinute")
    group_recon_per_minute: SmallRate = Field(alias="groupReconPerMinute")
    rows: list[PowerRow]


class UnusualPick(BaseModel):
    """A pick rate that stands out from the rest of the group.

    `surprise` is the gap in pick rate scaled by how much evidence there is for
    it - a binomial z-score against the group's rate. It exists so one game of
    something odd doesn't outrank a habit held over thirty.
    """

    model_config = ConfigDict(populate_by_name=True)

    general: General
    power: str
    games: int
    pick_rate: SmallRate = Field(alias="pickRate")
    group_pick_rate: SmallRate = Field(alias="groupPickRate")
    surprise: float
    # "over" when this player takes it more than the group, "under" for less.
    direction: str


class PlayerPowerProfile(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    player: str
    games: int
    generals: list[GeneralPowers]
    unusual: list[UnusualPick]


class PowerStats(BaseModel):
    """The powers page payload: who can be picked, and the picked player."""

    model_config = ConfigDict(populate_by_name=True)

    players: list[str]
    # Matches contributing power data. Lower than the corpus size: a match
    # whose details have not been derived yet contributes nothing.
    matches: int
    profile: PlayerPowerProfile | None = None
