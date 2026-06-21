"""Paths and hyperparameters for the match-outcome model.

Plain dataclasses (no torch import here) so this module is cheap to import from
the snapshot/split steps that don't need the model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# All ML artifacts live under ml/data/ (git-ignored).
DATA_DIR = Path(__file__).resolve().parent / "data"

# Bump when the on-disk snapshot/feature schema changes incompatibly.
SCHEMA_VERSION = 1


@dataclass(slots=True)
class ModelConfig:
    """Embedding sizes and the additive-term toggles (see model_design.md)."""

    emb_player: int = 16
    emb_general: int = 8
    emb_faction: int = 4
    emb_map: int = 8
    emb_format: int = 4
    synergy_k: int = 8

    mlp_hidden: tuple[int, ...] = (64, 32)
    dropout: float = 0.1

    # Additive logit terms — each can be ablated independently.
    use_mlp: bool = True  # False => linear (Bradley-Terry / openskill-like) floor
    use_synergy: bool = True
    use_matchup: bool = True

    # Optional features (off by default; see model_design.md leakage note).
    use_starting_position: bool = False
    use_openskill_numeric: bool = False


@dataclass(slots=True)
class TrainConfig:
    lr: float = 3e-3
    # Stronger than a typical default: the dataset is small (thousands of games,
    # dozens of players) so the embeddings overfit easily. Applies to matrices
    # only (see OutcomeModel.param_groups).
    weight_decay: float = 5e-3
    batch_size: int = 256
    max_epochs: int = 200
    patience: int = 20  # early-stop patience on val log-loss
    # Auxiliary regression heads (duration, etc.); weight 0 disables.
    aux_duration_weight: float = 0.0
    seed: int = 1234


@dataclass(slots=True)
class Config:
    model: ModelConfig = field(default_factory=ModelConfig)
    train: TrainConfig = field(default_factory=TrainConfig)
