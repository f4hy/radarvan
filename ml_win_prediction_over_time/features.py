"""Turn a snapshot record into a per-timestep feature sequence (torch-free).

Each match becomes a ``[T, N_FEATURES]`` array: one row per 30-second window,
holding cumulative per-side economy/military signals (and their differences) up
to that point in the game. ``FeatureStats`` standardises features using
statistics frozen from the training split only.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .config import BUCKET_SECONDS, MAX_BUCKETS, N_FEATURES
from .snapshot import EV_CAPTURE, EV_KILL, EV_STRUCT, EV_UNIT, Record

# Per-side cumulative feature order (money is index 0, the rest come from events).
# [money_level, units_built, structures_built, build_value, kills, value_destroyed, captures]
_PER_SIDE = 7


@dataclass(slots=True)
class SeqMatch:
    x: np.ndarray  # [T, N_FEATURES] float32, BEFORE standardization
    label: int  # 1 == side a (team_a) won
    length: int  # T
    match_id: int


def match_to_sequence(rec: Record) -> SeqMatch | None:
    """Encode one snapshot record into a feature sequence, or ``None`` if unusable."""
    frame_count = int(rec.get("frame_count", 0))
    duration_minutes = float(rec.get("duration_minutes", 0.0))
    if frame_count <= 0 or duration_minutes <= 0:
        return None

    sec_per_frame = (duration_minutes * 60.0) / frame_count
    total_seconds = duration_minutes * 60.0
    n_buckets = math.ceil(total_seconds / BUCKET_SECONDS)
    n_buckets = max(1, min(n_buckets, MAX_BUCKETS))

    def bucket_of(frame: int) -> int:
        b = int((frame * sec_per_frame) / BUCKET_SECONDS)
        return min(max(b, 0), n_buckets - 1)

    # Per-bucket increments per side: units, structs, build_value, kills,
    # value_destroyed, captures (6 event-derived features).
    inc = np.zeros((n_buckets, 2, 6), dtype=np.float64)
    for frame, typ, side, value in rec["events"]:
        b = bucket_of(frame)
        if typ == EV_UNIT:
            inc[b, side, 0] += 1
            inc[b, side, 2] += value
        elif typ == EV_STRUCT:
            inc[b, side, 1] += 1
            inc[b, side, 2] += value
        elif typ == EV_KILL:
            inc[b, side, 3] += 1
            inc[b, side, 4] += value
        elif typ == EV_CAPTURE:
            inc[b, side, 5] += 1
    cum = np.cumsum(inc, axis=0)  # [bucket, side, 6]

    # Money level at each bucket end, sampled from the per-side money series.
    si = rec.get("snapshot_interval", 0) or 1
    sec_per_snap = si * sec_per_frame
    money_level = np.zeros((n_buckets, 2), dtype=np.float64)
    for side in (0, 1):
        series = rec["money"].get(str(side), [])
        if not series:
            continue
        for b in range(n_buckets):
            t_sec = (b + 1) * BUCKET_SECONDS
            k = int(t_sec / sec_per_snap) if sec_per_snap > 0 else 0
            money_level[b, side] = series[min(max(k, 0), len(series) - 1)]

    feats = np.zeros((n_buckets, N_FEATURES), dtype=np.float32)
    for b in range(n_buckets):
        a = np.log1p(np.concatenate([[money_level[b, 0]], cum[b, 0]]))  # [7]
        bb = np.log1p(np.concatenate([[money_level[b, 1]], cum[b, 1]]))  # [7]
        elapsed = (b + 1) / n_buckets
        feats[b] = np.concatenate([a, bb, a - bb, [elapsed]]).astype(np.float32)

    return SeqMatch(
        x=feats, label=int(rec["label_a_win"]), length=n_buckets, match_id=rec["match_id"]
    )


@dataclass(slots=True)
class FeatureStats:
    """Per-feature mean/std for standardization, frozen from train only."""

    mean: list[float]
    std: list[float]

    @classmethod
    def fit(cls, seqs: list[SeqMatch]) -> FeatureStats:
        stacked = np.concatenate([s.x for s in seqs], axis=0)
        mean = stacked.mean(axis=0)
        std = stacked.std(axis=0)
        std[std < 1e-6] = 1.0  # guard constant features
        return cls(mean.astype(float).tolist(), std.astype(float).tolist())

    def apply(self, x: np.ndarray) -> np.ndarray:
        return (x - np.asarray(self.mean, np.float32)) / np.asarray(
            self.std, np.float32
        )

    def save(self, path: Path) -> None:
        path.write_text(json.dumps({"mean": self.mean, "std": self.std}, indent=2))

    @classmethod
    def load(cls, path: Path) -> FeatureStats:
        d = json.loads(Path(path).read_text())
        return cls(d["mean"], d["std"])
