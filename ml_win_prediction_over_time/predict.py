"""CPU inference + evaluation for the win-probability-over-time model.

Produce a win-probability curve for a single match::

    DATABASE_URL=... uv run --group ml python -m ml_win_prediction_over_time.predict \\
        <run_dir> --match-id 12345

Evaluate a run on its split's dev set, by game phase, against the baselines in
``baselines.py`` (coin flip and a memoryless logistic on the current scoreboard)::

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
from .baselines import coin_flip_probs, static_logistic_probs
from .dataset import encode_all
from .features import FeatureStats, match_to_sequence
from .model import WinProbLitModule
from .pregame import PregamePrior
from .snapshot import record_from_replay

logger = structlog.get_logger(__name__)


def load_run(run_dir: Path) -> tuple[WinProbLitModule, FeatureStats, PregamePrior]:
    cfg_d = json.loads((run_dir / "config.json").read_text())
    cfg = Config(
        model=ModelConfig(**cfg_d["model"]), train=TrainConfig(**cfg_d["train"])
    )
    module = WinProbLitModule(cfg, N_FEATURES)
    ckpt = torch.load(run_dir / "best.ckpt", map_location="cpu", weights_only=False)
    module.load_state_dict(ckpt["state_dict"])
    module.eval()
    stats = FeatureStats.load(run_dir / "feature_stats.json")
    prior_path = run_dir / "pregame_prior.json"
    prior = (
        PregamePrior.load(prior_path) if prior_path.exists() else PregamePrior.neutral()
    )
    return module, stats, prior


def win_prob_curve(
    module: WinProbLitModule,
    stats: FeatureStats,
    record: dict,
    prior: PregamePrior | None = None,
    temperature: float = 1.0,
) -> list[tuple[float, float]]:
    """Return [(minute, P(team_a wins)), ...] for one match record."""
    logit = (
        prior.logit(record["team_a_players"], record["team_b_players"])
        if prior is not None
        else 0.0
    )
    seq = match_to_sequence(record, prior_logit=logit)
    if seq is None:
        return []
    x = torch.from_numpy(stats.apply(seq.x).astype(np.float32))[None]  # [1, T, F]
    with torch.no_grad():
        probs = torch.sigmoid(module.model(x)[0] / temperature).tolist()
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


PHASES = (
    (0.0, 0.2, "first 20%"),
    (0.2, 0.4, "20-40%"),
    (0.4, 0.6, "40-60%"),
    (0.6, 0.8, "60-80%"),
    (0.8, 1.01, "last 20%"),
)


def _log_loss(p: np.ndarray, y: np.ndarray) -> float:
    p = np.clip(p, 1e-7, 1 - 1e-7)
    return float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean())


def _flatten(
    curves: list[np.ndarray], dev: list
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Every timestep of every match as (prob, label, phase-in-match)."""
    p, y, ph = [], [], []
    for c, s in zip(curves, dev, strict=True):
        p.append(np.asarray(c, float))
        y.append(np.full(s.length, float(s.label)))
        ph.append(np.arange(1, s.length + 1) / s.length)
    return np.concatenate(p), np.concatenate(y), np.concatenate(ph)


def model_curves(
    module: WinProbLitModule, stats: FeatureStats, dev: list, temperature: float = 1.0
):
    out = []
    with torch.no_grad():
        for seq in dev:
            x = torch.from_numpy(stats.apply(seq.x).astype(np.float32))[None]
            out.append(torch.sigmoid(module.model(x)[0] / temperature).numpy())
    return out


def evaluate(run_dir: Path) -> dict[str, object]:
    """Log-loss by game phase for the model and the baselines it has to clear.

    Reported per phase rather than as one pooled number, because pooling hides
    the only interesting part. Late in a decided game every predictor looks
    brilliant; what separates them is the first half, when the answer is not yet
    written on the scoreboard. The pooled figure is dominated by whichever games
    ran long.

    Both the flat and the late-weighted log-loss are shown: training optimises
    the weighted one (``TrainConfig.late_weight``), so quoting only the flat one
    scores the model on something it was not asked to do.
    """
    module, stats, prior = load_run(run_dir)
    split_dir = run_dir.parent.parent
    dev = encode_all(split_dir / "dev.jsonl.gz", stats, prior)
    train = encode_all(split_dir / "train.jsonl.gz", stats, prior)

    temperature = 1.0
    calib = run_dir / "calibration.json"
    if calib.exists():
        temperature = float(json.loads(calib.read_text())["temperature"])

    curves = {
        "coin_flip": coin_flip_probs(dev),
        "static_logistic": static_logistic_probs(train, dev, stats),
        "gru": model_curves(module, stats, dev),
        "gru+temperature": model_curves(module, stats, dev, temperature),
    }

    rows: dict[str, object] = {"n_dev": len(dev), "temperature": temperature}
    print(f"\n=== dev evaluation ({len(dev)} matches) ===")
    header = f"{'':<20}{'log-loss':>10}{'weighted':>10}{'final acc':>11}   " + "".join(
        f"{name:>11}" for _, _, name in PHASES
    )
    print(header)
    for name, cs in curves.items():
        p, y, ph = _flatten(cs, dev)
        w = 1.0 + (TrainConfig().late_weight - 1.0) * ph
        pc = np.clip(p, 1e-7, 1 - 1e-7)
        weighted = float(
            (-(y * np.log(pc) + (1 - y) * np.log(1 - pc)) * w).sum() / w.sum()
        )
        final_acc = float(
            np.mean(
                [(c[-1] > 0.5) == bool(s.label) for c, s in zip(cs, dev, strict=True)]
            )
        )
        by_phase = [
            _log_loss(p[(ph >= lo) & (ph < hi)], y[(ph >= lo) & (ph < hi)])
            for lo, hi, _ in PHASES
        ]
        print(
            f"{name:<20}{_log_loss(p, y):>10.4f}{weighted:>10.4f}{final_acc:>11.3f}   "
            + "".join(f"{v:>11.3f}" for v in by_phase)
        )
        rows[name] = {
            "log_loss": _log_loss(p, y),
            "weighted_log_loss": weighted,
            "final_acc": final_acc,
            "by_phase": dict(zip([n for _, _, n in PHASES], by_phase, strict=True)),
        }
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--match-id", type=int, default=None)
    parser.add_argument("--eval", action="store_true")
    args = parser.parse_args()

    configure_logging(dev=True)
    if args.eval:
        metrics = evaluate(args.run_dir)
        # evaluate() prints the table itself; keep the log line to the headline.
        logger.info(
            "eval",
            n_dev=metrics["n_dev"],
            temperature=round(float(metrics["temperature"]), 3),
            gru_log_loss=round(metrics["gru"]["log_loss"], 4),  # type: ignore[index]
            static_log_loss=round(metrics["static_logistic"]["log_loss"], 4),  # type: ignore[index]
        )
        return
    if args.match_id is not None:
        module, stats, prior = load_run(args.run_dir)
        calib = args.run_dir / "calibration.json"
        temperature = (
            float(json.loads(calib.read_text())["temperature"])
            if calib.exists()
            else 1.0
        )
        record = _record_for_match(args.match_id)
        if record is None:
            raise SystemExit(f"No usable replay for match {args.match_id}")
        curve = win_prob_curve(module, stats, record, prior, temperature)
        actual = "team_a" if record["label_a_win"] else "team_b"
        print(f"match {args.match_id} — actual winner: {actual}")
        for minute, prob in curve:
            bar = "#" * int(prob * 40)
            print(f"  {minute:5.1f}m  P(team_a)={prob:.3f}  {bar}")
        return
    parser.error("pass --eval or --match-id")


if __name__ == "__main__":
    main()
