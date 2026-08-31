"""ML match-outcome prediction."""

from __future__ import annotations

from pydantic import BaseModel, Field
from .common import General, PlayerName


# --- ML match-outcome prediction -------------------------------------------


class PredictPlayer(BaseModel):
    # PlayerName auto-resolves aliases (e.g. "skp" -> "Skip") at validation, so
    # the model sees the same canonical names it was trained on.
    name: PlayerName
    general: General
    team: int  # 1-based team id; players with the same id are on the same team


class PredictRequest(BaseModel):
    map_name: str
    players: list[PredictPlayer]


class MatchPrediction(BaseModel):
    """Win prediction from the N-model ONNX ensemble.

    Teams are labelled A/B by ascending team id (the model's canonical ordering);
    ``prob_team_a_wins`` is the mean calibrated probability that team A wins
    across the ensemble. ``prob_team_a_wins_std`` is the spread across
    replicates (see ``ml.bootstrap_matrix``) - a large value means the
    ensemble disagrees with itself and this prediction shouldn't be trusted
    much, which matters given how little training data there is.
    """

    match_id: int | None = None
    map_name: str
    team_a: int
    team_b: int
    team_a_players: list[str]
    team_b_players: list[str]
    prob_team_a_wins: float
    prob_team_a_wins_std: float = 0.0
    ensemble_size: int = 1
    favored_team: int
    favored_win_prob: float
    # Players not in the model's training vocab - their contribution falls back
    # to UNK, so the prediction for them is weak. Surfaced so callers can judge.
    unknown_players: list[str] = Field(default_factory=list)


class FactionMatchupOption(BaseModel):
    """One (player1_general, player2_general) draw and its predicted outcome.

    ``prob_player1_wins_std`` is the spread across the N-model ensemble for
    this cell (see ``ml.bootstrap_matrix``) - how much replicates disagree,
    not how far the mean is from 50%."""

    player1_general: General
    player2_general: General
    prob_player1_wins: float
    prob_player1_wins_std: float = 0.0


class FactionMatchupPrediction(BaseModel):
    """Every general-vs-general draw for a hypothetical player1 vs player2
    matchup, ranked by how favorable it is to player1 (best first)."""

    player1: str
    player2: str
    map_name: str
    options: list[FactionMatchupOption]
    ensemble_size: int = 1
    compute_ms: float


class FactionMatrixCell(BaseModel):
    """One (general_a, general_b) cell of the player-agnostic faction matrix.

    ``prob_a_wins`` is the ensemble mean; ``prob_a_wins_std`` is the spread
    across replicates. ``significant`` is True when the cell's ~90% empirical
    interval across the ensemble excludes 0.5 - i.e. this general pairing
    looks real rather than indistinguishable from a coin flip given how
    little training data there is (see ``ml.bootstrap_matrix``)."""

    general_a: General
    general_b: General
    prob_a_wins: float
    prob_a_wins_std: float = 0.0
    significant: bool = False


class FactionMatrix(BaseModel):
    """The full general-vs-general grid with both players and the map forced
    to the model's UNK slot - i.e. a pure faction-vs-faction signal, not tied
    to any specific players. ``median_prob_a_wins`` is the median across all
    cells; callers derive "above/below median" from it rather than reading
    ``prob_a_wins`` as an absolute probability."""

    map_name: str
    median_prob_a_wins: float
    cells: list[FactionMatrixCell]
    ensemble_size: int = 1
    compute_ms: float


class WinProbPoint(BaseModel):
    at_minute: float
    prob_team_a: float


class WinProbOverTime(BaseModel):
    """Win-probability-over-time for one match (sequence ONNX model).

    ``points`` is ordered by time; ``prob_team_a`` is P(team A wins) given the
    game up to that window. Team A is the lower team id (the model's canonical
    ordering).
    """

    match_id: int
    team_a_players: list[str]
    team_b_players: list[str]
    actual_winner: str | None = None  # "team_a" | "team_b" | None
    points: list[WinProbPoint]
