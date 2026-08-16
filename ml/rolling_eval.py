"""Rolling-origin evaluation: train up to a cut, score the next block, repeat.

A single temporal split spends 85% of the corpus on training and leaves ~180
games to measure with, which is not enough to tell this model from a coin flip:
the bootstrap CI on that slice's AUC spans 0.470-0.637. Worse, it is *one* slice
- per-block AUC ranges from 0.53 to 0.80 across the corpus, so which fortnight
the cut lands on moves the headline number more than any modelling change does.

This walks the cut point across the snapshot instead, trains a fresh model at
each cut (vocab frozen from that cut's train block, as in ml.split), predicts
the block immediately after it, and pools every block's predictions into one
scored set. Same corpus, ~2.4x the evaluation data, and no single fortnight can
dominate. Baselines (coin flip, openskill) are scored on exactly the pooled
games so the comparison is paired.

Each cut trains ``--seeds`` models; both the mean single-model score and the
seed-bagged ensemble are reported, since production serves an ensemble.

Usage::

    uv run --group ml --python 3.13 python -m ml.rolling_eval \\
        ml/data/snapshot-YYYYMMDD.jsonl.gz [--seeds 3] [--no-recency]

Writes ``ml/data/rolling-<stamp>/results.json`` plus each cut's split and run
bundles (git-ignored, safe to delete).
"""

from __future__ import annotations

import argparse
import dataclasses
import gzip
import json
import statistics
from dataclasses import asdict
from pathlib import Path

import structlog
import torch

from radarvan.api_types import MatchInfo

from .config import DATA_DIR, Config
from .features import Vocab, build_vocab
from .model import OutcomeLitModule
from .predict import Metrics, model_probs, openskill_probs, score
from .snapshot import load_snapshot
from .train import train

logger = structlog.get_logger(__name__)

# Where the cut points sit, as fractions of the (time-ordered) corpus. The first
# is late enough that the train block is a usable model, the last leaves a full
# block after it. Each block is BLOCK_FRAC of the corpus, taken immediately after
# its cut - blocks do not overlap at these spacings.
DEFAULT_CUTS = (0.55, 0.65, 0.75, 0.85, 0.93)
DEFAULT_BLOCK_FRAC = 0.07


def _write_jsonl_gz(matches: list[MatchInfo], path: Path) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        for m in matches:
            fh.write(m.model_dump_json())
            fh.write("\n")


def _load_module(run_dir: Path, cfg: Config) -> tuple[OutcomeLitModule, Vocab]:
    """Best checkpoint on CPU with its fitted temperature applied."""
    vocab = Vocab.load(run_dir / "vocab.json")
    module = OutcomeLitModule(vocab, cfg)
    ckpt = torch.load(run_dir / "best.ckpt", map_location="cpu", weights_only=False)
    module.load_state_dict(ckpt["state_dict"])
    calib = run_dir / "calibration.json"
    if calib.exists():
        module.model.temperature = torch.tensor(
            [float(json.loads(calib.read_text())["temperature"])]
        )
    module.eval()
    return module, vocab


def rolling_eval(
    snapshot: Path,
    out_dir: Path,
    cfg: Config,
    cuts: tuple[float, ...] = DEFAULT_CUTS,
    block_frac: float = DEFAULT_BLOCK_FRAC,
    seeds: tuple[int, ...] = (11, 22, 33),
    accelerator: str = "auto",
) -> dict[str, object]:
    matches = sorted(load_snapshot(snapshot), key=lambda m: m.timestamp)
    n = len(matches)
    stamp = snapshot.name.split(".")[0].replace("snapshot-", "")
    map_feat_path = snapshot.parent / f"map_features-{stamp}.json"
    map_feat = (
        json.loads(map_feat_path.read_text()) if map_feat_path.exists() else None
    )

    # Pooled predictions, one list per seed plus the shared labels/baselines.
    per_seed: dict[int, list[float]] = {s: [] for s in seeds}
    labels: list[int] = []
    os_probs: list[float] = []
    os_labels: list[int] = []
    per_cut: list[dict[str, object]] = []

    for cut_frac in cuts:
        cut = int(n * cut_frac)
        end = min(n, cut + int(n * block_frac))
        train_block, test_block = matches[:cut], matches[cut:end]
        if len(test_block) < 10:
            logger.warning("skipping cut, block too small", cut=cut_frac)
            continue

        cut_dir = out_dir / f"cut{int(cut_frac * 100):03d}"
        cut_dir.mkdir(parents=True, exist_ok=True)
        _write_jsonl_gz(train_block, cut_dir / "train.jsonl.gz")
        _write_jsonl_gz(test_block, cut_dir / "dev.jsonl.gz")
        build_vocab(train_block, map_feat).save(cut_dir / "vocab.json")

        block_labels: list[int] | None = None
        cut_aucs: list[float] = []
        for seed in seeds:
            seed_cfg = Config(
                model=cfg.model, train=dataclasses.replace(cfg.train, seed=seed)
            )
            run_dir = train(cut_dir, seed_cfg, accelerator=accelerator)
            module, vocab = _load_module(run_dir, seed_cfg)
            probs, block_lab = model_probs(module, vocab, test_block)
            per_seed[seed].extend(probs)
            if block_labels is None:
                block_labels = block_lab
            cut_aucs.append(score("m", probs, block_lab).auc)

        if block_labels is None:  # no seeds ran; nothing to pool for this cut
            continue
        labels.extend(block_labels)
        # openskill, fit on the same train block only. Pooled with its own labels:
        # it can drop a game the model kept (or vice versa), and padding to match
        # would invent predictions rather than report the baseline.
        cut_os, cut_os_lab = openskill_probs(train_block, test_block)
        os_probs.extend(cut_os)
        os_labels.extend(cut_os_lab)
        per_cut.append({
            "cut": cut_frac,
            "n_train": len(train_block),
            "n_test": len(test_block),
            "auc_mean": statistics.mean(cut_aucs),
            "auc_min": min(cut_aucs),
            "auc_max": max(cut_aucs),
        })
        logger.info(
            "cut done", cut=cut_frac, n_train=len(train_block), n_test=len(test_block),
            auc=round(statistics.mean(cut_aucs), 3),
        )

    results: list[Metrics] = [
        score("coin_flip", [0.5] * len(labels), labels),
        score("openskill", os_probs, os_labels),
    ]
    singles = [score(f"seed_{s}", per_seed[s], labels) for s in seeds]
    bagged = [statistics.mean(per_seed[s][i] for s in seeds) for i in range(len(labels))]
    results.append(score("ml_bagged", bagged, labels))

    print(f"\n=== rolling-origin evaluation ({len(labels)} pooled test games, "
          f"{len(per_cut)} cuts x {len(seeds)} seeds) ===")
    for r in results[:2]:
        print(_fmt(r))
    print(
        f"{'ml_single (mean)':<22} n={len(labels):<5} "
        f"logloss={statistics.mean(s.log_loss for s in singles):.4f} "
        f"acc={statistics.mean(s.accuracy for s in singles):.3f} "
        f"auc={statistics.mean(s.auc for s in singles):.3f} "
        f"brier={statistics.mean(s.brier for s in singles):.4f}"
    )
    print(_fmt(results[-1]))
    print("\nper cut:")
    for c in per_cut:
        print(f"  cut {c['cut']:<5} train={c['n_train']:<5} test={c['n_test']:<4} "
              f"auc={c['auc_mean']:.3f} ({c['auc_min']:.3f}-{c['auc_max']:.3f})")

    payload: dict[str, object] = {
        "snapshot": snapshot.name,
        "cuts": list(cuts),
        "block_frac": block_frac,
        "seeds": list(seeds),
        "n_pooled": len(labels),
        "config": asdict(cfg),
        "metrics": {r.name: asdict(r) for r in [*results, *singles]},
        "per_cut": per_cut,
    }
    (out_dir / "results.json").write_text(json.dumps(payload, indent=2, default=str))
    return payload


def _fmt(m: Metrics) -> str:
    return (
        f"{m.name:<22} n={m.n:<5} logloss={m.log_loss:.4f} "
        f"acc={m.accuracy:.3f} auc={m.auc:.3f} brier={m.brier:.4f}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument(
        "--cuts",
        type=str,
        default=",".join(str(c) for c in DEFAULT_CUTS),
        help="Comma-separated corpus fractions to cut at.",
    )
    parser.add_argument("--block-frac", type=float, default=DEFAULT_BLOCK_FRAC)
    parser.add_argument("--recency-half-life", type=float, default=None)
    parser.add_argument(
        "--no-recency", action="store_true", help="Weight every training game equally."
    )
    parser.add_argument("--accelerator", choices=("auto", "cpu", "gpu"), default="auto")
    args = parser.parse_args()

    cfg = Config()
    if args.no_recency:
        cfg.train.recency_half_life_days = None
    elif args.recency_half_life is not None:
        cfg.train.recency_half_life_days = args.recency_half_life

    stamp = args.snapshot.name.split(".")[0].replace("snapshot-", "")
    out_dir = args.out_dir or (DATA_DIR / f"rolling-{stamp}")
    out_dir.mkdir(parents=True, exist_ok=True)

    rolling_eval(
        args.snapshot,
        out_dir,
        cfg,
        cuts=tuple(float(c) for c in args.cuts.split(",")),
        block_frac=args.block_frac,
        seeds=tuple(11 * (i + 1) for i in range(args.seeds)),
        accelerator=args.accelerator,
    )


if __name__ == "__main__":
    main()
