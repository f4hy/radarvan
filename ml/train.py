"""Train the outcome model on a ``split-*`` directory (uses the GPU if present).

Usage::

    uv run python -m ml.train ml/data/split-YYYYMMDD-temporal/ \\
        [--max-epochs 200] [--no-mlp] [--no-synergy] [--no-matchup]

Writes a self-contained run bundle under ``<split>/runs/<timestamp>/``:
``best.ckpt``, ``vocab.json`` (copied), and ``config.json``.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

import lightning as L
import structlog
import torch
import torch.nn.functional as F
from lightning.pytorch.callbacks import EarlyStopping, ModelCheckpoint

from .config import Config, TrainConfig
from .dataset import MatchDataModule, collate
from .features import EncodedMatch
from .model import OutcomeLitModule

logger = structlog.get_logger(__name__)


def _raw_logits(
    module: OutcomeLitModule, matches: list[EncodedMatch]
) -> tuple[torch.Tensor, torch.Tensor]:
    """Uncalibrated logits + labels for a set of encoded matches (CPU, no grad)."""
    logits, labels = [], []
    with torch.no_grad():
        for i in range(0, len(matches), 256):
            batch = collate(matches[i : i + 256])
            logits.append(module.model(batch))
            labels.append(batch.label)
    return torch.cat(logits), torch.cat(labels)


# Temperature is clamped to this range: well outside it means a degenerate
# (near-separable / tiny) calibration set, where the right move is "don't rescale".
_T_MIN, _T_MAX = 0.2, 10.0


def fit_temperature(logits: torch.Tensor, labels: torch.Tensor) -> float:
    """Single-parameter temperature scaling: minimise NLL of logit/T over T>0.

    One parameter, so it can't meaningfully overfit; the standard fix for an
    accurate-but-overconfident classifier (lowers log-loss without touching the
    ranking/AUC). Fit on held-out data only.

    Robust to degenerate calibration sets: a single-class or perfectly-separable
    set drives T→0/∞ (and LBFGS to NaN), so we clamp inside the objective and
    fall back to T=1 (no rescaling) when the result isn't sane.
    """
    if labels.unique().numel() < 2:
        return 1.0
    log_t = torch.zeros(1, requires_grad=True)
    opt = torch.optim.LBFGS([log_t], lr=0.1, max_iter=50, line_search_fn="strong_wolfe")

    def closure() -> torch.Tensor:
        opt.zero_grad()
        t = log_t.exp().clamp(_T_MIN, _T_MAX)
        loss = F.binary_cross_entropy_with_logits(logits / t, labels)
        loss.backward()
        return loss

    opt.step(closure)  # type: ignore[arg-type]
    t = float(log_t.exp().clamp(_T_MIN, _T_MAX).item())
    return t if torch.isfinite(torch.tensor(t)) else 1.0


def _calibrate(module: OutcomeLitModule, calib: list[EncodedMatch]) -> float:
    """Fit temperature on games the weights were **not** fitted on.

    That set is ``MatchDataModule._val`` — the recent tail of train, which is
    also what early stopping watched. It used to be the last 20% of the *fit*
    block, i.e. games the model had already memorised: an overfit net looks
    perfectly calibrated on its own training data, so the fit returned T < 1
    (making it *more* confident) exactly when it needed T > 1. That is why the
    model out-ranked a 17-parameter logistic on AUC while losing to it on
    log-loss.
    """
    logits, labels = _raw_logits(module, calib)
    return fit_temperature(logits, labels)


def select_accelerator(requested: str) -> str:
    """Resolve 'auto' to 'gpu' only if CUDA can actually launch a kernel.

    ``torch.cuda.is_available()`` returns True even when the installed wheel has
    no kernel image for the GPU's compute capability (e.g. an old Pascal card vs
    a recent torch build), which then crashes mid-train with
    cudaErrorNoKernelImageForDevice. Probe with a real op + sync so we fall back
    to CPU cleanly instead. Pass --accelerator gpu to force it anyway.
    """
    if requested != "auto":
        return requested
    if not torch.cuda.is_available():
        return "cpu"
    try:
        x = torch.zeros(8, device="cuda")
        _ = (x + 1).sum().item()  # forces a kernel launch + device sync
        return "gpu"
    except RuntimeError as e:
        logger.warning(
            "cuda present but unusable; falling back to CPU",
            device=torch.cuda.get_device_name(0),
            capability=torch.cuda.get_device_capability(0),
            supported=torch.cuda.get_arch_list(),
            error=str(e).splitlines()[0],
        )
        return "cpu"


def _refit_on_full_train(
    split_dir: Path, cfg: Config, epochs: int, accelerator: str
) -> OutcomeLitModule:
    """Retrain from scratch on train + the validation tail, for a fixed budget.

    Same seed and hyperparameters; the only thing carried over from the
    early-stopped run is ``epochs``. No validation loader, so nothing here can
    select on anything.
    """
    dm = MatchDataModule(
        split_dir,
        batch_size=cfg.train.batch_size,
        recency_half_life_days=cfg.train.recency_half_life_days,
        val_frac=0.0,  # fit on the whole train split
    )
    dm.setup()
    module = OutcomeLitModule(dm.vocab, cfg)
    trainer = L.Trainer(
        max_epochs=max(1, epochs),
        accelerator=accelerator,
        devices="auto",
        enable_checkpointing=False,
        enable_progress_bar=True,
        limit_val_batches=0,
        num_sanity_val_steps=0,
        log_every_n_steps=10,
        logger=False,
    )
    trainer.fit(module, train_dataloaders=dm.train_dataloader())
    return module.cpu().eval()


def train(split_dir: Path, cfg: Config, accelerator: str = "auto") -> Path:
    L.seed_everything(cfg.train.seed, workers=True)
    accelerator = select_accelerator(accelerator)
    logger.info("accelerator", using=accelerator)
    dm = MatchDataModule(
        split_dir,
        batch_size=cfg.train.batch_size,
        recency_half_life_days=cfg.train.recency_half_life_days,
        val_frac=cfg.train.val_frac,
    )
    dm.setup()
    logger.info(
        "data",
        n_players=dm.vocab.n_players,
        n_maps=dm.vocab.n_maps,
        n_train=len(dm._train),
        n_val=len(dm._val),
        n_dev=len(dm._dev),
        recency_half_life_days=cfg.train.recency_half_life_days,
        val_frac=cfg.train.val_frac,
    )

    module = OutcomeLitModule(dm.vocab, cfg)

    run_dir = split_dir / "runs" / datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    ckpt_cb = ModelCheckpoint(
        dirpath=run_dir,
        filename="best",
        monitor="val_loss",
        mode="min",
        save_top_k=1,
    )
    early = EarlyStopping(monitor="val_loss", mode="min", patience=cfg.train.patience)

    trainer = L.Trainer(
        max_epochs=cfg.train.max_epochs,
        accelerator=accelerator,  # probed: GPU only if it can launch a kernel.
        devices="auto",
        callbacks=[ckpt_cb, early],
        log_every_n_steps=10,
        enable_progress_bar=True,
        logger=False,  # checkpoints go to run_dir; no stray lightning_logs/
    )
    trainer.fit(module, datamodule=dm)

    # Reload the best (lowest val_loss) weights onto CPU and fit temperature on
    # the same held-out validation tail. ModelCheckpoint saved the
    # pre-calibration weights.
    module = module.cpu()
    ckpt = torch.load(ckpt_cb.best_model_path, map_location="cpu", weights_only=False)
    module.load_state_dict(ckpt["state_dict"])
    module.eval()
    temperature = _calibrate(module, dm._val)
    best_epoch = int(ckpt.get("epoch", cfg.train.max_epochs))

    if cfg.train.refit_on_full and cfg.train.val_frac > 0:
        module = _refit_on_full_train(split_dir, cfg, best_epoch + 1, accelerator)
        torch.save({"state_dict": module.state_dict()}, run_dir / "best.ckpt")

    shutil.copy(split_dir / "vocab.json", run_dir / "vocab.json")
    (run_dir / "config.json").write_text(
        json.dumps(dataclasses.asdict(cfg), indent=2, default=str)
    )
    (run_dir / "calibration.json").write_text(
        json.dumps({"temperature": temperature}, indent=2)
    )
    logger.info(
        "done",
        best=str(run_dir / "best.ckpt"),
        val_loss=ckpt_cb.best_model_score,
        best_epoch=best_epoch,
        refit_on_full=cfg.train.refit_on_full and cfg.train.val_frac > 0,
        temperature=round(temperature, 3),
    )
    return run_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("split_dir", type=Path)
    parser.add_argument("--max-epochs", type=int, default=None)
    parser.add_argument("--no-mlp", action="store_true")
    parser.add_argument("--no-synergy", action="store_true")
    parser.add_argument("--no-matchup", action="store_true")
    parser.add_argument(
        "--no-map", action="store_true", help="Drop the map from the encoder entirely."
    )
    parser.add_argument(
        "--no-size-norm",
        action="store_true",
        help="Sum-pool each team instead of normalising by team size.",
    )
    parser.add_argument(
        "--no-refit",
        action="store_true",
        help="Keep the early-stopped weights instead of refitting on all of train.",
    )
    parser.add_argument(
        "--val-frac",
        type=float,
        default=None,
        help="Fraction of train held out for early stopping + temperature "
        "(0 = validate on dev, which leaks the reported set into model selection).",
    )
    parser.add_argument(
        "--global-bias",
        action="store_true",
        help="Add a team-id base-rate bias (default off -> order-invariant).",
    )
    parser.add_argument(
        "--map-features",
        action="store_true",
        help="Use numeric map geometry features instead of the map-name embedding.",
    )
    parser.add_argument("--aux-duration-weight", type=float, default=None)
    parser.add_argument(
        "--recency-half-life",
        type=float,
        default=None,
        help="Half-life in days for down-weighting old training games "
        f"(default {TrainConfig().recency_half_life_days}).",
    )
    parser.add_argument(
        "--no-recency",
        action="store_true",
        help="Weight every training game equally, however old.",
    )
    parser.add_argument(
        "--accelerator",
        choices=("auto", "cpu", "gpu"),
        default="auto",
        help="'auto' falls back to CPU if the GPU can't launch kernels.",
    )
    args = parser.parse_args()

    cfg = Config()
    if args.max_epochs is not None:
        cfg.train.max_epochs = args.max_epochs
    if args.aux_duration_weight is not None:
        cfg.train.aux_duration_weight = args.aux_duration_weight
    if args.no_recency:
        cfg.train.recency_half_life_days = None
    elif args.recency_half_life is not None:
        cfg.train.recency_half_life_days = args.recency_half_life
    cfg.model.use_mlp = not args.no_mlp
    cfg.model.use_synergy = not args.no_synergy
    cfg.model.use_matchup = not args.no_matchup
    cfg.model.use_global_bias = args.global_bias
    cfg.model.use_map_features = args.map_features
    cfg.model.use_map = not args.no_map
    cfg.model.size_norm = not args.no_size_norm
    if args.val_frac is not None:
        cfg.train.val_frac = args.val_frac
    if args.no_refit:
        cfg.train.refit_on_full = False

    train(args.split_dir, cfg, accelerator=args.accelerator)


if __name__ == "__main__":
    main()
