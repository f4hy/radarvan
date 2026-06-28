"""CPU inference + evaluation for the win-probability-over-time model.

Produce a win-probability curve for a single match::

    DATABASE_URL=... uv run --group ml python -m ml_win_prediction_over_time.predict \\
        <run_dir> --match-id 12345

Evaluate a run on its split's dev set vs the 0.5 coin-flip baseline::

    uv run --group ml python -m ml_win_prediction_over_time.predict <run_dir> --eval
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import numpy as np
import structlog
import torch

from radarvan import db as dbmod
from radarvan.db_utils import DatabaseManager
from radarvan.logging_config import configure_logging
from radarvan.replay_files import parse_json

from .config import BUCKET_SECONDS, N_FEATURES, Config, ModelConfig, TrainConfig
from .dataset import encode_all
from .features import FeatureStats, match_to_sequence
from .model import WinProbLitModule
from .snapshot import record_from_replay

logger = structlog.get_logger(__name__)


def load_run(run_dir: Path) -> tuple[WinProbLitModule, FeatureStats]:
    cfg_d = json.loads((run_dir / "config.json").read_text())
    cfg = Config(
        model=ModelConfig(**cfg_d["model"]), train=TrainConfig(**cfg_d["train"])
    )
    module = WinProbLitModule(cfg, N_FEATURES)
    ckpt = torch.load(run_dir / "best.ckpt", map_location="cpu", weights_only=False)
    module.load_state_dict(ckpt["state_dict"])
    module.eval()
    stats = FeatureStats.load(run_dir / "feature_stats.json")
    return module, stats


def win_prob_curve(
    module: WinProbLitModule, stats: FeatureStats, record: dict
) -> list[tuple[float, float]]:
    """Return [(minute, P(team_a wins)), ...] for one match record."""
    seq = match_to_sequence(record)
    if seq is None:
        return []
    x = torch.from_numpy(stats.apply(seq.x).astype(np.float32))[None]  # [1, T, F]
    with torch.no_grad():
        probs = torch.sigmoid(module.model(x))[0].tolist()
    return [((b + 1) * BUCKET_SECONDS / 60.0, p) for b, p in enumerate(probs)]


def _record_for_match(match_id: int) -> dict | None:
    constring = os.getenv("DATABASE_URL")
    if constring is None:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    db_manager = DatabaseManager(constring)
    with db_manager.SessionLocal() as session:
        uri = (
            session.query(dbmod.Match.json_s3_uri)
            .filter(dbmod.Match.match_id == match_id)
            .scalar()
        )
    if not uri:
        return None
    return record_from_replay(parse_json(uri))


def evaluate(run_dir: Path) -> dict[str, float]:
    """Mean masked log-loss + final-timestep accuracy on the split's dev set."""
    module, stats = load_run(run_dir)
    split_dir = run_dir.parent.parent
    dev = encode_all(split_dir / "dev.jsonl.gz", stats)
    total_ll, total_steps, correct = 0.0, 0, 0
    eps = 1e-7
    for seq in dev:
        x = torch.from_numpy(stats.apply(seq.x).astype(np.float32))[None]
        with torch.no_grad():
            probs = torch.sigmoid(module.model(x))[0].numpy()
        y = seq.label
        p = np.clip(probs, eps, 1 - eps)
        total_ll += float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).sum())
        total_steps += len(p)
        correct += int((probs[-1] > 0.5) == bool(y))
    n = len(dev)
    return {
        "n_dev": float(n),
        "log_loss": total_ll / max(total_steps, 1),
        "final_acc": correct / max(n, 1),
        "baseline_log_loss": float(np.log(2)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--match-id", type=int, default=None)
    parser.add_argument("--eval", action="store_true")
    args = parser.parse_args()

    configure_logging(dev=True)
    if args.eval:
        metrics = evaluate(args.run_dir)
        logger.info("eval", **metrics)
        return
    if args.match_id is not None:
        module, stats = load_run(args.run_dir)
        record = _record_for_match(args.match_id)
        if record is None:
            raise SystemExit(f"No usable replay for match {args.match_id}")
        curve = win_prob_curve(module, stats, record)
        actual = "team_a" if record["label_a_win"] else "team_b"
        print(f"match {args.match_id} — actual winner: {actual}")
        for minute, prob in curve:
            bar = "#" * int(prob * 40)
            print(f"  {minute:5.1f}m  P(team_a)={prob:.3f}  {bar}")
        return
    parser.error("pass --eval or --match-id")


if __name__ == "__main__":
    main()
