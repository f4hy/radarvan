"""DeepSets outcome model + Lightning wrapper.

logit(A vs B) = [score(t_A) - score(t_B)]   # individual + player/general/map interactions
              + [syn(A) - syn(B)]           # low-rank teammate synergy (symmetric)
              + matchup(A, B)               # skew-symmetric general counter

Each additive term is toggleable (``ModelConfig``) so we can ablate to a linear
Bradley-Terry / openskill-equivalent floor. The head is structurally
antisymmetric (difference of scores; skew-symmetric matchup), so team ordering
can never bias the prediction. See ``ml/model_design.md``.
"""

from __future__ import annotations

import lightning as L
import torch
import torch.nn.functional as F
from torch import nn
from torchmetrics.classification import BinaryAccuracy, BinaryAUROC

from .config import Config, ModelConfig
from .dataset import Batch
from .features import Vocab
from .map_features import N_MAP_FEATURES


def _build_mlp(
    in_dim: int, hidden: tuple[int, ...], dropout: float
) -> tuple[nn.Module, int]:
    layers: list[nn.Module] = []
    d = in_dim
    for h in hidden:
        layers += [nn.Linear(d, h), nn.ReLU(), nn.Dropout(dropout)]
        d = h
    return nn.Sequential(*layers), d


class OutcomeModel(nn.Module):
    def __init__(self, vocab: Vocab, cfg: ModelConfig):
        super().__init__()
        self.cfg = cfg
        self.n_generals = vocab.n_generals

        self.player_emb = nn.Embedding(vocab.n_players, cfg.emb_player, padding_idx=0)
        self.general_emb = nn.Embedding(vocab.n_generals, cfg.emb_general, padding_idx=0)
        self.faction_emb = nn.Embedding(vocab.n_factions, cfg.emb_faction, padding_idx=0)
        self.fmt_emb = nn.Embedding(vocab.n_formats, cfg.emb_format, padding_idx=0)

        # Map representation -> a cfg.emb_map vector, either projected from numeric
        # geometry features (generalises across maps) or a per-map-name embedding.
        if cfg.use_map_features:
            self.map_proj: nn.Linear | None = nn.Linear(N_MAP_FEATURES, cfg.emb_map)
            self.map_emb: nn.Embedding | None = None
        else:
            self.map_proj = None
            self.map_emb = nn.Embedding(vocab.n_maps, cfg.emb_map, padding_idx=0)

        in_dim = (
            cfg.emb_player + cfg.emb_general + cfg.emb_faction
            + cfg.emb_map + cfg.emb_format
        )
        if cfg.use_starting_position:
            self.start_emb: nn.Embedding | None = nn.Embedding(16, 4, padding_idx=0)
            in_dim += 4
        else:
            self.start_emb = None

        if cfg.use_mlp:
            self.encoder, enc_out = _build_mlp(in_dim, cfg.mlp_hidden, cfg.dropout)
        else:
            # Linear floor: encoder is a single linear map (no nonlinearity), so
            # the whole score term stays linear in the embeddings.
            enc_out = cfg.mlp_hidden[-1] if cfg.mlp_hidden else in_dim
            self.encoder = nn.Linear(in_dim, enc_out)
        self.score_head = nn.Linear(enc_out, 1)

        # (2) synergy: per-player low-rank vector; team bonus = sum_{i<j} u_i . u_j.
        if cfg.use_synergy:
            self.synergy_emb: nn.Embedding | None = nn.Embedding(
                vocab.n_players, cfg.synergy_k, padding_idx=0
            )
        else:
            self.synergy_emb = None

        # (3) matchup: skew-symmetric general-vs-general advantage A = W - W^T.
        if cfg.use_matchup:
            self.matchup_w: nn.Parameter | None = nn.Parameter(
                torch.zeros(vocab.n_generals, vocab.n_generals)
            )
        else:
            self.matchup_w = None

        # Optional auxiliary duration head (regression on combined team rep).
        self.duration_head = nn.Linear(enc_out, 1)

        # Global bias: captures the base-rate / team-id asymmetry (team_a is the
        # lower team id, and empirically wins != 50%). This is the one term that
        # is *not* antisymmetric under team swap. With it off the model is
        # structurally order-invariant: P(A) + P(B after swap) == 1 exactly.
        if cfg.use_global_bias:
            self.global_bias: nn.Parameter | None = nn.Parameter(torch.zeros(1))
        else:
            self.global_bias = None
        # Post-hoc temperature (calibration). 1.0 until fit on held-out data;
        # a non-persistent-free buffer so it travels in the state_dict.
        self.register_buffer("temperature", torch.ones(1))

        self._init_weights()

    def _init_weights(self) -> None:
        """Near-zero init so the initial logit ~= 0 (loss ~= ln 2).

        Default Embedding init (N(0,1)) made the quadratic synergy term produce
        large logits at step 0, i.e. extreme overconfidence the model then had to
        unlearn. Small embeddings + zero score head start calibrated.
        """
        embeds = [
            self.player_emb, self.general_emb, self.faction_emb, self.fmt_emb,
        ]
        if self.map_emb is not None:
            embeds.append(self.map_emb)
        if self.synergy_emb is not None:
            embeds.append(self.synergy_emb)
        if self.start_emb is not None:
            embeds.append(self.start_emb)
        with torch.no_grad():
            for emb in embeds:
                nn.init.normal_(emb.weight, std=0.05)
                emb.weight[0].zero_()  # keep padding row at 0
            nn.init.zeros_(self.score_head.weight)
            nn.init.zeros_(self.score_head.bias)

    def param_groups(self, weight_decay: float) -> list[dict[str, object]]:
        """Weight-decay the matrices (embeddings/weights), never the 1-D params.

        Decaying ``global_bias`` would fight the base rate it's meant to learn,
        and decaying biases is standard practice to avoid.
        """
        decay, no_decay = [], []
        for p in self.parameters():
            if not p.requires_grad:
                continue
            (decay if p.ndim >= 2 else no_decay).append(p)
        return [
            {"params": decay, "weight_decay": weight_decay},
            {"params": no_decay, "weight_decay": 0.0},
        ]

    # --- per-team encoding -------------------------------------------------

    def _encode_players(
        self,
        player: torch.Tensor,
        general: torch.Tensor,
        faction: torch.Tensor,
        start: torch.Tensor,
        e_map: torch.Tensor,
        e_fmt: torch.Tensor,
    ) -> torch.Tensor:
        """[B, T, *] ids -> per-player hidden [B, T, H]. Match-level map/fmt broadcast."""
        t = player.shape[1]
        feats = [
            self.player_emb(player),
            self.general_emb(general),
            self.faction_emb(faction),
            e_map.unsqueeze(1).expand(-1, t, -1),
            e_fmt.unsqueeze(1).expand(-1, t, -1),
        ]
        if self.start_emb is not None:
            feats.append(self.start_emb(start.clamp(max=15)))
        x = torch.cat(feats, dim=-1)
        return self.encoder(x)

    def _team_score(self, h: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        """Masked-sum of per-player scalar scores -> [B]."""
        per_player = self.score_head(h).squeeze(-1)  # [B, T]
        return (per_player * mask).sum(dim=1)

    def _team_pool(self, h: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        return (h * mask.unsqueeze(-1)).sum(dim=1)  # [B, H]

    def _synergy(self, player: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        if self.synergy_emb is None:
            return torch.zeros(player.shape[0], device=player.device)
        u = self.synergy_emb(player) * mask.unsqueeze(-1)  # [B, T, k]
        sum_u = u.sum(dim=1)  # [B, k]
        # sum_{i<j} u_i.u_j = 0.5(||sum u||^2 - sum ||u||^2)
        sq_of_sum = (sum_u * sum_u).sum(dim=-1)
        sum_of_sq = (u * u).sum(dim=(1, 2))
        return 0.5 * (sq_of_sum - sum_of_sq)

    def _general_counts(
        self, general: torch.Tensor, mask: torch.Tensor
    ) -> torch.Tensor:
        """[B, T] general ids -> [B, G] masked counts per general."""
        b = general.shape[0]
        counts = torch.zeros(b, self.n_generals, device=general.device)
        counts.scatter_add_(1, general, mask)
        return counts

    def _matchup(self, batch: Batch) -> torch.Tensor:
        if self.matchup_w is None:
            return torch.zeros(batch.map.shape[0], device=batch.map.device)
        a = self.matchup_w - self.matchup_w.t()  # skew-symmetric
        c_a = self._general_counts(batch.a_general, batch.a_mask)
        c_b = self._general_counts(batch.b_general, batch.b_mask)
        # c_a^T A c_b ; antisymmetric under team swap because A is skew-symmetric.
        return torch.einsum("bg,gh,bh->b", c_a, a, c_b)

    # --- public ------------------------------------------------------------

    def _map_embed(self, batch: Batch) -> torch.Tensor:
        """[B, emb_map] map representation, from numeric features or name embedding."""
        if self.map_proj is not None:
            return self.map_proj(batch.map_feat)
        if self.map_emb is not None:
            return self.map_emb(batch.map)
        raise RuntimeError("no map representation configured")

    def _logit_terms(self, batch: Batch) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
        """Raw logit plus its additive decomposition (each term is [B])."""
        e_map = self._map_embed(batch)
        e_fmt = self.fmt_emb(batch.fmt)
        h_a = self._encode_players(
            batch.a_player, batch.a_general, batch.a_faction, batch.a_start, e_map, e_fmt
        )
        h_b = self._encode_players(
            batch.b_player, batch.b_general, batch.b_faction, batch.b_start, e_map, e_fmt
        )
        strength = self._team_score(h_a, batch.a_mask) - self._team_score(
            h_b, batch.b_mask
        )
        synergy = self._synergy(batch.a_player, batch.a_mask) - self._synergy(
            batch.b_player, batch.b_mask
        )
        matchup = self._matchup(batch)
        if self.global_bias is None:
            bias = torch.zeros(batch.map.shape[0], device=batch.map.device)
        else:
            bias = self.global_bias.expand(batch.map.shape[0])
        raw = strength + synergy + matchup + bias
        return raw, {
            "strength": strength,
            "synergy": synergy,
            "matchup": matchup,
            "bias": bias,
        }

    def forward(self, batch: Batch) -> torch.Tensor:
        raw, _ = self._logit_terms(batch)
        return raw

    def calibrated_logit(self, batch: Batch) -> torch.Tensor:
        """Forward logit divided by the (post-hoc fit) temperature. Use at inference."""
        return self.forward(batch) / self.temperature

    def explain(self, batch: Batch) -> dict[str, torch.Tensor]:
        """Per-term breakdown + calibrated probability of team_a winning ([B] each)."""
        raw, terms = self._logit_terms(batch)
        cal = raw / self.temperature
        return {
            **terms,
            "raw_logit": raw,
            "calibrated_logit": cal,
            "prob_team_a": torch.sigmoid(cal),
        }

    def predict_duration(self, batch: Batch) -> torch.Tensor:
        e_map = self._map_embed(batch)
        e_fmt = self.fmt_emb(batch.fmt)
        h_a = self._encode_players(
            batch.a_player, batch.a_general, batch.a_faction, batch.a_start, e_map, e_fmt
        )
        h_b = self._encode_players(
            batch.b_player, batch.b_general, batch.b_faction, batch.b_start, e_map, e_fmt
        )
        combined = self._team_pool(h_a, batch.a_mask) + self._team_pool(h_b, batch.b_mask)
        return self.duration_head(combined).squeeze(-1)


class OutcomeLitModule(L.LightningModule):
    def __init__(self, vocab: Vocab, cfg: Config):
        super().__init__()
        self.cfg = cfg
        self.model = OutcomeModel(vocab, cfg.model)
        self.val_acc = BinaryAccuracy()
        self.val_auc = BinaryAUROC()
        self._val_brier_sum = 0.0
        self._val_n = 0

    def forward(self, batch: Batch) -> torch.Tensor:  # type: ignore[override]
        return self.model(batch)

    def _loss(self, batch: Batch) -> tuple[torch.Tensor, torch.Tensor]:
        logit = self.model(batch)
        # batch.weight is all-ones unless recency weighting is on, and is
        # normalised to mean 1.0 by ml.dataset.recency_weighted, so the loss keeps
        # its scale either way (BCE's `weight` scales per-sample terms before the
        # mean, it does not divide by the weight sum).
        loss = F.binary_cross_entropy_with_logits(
            logit, batch.label, weight=batch.weight
        )
        w = self.cfg.train.aux_duration_weight
        if w > 0:
            pred_dur = self.model.predict_duration(batch)
            loss = loss + w * F.mse_loss(pred_dur, batch.duration)
        return loss, logit

    def training_step(self, batch: Batch, _idx: int) -> torch.Tensor:  # type: ignore[override]
        loss, _ = self._loss(batch)
        self.log("train_loss", loss, prog_bar=True, batch_size=batch.label.shape[0])
        return loss

    def validation_step(self, batch: Batch, _idx: int) -> None:  # type: ignore[override]
        loss, logit = self._loss(batch)
        prob = torch.sigmoid(logit)
        self.val_acc.update(prob, batch.label.int())
        self.val_auc.update(prob, batch.label.int())
        self._val_brier_sum += ((prob - batch.label) ** 2).sum().item()
        self._val_n += batch.label.shape[0]
        self.log("val_loss", loss, prog_bar=True, batch_size=batch.label.shape[0])

    def on_validation_epoch_end(self) -> None:
        self.log("val_acc", self.val_acc.compute(), prog_bar=True)
        self.log("val_auc", self.val_auc.compute(), prog_bar=True)
        if self._val_n:
            self.log("val_brier", self._val_brier_sum / self._val_n, prog_bar=True)
        self.val_acc.reset()
        self.val_auc.reset()
        self._val_brier_sum = 0.0
        self._val_n = 0

    def configure_optimizers(self) -> dict[str, object]:
        opt = torch.optim.AdamW(
            self.model.param_groups(self.cfg.train.weight_decay),
            lr=self.cfg.train.lr,
        )
        sched = torch.optim.lr_scheduler.CosineAnnealingLR(
            opt, T_max=self.cfg.train.max_epochs
        )
        return {"optimizer": opt, "lr_scheduler": sched}
