"""Paths and hyperparameters for the win-probability-over-time model.

Plain dataclasses (no torch import) so the snapshot / split steps that don't need
the model stay cheap to import.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# All artifacts (snapshots, splits, runs) live under data/ (git-ignored).
DATA_DIR = Path(__file__).resolve().parent / "data"

# Bump when the on-disk snapshot record schema changes incompatibly.
SCHEMA_VERSION = 1

# --- Time bucketing ---------------------------------------------------------
# The match is discretised into fixed real-time windows. Each window becomes one
# timestep in the sequence; the model emits a win probability per window.
BUCKET_SECONDS = 30.0
# Hard cap on sequence length (windows). Longer games are truncated; this bounds
# memory and keeps a handful of 90-minute outliers from dominating padding.
MAX_BUCKETS = 80  # 40 minutes at 30s/bucket

# Number of per-timestep input features produced by ``features.match_to_sequence``.
# 7 cumulative features per side (a, b), their 7 differences, plus elapsed_frac.
N_FEATURES = 7 * 2 + 7 + 1  # = 22


@dataclass(slots=True)
class ModelConfig:
    hidden: int = 64
    num_layers: int = 1
    dropout: float = 0.1
    bidirectional: bool = False  # must stay causal (no peeking ahead) for serving


@dataclass(slots=True)
class TrainConfig:
    lr: float = 2e-3
    weight_decay: float = 1e-4
    batch_size: int = 64
    max_epochs: int = 100
    patience: int = 15  # early-stop patience on val log-loss
    seed: int = 1234
    # Fraction of the *train* split (its most recent tail) held out for early
    # stopping and best-checkpoint selection. Validating on dev.jsonl.gz - which
    # is what this trainer used to do, and what `predict.py --eval` then scores -
    # is test-set model selection; the same bug in ../ml inflated its published
    # AUC by ~0.06. 0.0 restores that behaviour.
    val_frac: float = 0.15
    # Later timesteps are weighted up to this multiple of early ones: a game's
    # outcome is genuinely uncertain early, so we don't punish the model as hard
    # for a coin-flip at minute 1 as for a wrong call at minute 20.
    late_weight: float = 3.0


@dataclass(slots=True)
class Config:
    model: ModelConfig = field(default_factory=ModelConfig)
    train: TrainConfig = field(default_factory=TrainConfig)
