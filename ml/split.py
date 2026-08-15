"""Split a snapshot into train/dev and freeze the vocab from train only.

Two modes:
- ``temporal`` (default): train on older games, dev on the most recent fraction.
  The honest "predict the future" measure we report.
- ``random``: stratified random split. Measures raw capacity / overfitting gap.

The vocab is built from the **train** matches only; players/maps unseen in train
fall through to UNK at dev time, exactly as in production.

Usage::

    uv run python -m ml.split ml/data/snapshot-YYYYMMDD.jsonl.gz \\
        [--mode temporal|random] [--dev-frac 0.15] [--seed 1234]

Writes ``ml/data/split-<snapshot>/{train.jsonl.gz,dev.jsonl.gz,vocab.json,split.json}``.
"""

from __future__ import annotations

import argparse
import gzip
import json
import random
from datetime import UTC, datetime
from pathlib import Path

import structlog

from radarvan.api_types import MatchInfo

from .config import DATA_DIR
from .features import build_vocab
from .snapshot import is_1v1, load_snapshot

logger = structlog.get_logger(__name__)


def temporal_split(
    matches: list[MatchInfo], dev_frac: float, *, holdout_1v1: bool = False
) -> tuple[list[MatchInfo], list[MatchInfo]]:
    """Oldest games train, the most recent ``dev_frac`` are dev.

    1v1s are routed into train by default, whatever their date. Nearly every
    1v1 in the snapshot was played in the last few months, so a plain temporal
    cut puts most of them in dev: the model then trains on almost no 1v1s,
    "1v1" barely reaches the train-only vocab, and serving one falls back
    toward the UNK format embedding - exactly the state that including them was
    meant to fix. They're worth more as signal than as a held-out set at this
    volume. Pass ``holdout_1v1`` for the plain cut.

    The dev fraction applies to the games that can land in dev, so holding the
    1v1s back grows train rather than shrinking dev.
    """
    ordered = sorted(matches, key=lambda m: m.timestamp)
    if holdout_1v1:
        reserved, splittable = [], ordered
    else:
        reserved = [m for m in ordered if is_1v1(m)]
        splittable = [m for m in ordered if not is_1v1(m)]
    n_dev = max(1, round(len(splittable) * dev_frac))
    train = sorted([*splittable[:-n_dev], *reserved], key=lambda m: m.timestamp)
    return train, splittable[-n_dev:]


def random_split(
    matches: list[MatchInfo], dev_frac: float, seed: int
) -> tuple[list[MatchInfo], list[MatchInfo]]:
    rng = random.Random(seed)  # noqa: S311 - shuffling a dataset, not crypto
    shuffled = list(matches)
    rng.shuffle(shuffled)
    n_dev = max(1, round(len(shuffled) * dev_frac))
    return shuffled[n_dev:], shuffled[:n_dev]


def _write_jsonl_gz(matches: list[MatchInfo], path: Path) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        for m in matches:
            fh.write(m.model_dump_json())
            fh.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--mode", choices=("temporal", "random"), default="temporal")
    parser.add_argument("--dev-frac", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=1234)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument(
        "--holdout-1v1",
        action="store_true",
        help="temporal mode: let 1v1s fall into dev by date like anything else "
        "(default: route them into train - see temporal_split)",
    )
    args = parser.parse_args()

    matches = load_snapshot(args.snapshot)
    if len(matches) < 10:
        raise SystemExit(f"Too few matches to split: {len(matches)}")

    if args.mode == "temporal":
        train, dev = temporal_split(
            matches, args.dev_frac, holdout_1v1=args.holdout_1v1
        )
    else:
        train, dev = random_split(matches, args.dev_frac, args.seed)

    # Sibling map_features-<stamp>.json holds numeric map geometry (optional;
    # absent => the map-feature path falls back to mean features for every map).
    stamp = args.snapshot.name.split(".")[0].replace("snapshot-", "")
    map_feat_path = args.snapshot.parent / f"map_features-{stamp}.json"
    map_feat_table = (
        json.loads(map_feat_path.read_text()) if map_feat_path.exists() else None
    )
    if map_feat_table is None:
        logger.warning("no map_features file found", expected=str(map_feat_path))

    # Vocab is frozen from train only — dev sees UNK for novel players/maps.
    vocab = build_vocab(train, map_feat_table)

    out_dir = args.out_dir or (DATA_DIR / f"split-{stamp}-{args.mode}")
    out_dir.mkdir(parents=True, exist_ok=True)

    _write_jsonl_gz(train, out_dir / "train.jsonl.gz")
    _write_jsonl_gz(dev, out_dir / "dev.jsonl.gz")
    vocab.save(out_dir / "vocab.json")

    info = {
        "created_at": datetime.now(UTC).isoformat(),
        "snapshot": args.snapshot.name,
        "mode": args.mode,
        "dev_frac": args.dev_frac,
        "seed": args.seed,
        "holdout_1v1": args.holdout_1v1,
        "n_train": len(train),
        "n_dev": len(dev),
        "n_train_1v1": sum(1 for m in train if is_1v1(m)),
        "n_dev_1v1": sum(1 for m in dev if is_1v1(m)),
        "n_players": vocab.n_players,
        "n_maps": vocab.n_maps,
    }
    (out_dir / "split.json").write_text(json.dumps(info, indent=2, sort_keys=True))
    logger.info("wrote split", out_dir=str(out_dir), **info)


if __name__ == "__main__":
    main()
