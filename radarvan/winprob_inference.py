"""Serve win-probability-over-time from the exported ONNX model — torch-free.

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
from ml_win_prediction_over_time.snapshot import record_from_replay

from .api_types import WinProbOverTime, WinProbPoint
from .cncstats_model.zhreplay import EnhancedReplayV2

logger = structlog.get_logger(__name__)

MODEL_PATH = Path(os.getenv("WINPROB_MODEL_PATH", "ml_winprob_over_time.onnx"))
STATS_PATH = Path(os.getenv("WINPROB_STATS_PATH", "ml_winprob_over_time_stats.json"))


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


def model_available() -> bool:
    return MODEL_PATH.exists() and STATS_PATH.exists()


def predict_over_time(replay: EnhancedReplayV2) -> WinProbOverTime | None:
    """Win-probability curve for a parsed replay.

    Returns ``None`` if the replay isn't a usable two-team game with a decisive
    winner (the same gate the model was trained under). Rosters come straight
    from the encoded record, so the names always line up with ``prob_team_a``.
    """
    record = record_from_replay(replay)
    if record is None:
        return None
    seq = match_to_sequence(record)
    if seq is None:
        return None

    x = _stats().apply(seq.x).astype(np.float32)[None]  # [1, T, F]
    probs = _session().run(["prob_team_a"], {"x": x})[0][0]  # [T]
    points = [
        WinProbPoint(at_minute=(i + 1) * BUCKET_SECONDS / 60.0, prob_team_a=float(p))
        for i, p in enumerate(probs)
    ]
    actual = "team_a" if record["label_a_win"] else "team_b"
    return WinProbOverTime(
        match_id=int(record["match_id"]),
        team_a_players=record["team_a_players"],
        team_b_players=record["team_b_players"],
        actual_winner=actual,
        points=points,
    )
