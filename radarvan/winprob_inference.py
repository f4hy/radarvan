"""Serve win-probability-over-time from the exported ONNX model - torch-free.

The production app has no torch; ONNX Runtime + numpy is all we need at serving
time. Feature encoding reuses the torch-free encoder in
``ml_win_prediction_over_time`` (the same code used for training) so there is no
train/serve skew. The model + its feature stats are loaded once and cached. See
``ml_win_prediction_over_time/README.md`` and ``export.py``.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import numpy as np
import onnxruntime as ort
import structlog

from ml_win_prediction_over_time.config import BUCKET_SECONDS
from ml_win_prediction_over_time.features import FeatureStats, match_to_sequence
from ml_win_prediction_over_time.pregame import PregamePrior
from ml_win_prediction_over_time.snapshot import (
    higher_slot_is_side_a,
    record_from_replay,
)

from .api_types import WinProbOverTime, WinProbPoint
from .cncstats_model.zhreplay import EnhancedReplayV2
from .player_ids import resolve_player_name
from .utils import players_from_replay

logger = structlog.get_logger(__name__)

MODEL_PATH = Path(os.getenv("WINPROB_MODEL_PATH", "ml_winprob_over_time.onnx"))
STATS_PATH = Path(os.getenv("WINPROB_STATS_PATH", "ml_winprob_over_time_stats.json"))
# Frozen pre-game prior (rosters -> log-odds), one of the model's input features.
# Optional: a model exported before the prior existed has a neutral one baked in,
# and PregamePrior.neutral() reproduces exactly the 0.0 column it was trained on.
PRIOR_PATH = Path(os.getenv("WINPROB_PRIOR_PATH", "ml_winprob_over_time_prior.json"))


class ModelUnavailable(RuntimeError):
    """Raised when the ONNX model / feature-stats files are missing."""


@lru_cache(maxsize=1)
def _session() -> ort.InferenceSession:
    if not MODEL_PATH.exists():
        raise ModelUnavailable(f"ONNX model not found at {MODEL_PATH}")
    return ort.InferenceSession(str(MODEL_PATH), providers=["CPUExecutionProvider"])


@lru_cache(maxsize=1)
def _stats() -> FeatureStats:
    if not STATS_PATH.exists():
        raise ModelUnavailable(f"feature stats not found at {STATS_PATH}")
    return FeatureStats.load(STATS_PATH)


@lru_cache(maxsize=1)
def _prior() -> PregamePrior:
    return (
        PregamePrior.load(PRIOR_PATH) if PRIOR_PATH.exists() else PregamePrior.neutral()
    )


def model_available() -> bool:
    return MODEL_PATH.exists() and STATS_PATH.exists()


def _resolved_names(replay: EnhancedReplayV2, names: list[str]) -> list[str]:
    """Alias-resolve raw replay names ("Mod" -> "Modus") for display.

    The snapshot record carries in-game names; every other surface (including
    the pre-game ``MatchPrediction`` shown right above this chart) shows
    canonical ones, so resolve here rather than making the UI do it. Color
    disambiguates the shared "pc" alias.
    """
    color_by_name = {p.name: p.color for p in players_from_replay(replay)}
    return [resolve_player_name(n, color_by_name.get(n, "")) for n in names]


def predict_over_time(replay: EnhancedReplayV2) -> WinProbOverTime | None:
    """Win-probability curve for a parsed replay.

    Returns ``None`` if the replay isn't a usable two-team game with a decisive
    winner (the same gate the model was trained under). Rosters come straight
    from the encoded record, so the names always line up with ``prob_team_a``.

    The model's own side A is a per-match coin flip (see
    ``snapshot.higher_slot_is_side_a``) — a training-time trick to keep the
    t=0 prior at 0.5. We undo it here so the response honours its documented
    contract of "team A == lower team id", which is what
    ``ml_inference.predict_match_info`` also uses. Without this the two AI
    panels label opposite teams "Team A" on ~half of all matches.
    """
    record = record_from_replay(replay)
    if record is None:
        return None
    prior_logit = _prior().logit(record["team_a_players"], record["team_b_players"])
    seq = match_to_sequence(record, prior_logit=prior_logit)
    if seq is None:
        return None

    x = _stats().apply(seq.x).astype(np.float32)[None]  # [1, T, F]
    probs = _session().run(["prob_team_a"], {"x": x})[0][0]  # [T]

    flip = higher_slot_is_side_a(int(record["match_id"]))
    a_players, b_players = record["team_a_players"], record["team_b_players"]
    a_won = bool(record["label_a_win"])
    if flip:
        a_players, b_players = b_players, a_players
        a_won = not a_won
        probs = 1.0 - probs

    points = [
        WinProbPoint(at_minute=(i + 1) * BUCKET_SECONDS / 60.0, prob_team_a=float(p))
        for i, p in enumerate(probs)
    ]
    return WinProbOverTime(
        match_id=int(record["match_id"]),
        team_a_players=_resolved_names(replay, a_players),
        team_b_players=_resolved_names(replay, b_players),
        actual_winner="team_a" if a_won else "team_b",
        points=points,
    )
