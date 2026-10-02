"""Turn a snapshot record into a per-timestep feature sequence (torch-free).

Each match becomes a ``[T, len(FEATURE_NAMES)]`` array: one row per 30-second
window, holding cumulative per-side economy/military signals (and their
differences) up to that point in the game. ``FeatureStats`` picks the columns a
model uses and standardises them with statistics frozen from the training split.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .config import BUCKET_SECONDS, MAX_BUCKETS
from .snapshot import (
    EV_CAPTURE,
    EV_DEATH,
    EV_KILL,
    EV_KILL_STRUCT,
    EV_STRUCT,
    EV_UNIT,
    Record,
)

# Per-side signals, each emitted for side a, side b and a - b. All but "alive"
# are cumulative and log1p'd; "alive" is the fraction of the side still playing.
SIDE_GROUPS = (
    "money",
    "income",
    "units",
    "structures",
    "build_value",
    "kills",
    "value_destroyed",
    "struct_destroyed",
    "captures",
    "alive",
)
MATCH_GROUPS = ("elapsed", "prior")
GROUPS = SIDE_GROUPS + MATCH_GROUPS

FEATURE_NAMES: tuple[str, ...] = (
    *(f"{side}.{g}" for side in ("a", "b", "d") for g in SIDE_GROUPS),
    *MATCH_GROUPS,
)
_COLUMN = {name: i for i, name in enumerate(FEATURE_NAMES)}


def feature_names(drop: set[str] | frozenset[str] = frozenset()) -> list[str]:
    """Every column whose group is not in ``drop``."""
    unknown = set(drop) - set(GROUPS)
    if unknown:
        raise ValueError(f"unknown feature groups: {sorted(unknown)}")
    return [n for n in FEATURE_NAMES if n.rsplit(".", 1)[-1] not in drop]


@dataclass(slots=True)
class SeqMatch:
    x: np.ndarray  # [T, len(FEATURE_NAMES)] float32, BEFORE selection/standardization
    label: int  # 1 == side a (team_a) won
    length: int  # T
    match_id: int


def _sample(series: list[int], snap_idx: np.ndarray) -> np.ndarray:
    if not series:
        return np.zeros(len(snap_idx))
    arr = np.asarray(series, dtype=np.float64)
    sampled: np.ndarray = arr[np.clip(snap_idx, 0, len(arr) - 1)]
    return sampled


def match_to_sequence(rec: Record, prior_logit: float = 0.0) -> SeqMatch | None:
    """Encode one snapshot record into a feature sequence, or ``None`` if unusable.

    ``prior_logit`` is the frozen pre-game prior for this match (``pregame.py``),
    repeated across every timestep.
    """
    frame_count = int(rec.get("frame_count", 0))
    duration_minutes = float(rec.get("duration_minutes", 0.0))
    if frame_count <= 0 or duration_minutes <= 0:
        return None

    sec_per_frame = (duration_minutes * 60.0) / frame_count
    n_buckets = math.ceil(duration_minutes * 60.0 / BUCKET_SECONDS)
    n_buckets = max(1, min(n_buckets, MAX_BUCKETS))

    # Per-bucket increments per side, in SIDE_GROUPS order minus money/income/alive:
    # units, structures, build_value, kills, value_destroyed, struct_destroyed,
    # captures, deaths.
    inc = np.zeros((n_buckets, 2, 8), dtype=np.float64)
    for frame, typ, side, value in rec["events"]:
        b = int((frame * sec_per_frame) / BUCKET_SECONDS)
        if b >= n_buckets:
            continue
        b = max(b, 0)
        if typ == EV_UNIT:
            inc[b, side, 0] += 1
            inc[b, side, 2] += value
        elif typ == EV_STRUCT:
            inc[b, side, 1] += 1
            inc[b, side, 2] += value
        elif typ in (EV_KILL, EV_KILL_STRUCT):
            inc[b, side, 3] += 1
            inc[b, side, 4] += value
            if typ == EV_KILL_STRUCT:
                inc[b, side, 5] += value
        elif typ == EV_CAPTURE:
            inc[b, side, 6] += 1
        elif typ == EV_DEATH:
            inc[b, side, 7] += 1
    cum = np.cumsum(inc, axis=0)  # [bucket, side, 8]

    # Money / income level at each bucket end, from the per-side snapshot series.
    si = rec.get("snapshot_interval", 0) or 1
    snap_idx = (
        np.arange(1, n_buckets + 1) * BUCKET_SECONDS / (si * sec_per_frame)
    ).astype(int)
    team_size = max(int(rec.get("team_size", 1)), 1)

    def side_block(side: int) -> np.ndarray:
        money = _sample(rec["money"].get(str(side), []), snap_idx)
        income = _sample(rec.get("earned", {}).get(str(side), []), snap_idx)
        logged = np.log1p(np.column_stack([money, income, cum[:, side, :7]]))
        alive = 1.0 - np.minimum(cum[:, side, 7], team_size) / team_size
        return np.column_stack([logged, alive])  # SIDE_GROUPS order

    feat_a, feat_b = side_block(0), side_block(1)
    # Minutes played so far, never the fraction of the match elapsed: that
    # needs the final duration, which a live bar cannot know.
    elapsed = np.log1p(np.arange(1, n_buckets + 1) * BUCKET_SECONDS / 60.0)[:, None]
    prior = np.full((n_buckets, 1), float(prior_logit))
    feats = np.concatenate(
        [feat_a, feat_b, feat_a - feat_b, elapsed, prior], axis=1
    ).astype(np.float32)

    return SeqMatch(
        x=feats,
        label=int(rec["label_a_win"]),
        length=n_buckets,
        match_id=rec["match_id"],
    )


@dataclass(slots=True)
class FeatureStats:
    """The columns a model reads, with their mean/std frozen from train only."""

    names: list[str]
    mean: list[float]
    std: list[float]

    @property
    def cols(self) -> list[int]:
        return [_COLUMN[n] for n in self.names]

    @classmethod
    def fit(cls, seqs: list[SeqMatch], names: list[str] | None = None) -> FeatureStats:
        names = list(FEATURE_NAMES) if names is None else names
        cols = [_COLUMN[n] for n in names]
        stacked = np.concatenate([s.x[:, cols] for s in seqs], axis=0)
        mean = stacked.mean(axis=0)
        std = stacked.std(axis=0)
        std[std < 1e-6] = 1.0  # guard constant features
        return cls(names, mean.astype(float).tolist(), std.astype(float).tolist())

    def apply(self, x: np.ndarray) -> np.ndarray:
        return (x[:, self.cols] - np.asarray(self.mean, np.float32)) / np.asarray(
            self.std, np.float32
        )

    def save(self, path: Path) -> None:
        path.write_text(
            json.dumps(
                {"names": self.names, "mean": self.mean, "std": self.std}, indent=2
            )
        )

    @classmethod
    def load(cls, path: Path) -> FeatureStats:
        d = json.loads(Path(path).read_text())
        return cls(d["names"], d["mean"], d["std"])


# Lags in windows (30s each) whose changes the GBDT sees: its only memory.
DELTA_LAGS = (2, 4)


def with_deltas(x: np.ndarray) -> np.ndarray:
    """``[T, F]`` standardized rows -> ``[T, F * (1 + len(DELTA_LAGS))]``.

    Each lag's change is taken against the first row before the game has that
    much history, so early windows see a change of zero rather than a jump.
    """
    parts = [x]
    for lag in DELTA_LAGS:
        prev = np.vstack([np.repeat(x[:1], lag, axis=0), x])[: len(x)]
        parts.append(x - prev)
    return np.hstack(parts).astype(np.float32, copy=False)
