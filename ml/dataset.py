"""Torch ``Dataset`` / collate / Lightning ``DataModule`` over encoded matches.

Teams are ragged (1v1 .. 3v3+), so collate pads each team to the batch-max team
size and emits a float mask; the model pools/cross-products under the mask so
padded slots contribute nothing.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from pathlib import Path

import lightning as L
import torch
from torch.utils.data import DataLoader, Dataset

from .features import EncodedMatch, Vocab, encode_match
from .snapshot import load_snapshot


@dataclass(slots=True)
class Batch:
    # [B, T] team feature ids; [B, T] mask (1=real, 0=pad). a/b = the two teams.
    a_player: torch.Tensor
    a_general: torch.Tensor
    a_faction: torch.Tensor
    a_start: torch.Tensor
    a_mask: torch.Tensor
    b_player: torch.Tensor
    b_general: torch.Tensor
    b_faction: torch.Tensor
    b_start: torch.Tensor
    b_mask: torch.Tensor
    map: torch.Tensor  # [B] (map-name embedding path)
    map_feat: torch.Tensor  # [B, N_MAP_FEATURES] (numeric map-feature path)
    fmt: torch.Tensor  # [B]
    label: torch.Tensor  # [B] float (1 == team_a won)
    duration: torch.Tensor  # [B] float

    def to(self, device: torch.device) -> Batch:
        return Batch(
            **{f.name: getattr(self, f.name).to(device) for f in fields(self)}
        )


class MatchDataset(Dataset[EncodedMatch]):
    def __init__(self, matches: list[EncodedMatch]):
        self._matches = matches

    def __len__(self) -> int:
        return len(self._matches)

    def __getitem__(self, idx: int) -> EncodedMatch:
        return self._matches[idx]


def _pad_team(
    teams: list[list[tuple[int, int, int, int]]], max_t: int
) -> tuple[torch.Tensor, ...]:
    """Stack a list of teams (each a list of (player,general,faction,start) tuples)
    into [B, max_t] tensors + mask."""
    b = len(teams)
    player = torch.zeros((b, max_t), dtype=torch.long)
    general = torch.zeros((b, max_t), dtype=torch.long)
    faction = torch.zeros((b, max_t), dtype=torch.long)
    start = torch.zeros((b, max_t), dtype=torch.long)
    mask = torch.zeros((b, max_t), dtype=torch.float32)
    for i, team in enumerate(teams):
        for j, (pl, ge, fa, st) in enumerate(team):
            player[i, j] = pl
            general[i, j] = ge
            faction[i, j] = fa
            start[i, j] = st
            mask[i, j] = 1.0
    return player, general, faction, start, mask


def collate(matches: list[EncodedMatch]) -> Batch:
    max_t = max(
        max(len(m.team_a), len(m.team_b)) for m in matches
    )

    def as_tuples(team: list) -> list[tuple[int, int, int, int]]:
        return [(p.player, p.general, p.faction, p.start_pos) for p in team]

    a = _pad_team([as_tuples(m.team_a) for m in matches], max_t)
    b = _pad_team([as_tuples(m.team_b) for m in matches], max_t)
    return Batch(
        a_player=a[0], a_general=a[1], a_faction=a[2], a_start=a[3], a_mask=a[4],
        b_player=b[0], b_general=b[1], b_faction=b[2], b_start=b[3], b_mask=b[4],
        map=torch.tensor([m.map for m in matches], dtype=torch.long),
        map_feat=torch.tensor(
            [m.map_feat for m in matches], dtype=torch.float32
        ),
        fmt=torch.tensor([m.fmt for m in matches], dtype=torch.long),
        label=torch.tensor([float(m.label) for m in matches], dtype=torch.float32),
        duration=torch.tensor(
            [m.duration_minutes for m in matches], dtype=torch.float32
        ),
    )


def encode_all(matches_path: Path, vocab: Vocab) -> list[EncodedMatch]:
    encoded = [encode_match(m, vocab) for m in load_snapshot(matches_path)]
    return [e for e in encoded if e is not None]


class MatchDataModule(L.LightningDataModule):
    """Loads a ``split-*`` directory (train/dev jsonl + vocab)."""

    def __init__(self, split_dir: Path, batch_size: int, num_workers: int = 0):
        super().__init__()
        self.split_dir = Path(split_dir)
        self.batch_size = batch_size
        self.num_workers = num_workers
        self.vocab = Vocab.load(self.split_dir / "vocab.json")
        self._train: list[EncodedMatch] = []
        self._dev: list[EncodedMatch] = []

    def setup(self, stage: str | None = None) -> None:
        self._train = encode_all(self.split_dir / "train.jsonl.gz", self.vocab)
        self._dev = encode_all(self.split_dir / "dev.jsonl.gz", self.vocab)

    def train_dataloader(self) -> DataLoader[EncodedMatch]:
        return DataLoader(
            MatchDataset(self._train),
            batch_size=self.batch_size,
            shuffle=True,
            collate_fn=collate,
            num_workers=self.num_workers,
        )

    def val_dataloader(self) -> DataLoader[EncodedMatch]:
        return DataLoader(
            MatchDataset(self._dev),
            batch_size=self.batch_size,
            shuffle=False,
            collate_fn=collate,
            num_workers=self.num_workers,
        )
