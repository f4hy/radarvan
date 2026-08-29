"""Train the win-probability-over-time model on a ``split-*`` dir (GPU if usable).

Usage::

    uv run --group ml python -m ml_win_prediction_over_time.train \\
        ml_win_prediction_over_time/data/split-YYYYMMDD-temporal/ [--max-epochs 100]

Writes a self-contained run bundle under ``<split>/runs/<timestamp>/``:
``best.ckpt``, ``feature_stats.json`` (copied), and ``config.json``.
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

from .config import N_FEATURES, Config
from .dataset import WinProbDataModule, collate
from .features import FeatureStats, SeqMatch
from .model import WinProbLitModule

logger = structlog.get_logger(__name__)

# Temperature is clamped to this range: well outside it means a degenerate
# calibration set, where the right move is "don't rescale".
_T_MIN, _T_MAX = 0.2, 10.0


def fit_temperature(logits: torch.Tensor, labels: torch.Tensor) -> float:
    """Single-parameter temperature scaling: minimise NLL of logit/T over T>0.

    Deliberately a near-copy of ``ml.train.fit_temperature`` rather than an
    import: that module pulls the whole pre-game stack (its dataset, its
    snapshot, the DB layer) in behind it for twenty lines of arithmetic, and the
    aggregation differs anyway - here every timestep of every validation
    sequence is one row.
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


def _val_logits(
    module: WinProbLitModule, seqs: list[SeqMatch], stats: FeatureStats
) -> tuple[torch.Tensor, torch.Tensor]:
    """Flat (logit, label) over every real timestep of every held-out sequence."""
    items = [(stats.apply(s.x), s.label, s.length) for s in seqs]
    logits, labels = [], []
    module.eval()
    with torch.no_grad():
        for i in range(0, len(items), 64):
            batch = collate(items[i : i + 64])
            out = module.model(batch.x)
            keep = batch.mask > 0
            logits.append(out[keep])
            labels.append(batch.label[:, None].expand_as(out)[keep])
    if not logits:
        return torch.zeros(0), torch.zeros(0)
    return torch.cat(logits), torch.cat(labels)


def _refit_on_full_train(
    split_dir: Path, cfg: Config, epochs: int, accelerator: str
) -> WinProbLitModule:
    """Retrain from scratch on train + the validation tail, for a fixed budget."""
    dm = WinProbDataModule(split_dir, batch_size=cfg.train.batch_size, val_frac=0.0)
    dm.setup()
    module = WinProbLitModule(cfg, N_FEATURES)
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


def select_accelerator(requested: str) -> str:
    """Resolve 'auto' to 'gpu' only if CUDA can actually launch a kernel.

    ``torch.cuda.is_available()`` returns True even when the installed wheel has
    no kernel image for the GPU's compute capability, which then crashes mid-train
    with cudaErrorNoKernelImageForDevice. Probe with a real op + sync so we fall
    back to CPU cleanly. Pass --accelerator gpu to force it.
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
            error=str(e).splitlines()[0],
        )
        return "cpu"


def train(split_dir: Path, cfg: Config, accelerator: str = "auto") -> Path:
    L.seed_everything(cfg.train.seed, workers=True)
    accelerator = select_accelerator(accelerator)
    logger.info("accelerator", using=accelerator)

    dm = WinProbDataModule(
        split_dir, batch_size=cfg.train.batch_size, val_frac=cfg.train.val_frac
    )
    dm.setup()
    logger.info(
        "data",
        n_train=len(dm._train),
        n_val=len(dm._val),
        n_dev=len(dm._dev),
        val_frac=cfg.train.val_frac,
    )

    module = WinProbLitModule(cfg, N_FEATURES)

    run_dir = split_dir / "runs" / datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    ckpt_cb = ModelCheckpoint(
        dirpath=run_dir, filename="best", monitor="val_loss", mode="min", save_top_k=1
    )
    early = EarlyStopping(monitor="val_loss", mode="min", patience=cfg.train.patience)

    trainer = L.Trainer(
        max_epochs=cfg.train.max_epochs,
        accelerator=accelerator,
        devices="auto",
        callbacks=[ckpt_cb, early],
        log_every_n_steps=10,
        enable_progress_bar=True,
        logger=False,
    )
    trainer.fit(module, datamodule=dm)

    # Best (lowest val_loss) weights back on CPU, then fit the temperature on the
    # same held-out tail - games the weights were never fitted on, which is the
    # only thing that makes the number meaningful.
    module = module.cpu()
    ckpt = torch.load(ckpt_cb.best_model_path, map_location="cpu", weights_only=False)
    module.load_state_dict(ckpt["state_dict"])
    module.eval()
    logits, labels = _val_logits(module, dm._val, dm.stats)
    temperature = fit_temperature(logits, labels)
    best_epoch = int(ckpt.get("epoch", cfg.train.max_epochs))

    if cfg.train.refit_on_full and cfg.train.val_frac > 0:
        module = _refit_on_full_train(split_dir, cfg, best_epoch + 1, accelerator)
        torch.save({"state_dict": module.state_dict()}, run_dir / "best.ckpt")

    shutil.copy(split_dir / "feature_stats.json", run_dir / "feature_stats.json")
    prior_path = split_dir / "pregame_prior.json"
    if prior_path.exists():
        shutil.copy(prior_path, run_dir / "pregame_prior.json")
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
    parser.add_argument("--hidden", type=int, default=None)
    parser.add_argument("--lr", type=float, default=None)
    parser.add_argument("--accelerator", choices=("auto", "cpu", "gpu"), default="auto")
    args = parser.parse_args()

    cfg = Config()
    if args.max_epochs is not None:
        cfg.train.max_epochs = args.max_epochs
    if args.hidden is not None:
        cfg.model.hidden = args.hidden
    if args.lr is not None:
        cfg.train.lr = args.lr

    train(args.split_dir, cfg, accelerator=args.accelerator)


if __name__ == "__main__":
    main()
