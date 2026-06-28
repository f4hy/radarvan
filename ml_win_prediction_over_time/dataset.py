"""Torch ``Dataset`` / collate / Lightning ``DataModule`` over feature sequences.

Sequences are ragged (games differ in length), so collate pads to the batch-max
length and emits a float mask; the model and loss ignore padded timesteps.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from pathlib import Path

import lightning as L
import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset

from .features import FeatureStats, SeqMatch, match_to_sequence
from .snapshot import load_snapshot

# One standardized, label-tagged sequence ready for collation.
_Item = tuple[np.ndarray, int, int]  # (x[T,F] float32, label, length)


@dataclass(slots=True)
class Batch:
    x: torch.Tensor  # [B, T, F]
    mask: torch.Tensor  # [B, T] (1 = real timestep, 0 = pad)
    label: torch.Tensor  # [B] float (1 == team_a won)

    def to(self, device: torch.device) -> Batch:
        return Batch(**{f.name: getattr(self, f.name).to(device) for f in fields(self)})


class SeqDataset(Dataset[_Item]):
    def __init__(self, seqs: list[SeqMatch], stats: FeatureStats):
        self._items: list[_Item] = [
            (stats.apply(s.x).astype(np.float32), s.label, s.length) for s in seqs
        ]

    def __len__(self) -> int:
        return len(self._items)

    def __getitem__(self, idx: int) -> _Item:
        return self._items[idx]


def collate(items: list[_Item]) -> Batch:
    b = len(items)
    t_max = max(length for _, _, length in items)
    f = items[0][0].shape[1]
    x = torch.zeros((b, t_max, f), dtype=torch.float32)
    mask = torch.zeros((b, t_max), dtype=torch.float32)
    label = torch.zeros((b,), dtype=torch.float32)
    for i, (arr, lab, length) in enumerate(items):
        x[i, :length] = torch.from_numpy(arr[:length])
        mask[i, :length] = 1.0
        label[i] = float(lab)
    return Batch(x=x, mask=mask, label=label)


def encode_all(path: Path, stats: FeatureStats) -> list[SeqMatch]:
    seqs = [match_to_sequence(r) for r in load_snapshot(path)]
    return [s for s in seqs if s is not None]


class WinProbDataModule(L.LightningDataModule):
    """Loads a ``split-*`` directory (train/dev jsonl + feature_stats.json)."""

    def __init__(self, split_dir: Path, batch_size: int, num_workers: int = 0):
        super().__init__()
        self.split_dir = Path(split_dir)
        self.batch_size = batch_size
        self.num_workers = num_workers
        self.stats = FeatureStats.load(self.split_dir / "feature_stats.json")
        self._train: list[SeqMatch] = []
        self._dev: list[SeqMatch] = []

    def setup(self, stage: str | None = None) -> None:
        self._train = encode_all(self.split_dir / "train.jsonl.gz", self.stats)
        self._dev = encode_all(self.split_dir / "dev.jsonl.gz", self.stats)

    def train_dataloader(self) -> DataLoader[_Item]:
        return DataLoader(
            SeqDataset(self._train, self.stats),
            batch_size=self.batch_size,
            shuffle=True,
            collate_fn=collate,
            num_workers=self.num_workers,
        )

    def val_dataloader(self) -> DataLoader[_Item]:
        return DataLoader(
            SeqDataset(self._dev, self.stats),
            batch_size=self.batch_size,
            shuffle=False,
            collate_fn=collate,
            num_workers=self.num_workers,
        )
