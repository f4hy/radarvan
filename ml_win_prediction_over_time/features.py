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

from .config import BUCKET_SECONDS, MAX_BUCKETS
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


def match_to_sequence(rec: Record, prior_logit: float = 0.0) -> SeqMatch | None:
    """Encode one snapshot record into a feature sequence, or ``None`` if unusable.

    ``prior_logit`` is the frozen pre-game prior for this match (``pregame.py``),
    repeated across every timestep. It defaults to 0.0 — an even prior — so a
    caller that has no fitted prior still gets a usable sequence of the right
    width.
    """
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
    if sec_per_snap > 0:
        snap_idx = (np.arange(1, n_buckets + 1) * BUCKET_SECONDS / sec_per_snap).astype(
            int
        )
        for side in (0, 1):
            series = rec["money"].get(str(side), [])
            if series:
                arr = np.asarray(series)
                money_level[:, side] = arr[np.clip(snap_idx, 0, len(arr) - 1)]

    # Per-side feature blocks [n_buckets, 7]: money + the 6 cumulative event counts.
    feat_a = np.log1p(np.concatenate([money_level[:, 0:1], cum[:, 0]], axis=1))
    feat_b = np.log1p(np.concatenate([money_level[:, 1:2], cum[:, 1]], axis=1))
    # Minutes played so far, NOT the fraction of the match elapsed. The fraction
    # is `bucket / n_buckets`, and `n_buckets` comes from the match's *total*
    # duration - so it told the model how long the game was going to last, which
    # no live win-probability bar can know. Measured on the rolling protocol the
    # swap is a dead heat (+0.0006 log-loss, 95% CI [-0.0082, +0.0094]), so this
    # costs nothing and makes the module's "same information a live bar would
    # have" claim true.
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
