"""Serve win-probability-over-time from the exported ONNX models - torch-free.

The curve is the average of a GRU and a GBDT (``ml_win_prediction_over_time/gbdt.py``
says why). Features come from the same torch-free encoder training uses, so there
is no train/serve skew. ``export.py`` deploys the four bundle files together.
"""

from __future__ import annotations

import hashlib
import os
from functools import lru_cache
from pathlib import Path

import onnxruntime as ort
import structlog
from opentelemetry import trace

from ml_win_prediction_over_time.config import BUCKET_SECONDS, GBDT_OUTPUT
from ml_win_prediction_over_time.features import (
    FeatureStats,
    match_to_sequence,
    with_deltas,
)
from ml_win_prediction_over_time.pregame import PregamePrior
from ml_win_prediction_over_time.snapshot import (
    higher_slot_is_side_a,
    record_from_replay,
)

from .api_types import WinProbOverTime, WinProbPoint
from .cncstats_model.zhreplay import EnhancedReplayV2
from .ml_inference import cpu_session
from .player_ids import resolve_player_name
from .utils import log_duration, players_from_replay

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)

MODEL_PATH = Path(os.getenv("WINPROB_MODEL_PATH", "ml_winprob_over_time.onnx"))
STATS_PATH = Path(os.getenv("WINPROB_STATS_PATH", "ml_winprob_over_time_stats.json"))
# Frozen pre-game prior (rosters -> log-odds), one of the model's input features.
PRIOR_PATH = Path(os.getenv("WINPROB_PRIOR_PATH", "ml_winprob_over_time_prior.json"))
GBDT_PATH = Path(os.getenv("WINPROB_GBDT_PATH", "ml_winprob_over_time_gbdt.onnx"))
_BUNDLE = (MODEL_PATH, STATS_PATH, PRIOR_PATH, GBDT_PATH)


class ModelUnavailable(RuntimeError):
    """Raised when any file of the serving bundle is missing."""


def _require(path: Path) -> Path:
    if not path.exists():
        raise ModelUnavailable(f"win-prob model file not found at {path}")
    return path


def _onnx(path: Path) -> ort.InferenceSession:
    return cpu_session(_require(path))


@lru_cache(maxsize=1)
def _session() -> ort.InferenceSession:
    return _onnx(MODEL_PATH)


@lru_cache(maxsize=1)
def _gbdt_session() -> ort.InferenceSession:
    return _onnx(GBDT_PATH)


@lru_cache(maxsize=1)
def _stats() -> FeatureStats:
    return FeatureStats.load(_require(STATS_PATH))


@lru_cache(maxsize=1)
def _prior() -> PregamePrior:
    return PregamePrior.load(_require(PRIOR_PATH))


def model_available() -> bool:
    return all(p.exists() for p in _BUNDLE)


def bundle_version() -> str:
    """Short hash of the deployed bundle, so caches of its output follow a retrain."""
    digest = hashlib.sha256()
    for path in _BUNDLE:
        digest.update(path.read_bytes() if path.exists() else b"missing")
    return digest.hexdigest()[:12]


def _resolved_names(replay: EnhancedReplayV2, names: list[str]) -> list[str]:
    """Alias-resolve raw replay names ("Mod" -> "Modus") for display.

    The snapshot record carries in-game names; every other surface (including
    the pre-game ``MatchPrediction`` shown right above this chart) shows
    canonical ones, so resolve here rather than making the UI do it. Color
    disambiguates the shared "pc" alias.
    """
    color_by_name = {p.name: p.color for p in players_from_replay(replay)}
    return [resolve_player_name(n, color_by_name.get(n, "")) for n in names]


@log_duration
def predict_over_time(replay: EnhancedReplayV2) -> WinProbOverTime | None:
    """Win-probability curve, or ``None`` unless two even teams with a decided winner.

    Undoes the training-time side-A coin flip (``snapshot.higher_slot_is_side_a``)
    so team A is the lower team id, as in ``ml_inference.predict_match_info``.
    """
    record = record_from_replay(replay)
    if record is None:
        return None
    prior_logit = _prior().logit(record["team_a_players"], record["team_b_players"])
    seq = match_to_sequence(record, prior_logit=prior_logit)
    if seq is None:
        return None

    x = _stats().apply(seq.x)  # [T, F] float32
    with tracer.start_as_current_span(
        "winprob onnx inference", attributes={"winprob.timesteps": len(x)}
    ):
        gru_probs = _session().run(["prob_team_a"], {"x": x[None]})[0][0]  # [T]
        tree_probs = _gbdt_session().run([GBDT_OUTPUT], {"x": with_deltas(x)})[0][:, 1]
    probs = (gru_probs + tree_probs) / 2

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
