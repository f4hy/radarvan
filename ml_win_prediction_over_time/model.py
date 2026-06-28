"""Sequence model: a causal GRU that emits P(team_a wins) at every timestep.

Causal (unidirectional) so the prediction at time t only depends on events up to
t — the same information a live win-probability bar would have. Trained with a
time-weighted, masked BCE: every timestep is supervised against the final
outcome, but later timesteps (where the game is more decided) carry more weight.
"""

from __future__ import annotations

import lightning as L
import torch
import torch.nn.functional as F
from torch import nn

from .config import Config


class WinProbModel(nn.Module):
    def __init__(self, cfg: Config, n_features: int):
        super().__init__()
        m = cfg.model
        self.gru = nn.GRU(
            input_size=n_features,
            hidden_size=m.hidden,
            num_layers=m.num_layers,
            batch_first=True,
            dropout=m.dropout if m.num_layers > 1 else 0.0,
            bidirectional=False,
        )
        self.head = nn.Linear(m.hidden, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [B, T, F] -> logits [B, T]
        out, _ = self.gru(x)
        return self.head(out).squeeze(-1)


def _time_weights(mask: torch.Tensor, late_weight: float) -> torch.Tensor:
    """Per-timestep weights ramping 1 -> late_weight across each game's length."""
    lengths = mask.sum(dim=1, keepdim=True)  # [B, 1]
    pos = torch.cumsum(mask, dim=1)  # 1..length on real steps
    frac = (pos - 1) / (lengths - 1).clamp_min(1.0)
    return (1.0 + (late_weight - 1.0) * frac) * mask


def _last_logits(logits: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    """Logit at each sample's final real timestep."""
    last = (mask.sum(dim=1).long() - 1).clamp_min(0)  # [B]
    return logits.gather(1, last[:, None]).squeeze(1)


class WinProbLitModule(L.LightningModule):
    def __init__(self, cfg: Config, n_features: int):
        super().__init__()
        self.save_hyperparameters(ignore=["cfg"])
        self.cfg = cfg
        self.model = WinProbModel(cfg, n_features)

    def _loss(self, batch) -> tuple[torch.Tensor, torch.Tensor]:
        logits = self.model(batch.x)  # [B, T]
        target = batch.label[:, None].expand_as(logits)
        bce = F.binary_cross_entropy_with_logits(logits, target, reduction="none")
        w = _time_weights(batch.mask, self.cfg.train.late_weight)
        loss = (bce * w).sum() / w.sum().clamp_min(1.0)
        return loss, logits

    def training_step(self, batch, _idx) -> torch.Tensor:
        loss, _ = self._loss(batch)
        self.log("train_loss", loss, prog_bar=True, batch_size=batch.label.shape[0])
        return loss

    def validation_step(self, batch, _idx) -> torch.Tensor:
        loss, logits = self._loss(batch)
        bsz = batch.label.shape[0]
        # Plain (unweighted) masked log-loss across all timesteps, for monitoring.
        target = batch.label[:, None].expand_as(logits)
        bce = F.binary_cross_entropy_with_logits(logits, target, reduction="none")
        flat = (bce * batch.mask).sum() / batch.mask.sum().clamp_min(1.0)
        self.log("val_loss", flat, prog_bar=True, batch_size=bsz)
        # Accuracy at the final timestep (should be near-perfect if signal exists).
        final = _last_logits(logits, batch.mask)
        acc = ((final > 0).float() == batch.label).float().mean()
        self.log("val_acc_final", acc, prog_bar=True, batch_size=bsz)
        return loss

    def configure_optimizers(self) -> torch.optim.Optimizer:
        return torch.optim.AdamW(
            self.parameters(),
            lr=self.cfg.train.lr,
            weight_decay=self.cfg.train.weight_decay,
        )
