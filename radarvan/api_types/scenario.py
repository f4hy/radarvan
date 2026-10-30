"""Equal-skill scenario prediction: generals, composition and map, no players."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from .common import Faction, General


class ScenarioPick(StrEnum):
    """One slot: a specific general, or a uniformly random one from a faction (or any)."""

    USA = "USA"
    AIR = "AIR"
    LASER = "LASER"
    SUPER = "SUPER"
    CHINA = "CHINA"
    NUKE = "NUKE"
    TANK = "TANK"
    INFANTRY = "INFANTRY"
    GLA = "GLA"
    TOXIN = "TOXIN"
    STEALTH = "STEALTH"
    DEMO = "DEMO"
    RANDOM_USA = "RANDOM_USA"
    RANDOM_CHINA = "RANDOM_CHINA"
    RANDOM_GLA = "RANDOM_GLA"
    RANDOM = "RANDOM"


class _Wire(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class ScenarioModelInfo(_Wire):
    n_games: int = Field(alias="nGames")
    date_min: str = Field(alias="dateMin")
    date_max: str = Field(alias="dateMax")
    trained_at: str = Field(alias="trainedAt")
    replicates: int


class ScenarioInterval(_Wire):
    """Point estimate with a 5-95% game-night bootstrap interval."""

    value: float
    low: float
    high: float


class ScenarioContributions(_Wire):
    """Logit-scale pieces of the point estimate, positive favouring team A."""

    generals: float
    teammates: float
    matchups: float
    map: float


class ScenarioMapInfo(_Wire):
    key: str
    known_geometry: bool = Field(alias="knownGeometry")
    training_games: int = Field(alias="trainingGames")
    # Standardised (z-score) geometry features; empty when geometry is unknown.
    features: dict[str, float]


class ScenarioSupport(_Wire):
    """Historical games with exactly this general composition (players ignored)."""

    exact_games: int = Field(alias="exactGames")
    exact_team_a_wins: int = Field(alias="exactTeamAWins")
    exact_games_on_map: int = Field(alias="exactGamesOnMap")
    exact_team_a_wins_on_map: int = Field(alias="exactTeamAWinsOnMap")


class ScenarioSwapOption(_Wire):
    general: General
    prob_team_a: float = Field(alias="probTeamA")
    delta: ScenarioInterval


class ScenarioSlotSwaps(_Wire):
    """What happens to P(team A) if this one slot is changed to each general."""

    team: str
    index: int
    options: list[ScenarioSwapOption]


class ScenarioMapOption(_Wire):
    key: str
    training_games: int = Field(alias="trainingGames")
    prob_team_a: float = Field(alias="probTeamA")
    delta: ScenarioInterval


class ScenarioPrediction(_Wire):
    prob_team_a: ScenarioInterval = Field(alias="probTeamA")
    contributions: ScenarioContributions
    # Random slots are averaged over their generals; above a cap, a fixed sample.
    combinations: int
    combinations_exact: bool = Field(alias="combinationsExact")
    map: ScenarioMapInfo | None
    support: ScenarioSupport | None
    swaps: list[ScenarioSlotSwaps]
    # The same matchup on the most-played maps, relative to an average map.
    maps: list[ScenarioMapOption]
    model: ScenarioModelInfo


class ScenarioGeneralEffect(_Wire):
    general: General
    effect: ScenarioInterval
    games: int


class ScenarioPairEffect(_Wire):
    general_a: General = Field(alias="generalA")
    general_b: General = Field(alias="generalB")
    effect: ScenarioInterval


class ScenarioFactionPairEffect(_Wire):
    faction_a: Faction = Field(alias="factionA")
    faction_b: Faction = Field(alias="factionB")
    effect: ScenarioInterval


class ScenarioMapEffect(_Wire):
    general: General
    feature: str
    effect: ScenarioInterval


class ScenarioMapEntry(_Wire):
    key: str
    training_games: int = Field(alias="trainingGames")
    known_geometry: bool = Field(alias="knownGeometry")
    # Start positions from MapData; None when the map has no stored geometry.
    players: int | None


class ScenarioEvaluation(_Wire):
    """Held-out log-loss change from adding every general/map term to a players-only fit."""

    protocol: str
    games: int
    delta_log_loss: ScenarioInterval = Field(alias="deltaLogLoss")


class ScenarioModelSummary(_Wire):
    model: ScenarioModelInfo
    # Centered logit effects; pair/map effects are the largest by magnitude.
    generals: list[ScenarioGeneralEffect]
    matchups: list[ScenarioPairEffect]
    # Teammate effects are shrunk to the faction level; general pairs add ~nothing.
    teammates: list[ScenarioFactionPairEffect]
    map_effects: list[ScenarioMapEffect] = Field(alias="mapEffects")
    map_features: list[str] = Field(alias="mapFeatures")
    maps: list[ScenarioMapEntry]
    evaluation: list[ScenarioEvaluation]
