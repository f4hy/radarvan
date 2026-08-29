"""Types for the new cncstats parsed JSON format (v2).

The new format adds a top-level `Stats` key containing structured event streams
and per-player time-series data. The `Summary` no longer includes `MoneySpent`.
"""

from pydantic import BaseModel, Field, RootModel, ConfigDict
from typing import Annotated, Literal


# ---------------------------------------------------------------------------
# Byte array helpers (shared with header)
# ---------------------------------------------------------------------------


class ByteArray2(RootModel[list[int]]):
    root: Annotated[list[int], Field(min_length=2, max_length=2)]


class ByteArray4(RootModel[list[int]]):
    root: Annotated[list[int], Field(min_length=4, max_length=4)]


class ByteArray8(RootModel[list[int]]):
    root: Annotated[list[int], Field(min_length=8, max_length=8)]


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------


class Player(BaseModel):
    Type: Literal["H", "C"]
    Name: str
    IP: str
    Port: str
    FT: str
    Color: str
    Faction: int
    StartingPosition: str
    Team: int
    Unknown: str


class Metadata(BaseModel):
    MapFile: str
    MapCRC: str
    MapSize: str
    Seed: int
    C: str
    SR: str
    StartingCredits: str
    Players: list[Player]


class GeneralsHeader(BaseModel):
    GameType: str
    TimeStampBegin: int
    TimeStampEnd: int
    Desync: list[int] = []
    UnusedDesync: list[int] | None = None
    MoreUnusedDesync: list[int] | None = None
    QuitEarly: list[int] = []
    Disconnect: list[int] = []
    Filler: list[int] | None = None
    NumTimeStamps: int
    FileName: str
    Year: int
    Month: int
    DOW: int
    Day: int
    Hour: int
    Minute: int
    Second: int
    Millisecond: int
    Version: str
    BuildDate: str
    VersionMinor: int
    VersionMajor: int
    Hash: ByteArray8
    Metadata: Metadata
    ReplayOwnerSlot: ByteArray2 | None = None
    Unknown1: ByteArray4 | None = None
    Unknown2: ByteArray4 | None = None
    Unknown3: ByteArray4 | None = None
    GameSpeed: int | None = None


# ---------------------------------------------------------------------------
# Body (game commands - same structure as v1)
# ---------------------------------------------------------------------------


class EventDetails(BaseModel):
    Name: str
    Cost: int | None = None


class BodyChunk(BaseModel):
    model_config = ConfigDict(extra="ignore")

    TimeCode: int
    OrderCode: int
    OrderName: str
    PlayerID: int
    PlayerName: str
    Details: EventDetails | None = None


# ---------------------------------------------------------------------------
# Summary (per-player end-of-game totals; MoneySpent removed in v2)
# ---------------------------------------------------------------------------


class ObjectSummary(BaseModel):
    Count: int
    TotalSpent: int


class PlayerSummary(BaseModel):
    Name: str
    Side: str
    Team: int
    Win: bool
    UnitsCreated: dict[str, ObjectSummary]
    BuildingsBuilt: dict[str, ObjectSummary]
    UpgradesBuilt: dict[str, ObjectSummary]
    PowersUsed: dict[str, int]


# ---------------------------------------------------------------------------
# Stats - new in v2
# ---------------------------------------------------------------------------


class GameInfo(BaseModel):
    map: str
    mode: str
    frameCount: int
    seed: int
    replayFile: str
    playerCount: int
    snapshotInterval: int


class AcademyStats(BaseModel):
    supplyCentersBuilt: int
    peonsBuilt: int
    structuresCaptured: int
    generalsPointsSpent: int
    specialPowersUsed: int
    structuresGarrisoned: int
    upgradesPurchased: int
    gatherersBuilt: int
    heroesBuilt: int
    controlGroupsUsed: int
    secondaryIncomeUnitsBuilt: int
    clearedGarrisonedBuildings: int
    salvageCollected: int
    guardAbilityUsedCount: int
    doubleClickAttackMoveOrdersGiven: int
    minesCleared: int
    vehiclesDisguised: int
    firestormsCreated: int


class StatsPlayer(BaseModel):
    index: int
    displayName: str
    faction: str
    side: str
    baseSide: str
    type: str
    color: str
    money: int
    moneyEarned: int
    moneySpent: int
    score: int
    academy: AcademyStats


class TimeSeriesPlayer(BaseModel):
    index: int
    money: list[int]
    moneyEarned: list[int]
    moneySpent: list[int]


class TimeSeries(BaseModel):
    players: list[TimeSeriesPlayer]


class BuildEvent(BaseModel):
    frame: int
    player: int
    x: float
    y: float
    cost: int
    buildTime: int
    object: str
    producer: str


class KillEvent(BaseModel):
    frame: int
    killerPlayer: int
    victimPlayer: int
    x: float
    y: float
    killer: str
    victim: str
    damageType: str


class DeathEvent(BaseModel):
    frame: int
    player: int


class CaptureEvent(BaseModel):
    frame: int
    newOwner: int
    oldOwner: int
    x: float
    y: float
    object: str


class RankEvent(BaseModel):
    frame: int
    player: int
    rankLevel: int


class EnergyEvent(BaseModel):
    frame: int
    player: int
    production: int
    consumption: int


class SciencePointsEvent(BaseModel):
    frame: int
    player: int
    sciencePurchasePoints: int


class SkillPointsEvent(BaseModel):
    frame: int
    player: int
    skillPoints: int


class RadarEvent(BaseModel):
    frame: int
    player: int
    hasRadar: bool


class BattlePlanEvent(BaseModel):
    frame: int
    player: int
    bombardment: int
    holdTheLine: int
    searchAndDestroy: int


class GameStats(BaseModel):
    version: int
    game: GameInfo
    players: list[StatsPlayer]
    timeSeries: TimeSeries
    buildEvents: list[BuildEvent]
    killEvents: list[KillEvent]
    deathEvents: list[DeathEvent]
    captureEvents: list[CaptureEvent]
    rankEvents: list[RankEvent]
    energyEvents: list[EnergyEvent]
    sciencePointsEvents: list[SciencePointsEvent]
    skillPointsEvents: list[SkillPointsEvent]
    radarEvents: list[RadarEvent]
    battlePlanEvents: list[BattlePlanEvent]


# ---------------------------------------------------------------------------
# Top-level replay
# ---------------------------------------------------------------------------


class EnhancedReplayV2(BaseModel):
    Header: GeneralsHeader
    Body: list[BodyChunk]
    Summary: list[PlayerSummary]
    Offset: int
    Stats: GameStats | None = None

    def replay_id(self) -> int:
        return self.Header.Metadata.Seed
