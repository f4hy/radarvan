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

from .config import DATA_DIR
from .features import FeatureStats, match_to_sequence
from .snapshot import load_snapshot

logger = structlog.get_logger(__name__)


def _write_jsonl_gz(records: list[dict], path: Path) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, separators=(",", ":")))
            fh.write("\n")


def split(snapshot_path: Path, out_dir: Path, dev_frac: float = 0.15) -> Path:
    records = load_snapshot(snapshot_path)  # already time-sorted by snapshot.py
    if len(records) < 10:
        raise SystemExit(f"Too few matches to split: {len(records)}")
    cut = int(len(records) * (1.0 - dev_frac))
    train, dev = records[:cut], records[cut:]

    out_dir.mkdir(parents=True, exist_ok=True)
    _write_jsonl_gz(train, out_dir / "train.jsonl.gz")
    _write_jsonl_gz(dev, out_dir / "dev.jsonl.gz")

    seqs = [s for r in train if (s := match_to_sequence(r)) is not None]
    if not seqs:
        raise SystemExit("No encodable training sequences — check the snapshot.")
    stats = FeatureStats.fit(seqs)
    stats.save(out_dir / "feature_stats.json")

    (out_dir / "split.json").write_text(
        json.dumps(
            {
                "created_at": datetime.now(UTC).isoformat(),
                "snapshot": snapshot_path.name,
                "mode": "temporal",
                "dev_frac": dev_frac,
                "n_train": len(train),
                "n_dev": len(dev),
            },
            indent=2,
        )
    )
    logger.info("wrote split", dir=str(out_dir), n_train=len(train), n_dev=len(dev))
    return out_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--dev-frac", type=float, default=0.15)
    parser.add_argument("--out-dir", type=Path, default=None)
    args = parser.parse_args()

    configure_logging(dev=True)
    out_dir = args.out_dir
    if out_dir is None:
        stamp = datetime.now(UTC).strftime("%Y%m%d")
        out_dir = DATA_DIR / f"split-{stamp}-temporal"
    split(args.snapshot, out_dir, dev_frac=args.dev_frac)


if __name__ == "__main__":
    main()
