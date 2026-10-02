"""Split a snapshot into temporal train/dev and freeze feature stats from train.

Temporal (not random) split: train on the earliest games, validate on the most
recent, mirroring how the model is actually used (predict future matches). The
standardization stats are fit on train only, so dev never leaks into them.

Usage::

    uv run --group ml python -m ml_win_prediction_over_time.split \\
        ml_win_prediction_over_time/data/snapshot-YYYYMMDD.jsonl.gz [--dev-frac 0.15]
"""

from __future__ import annotations

import argparse
import gzip
import json
from datetime import UTC, datetime
from pathlib import Path

import structlog

from radarvan.logging_config import configure_logging

from . import pregame
from .config import DATA_DIR
from .features import FeatureStats, feature_names, match_to_sequence
from .snapshot import load_snapshot

logger = structlog.get_logger(__name__)


def _write_jsonl_gz(records: list[dict], path: Path) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, separators=(",", ":")))
            fh.write("\n")


def write_split(
    train: list[dict],
    dev: list[dict],
    out_dir: Path,
    drop: frozenset[str] = frozenset(),
    meta: dict | None = None,
    oof_prior: bool = True,
) -> Path:
    """Write train/dev with frozen prior logits, the prior itself and feature stats.

    The prior is a fitted model, so it is frozen from train like the feature
    stats. Train records carry out-of-fold logits (see ``pregame.oof_logits``);
    dev records the full-train fit, exactly what serving computes.
    """
    prior = pregame.fit(train)
    train_logits = (
        pregame.oof_logits(train)
        if oof_prior
        else [prior.logit(r["team_a_players"], r["team_b_players"]) for r in train]
    )
    train = [{**r, "prior_logit": z} for r, z in zip(train, train_logits, strict=True)]
    dev = [
        {**r, "prior_logit": prior.logit(r["team_a_players"], r["team_b_players"])}
        for r in dev
    ]

    out_dir.mkdir(parents=True, exist_ok=True)
    _write_jsonl_gz(train, out_dir / "train.jsonl.gz")
    _write_jsonl_gz(dev, out_dir / "dev.jsonl.gz")
    prior.save(out_dir / "pregame_prior.json")

    seqs = [
        s
        for r in train
        if (s := match_to_sequence(r, prior_logit=r["prior_logit"])) is not None
    ]
    if not seqs:
        raise SystemExit("No encodable training sequences — check the snapshot.")
    FeatureStats.fit(seqs, feature_names(drop)).save(out_dir / "feature_stats.json")

    (out_dir / "split.json").write_text(
        json.dumps(
            {
                "created_at": datetime.now(UTC).isoformat(),
                **(meta or {}),
                "dropped_groups": sorted(drop),
                "oof_prior": oof_prior,
                "n_train": len(train),
                "n_dev": len(dev),
                "n_prior_players": len(prior.players),
            },
            indent=2,
        )
    )
    logger.info("wrote split", dir=str(out_dir), n_train=len(train), n_dev=len(dev))
    return out_dir


def split(
    snapshot_path: Path,
    out_dir: Path,
    dev_frac: float = 0.15,
    drop: frozenset[str] = frozenset(),
) -> Path:
    records = load_snapshot(snapshot_path)  # already time-sorted by snapshot.py
    if len(records) < 10:
        raise SystemExit(f"Too few matches to split: {len(records)}")
    cut = int(len(records) * (1.0 - dev_frac))
    meta = {"snapshot": snapshot_path.name, "mode": "temporal", "dev_frac": dev_frac}
    return write_split(records[:cut], records[cut:], out_dir, drop, meta)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--dev-frac", type=float, default=0.15)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument(
        "--drop", nargs="*", default=[], help="feature groups to leave out"
    )
    args = parser.parse_args()

    configure_logging(dev=True)
    out_dir = args.out_dir
    if out_dir is None:
        stamp = datetime.now(UTC).strftime("%Y%m%d")
        out_dir = DATA_DIR / f"split-{stamp}-temporal"
    split(args.snapshot, out_dir, dev_frac=args.dev_frac, drop=frozenset(args.drop))


if __name__ == "__main__":
    main()
