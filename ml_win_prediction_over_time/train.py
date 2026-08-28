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
from lightning.pytorch.callbacks import EarlyStopping, ModelCheckpoint

from .config import N_FEATURES, Config
from .dataset import WinProbDataModule
from .model import WinProbLitModule

logger = structlog.get_logger(__name__)


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
    early = EarlyStopping(
        monitor="val_loss", mode="min", patience=cfg.train.patience
    )

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

    shutil.copy(split_dir / "feature_stats.json", run_dir / "feature_stats.json")
    (run_dir / "config.json").write_text(
        json.dumps(dataclasses.asdict(cfg), indent=2, default=str)
    )
    logger.info(
        "done", best=str(ckpt_cb.best_model_path), val_loss=ckpt_cb.best_model_score
    )
    return run_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("split_dir", type=Path)
    parser.add_argument("--max-epochs", type=int, default=None)
    parser.add_argument("--hidden", type=int, default=None)
    parser.add_argument("--lr", type=float, default=None)
    parser.add_argument(
        "--accelerator", choices=("auto", "cpu", "gpu"), default="auto"
    )
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
