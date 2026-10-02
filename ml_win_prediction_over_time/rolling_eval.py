"""Rolling-origin evaluation for the win-probability curve, and paired comparisons.

A single temporal split leaves ~180 games to score, and which fortnight the cut
lands on moves the number more than most modelling changes do. This walks the
cut across the snapshot (same cuts as ``ml.rolling_eval``), trains a seed bag at
each, scores the block after it, and pools every block. The baselines are scored
on exactly the same windows, and every prediction is saved so two runs - e.g. a
feature group dropped - can be compared match-paired afterwards.

Usage::

    .venv-ml/bin/python -m ml_win_prediction_over_time.rolling_eval run \\
        data/snapshot-YYYYMMDD.jsonl.gz --name full [--drop income alive] \\
        [--late-weight 3] [--seeds 11 22 33]
    .venv-ml/bin/python -m ml_win_prediction_over_time.rolling_eval compare \\
        data/rolling-full:gru data/rolling-no-income:gru

Writes ``data/rolling-<name>/{results.json,predictions.json.gz}`` plus each
cut's split and runs (git-ignored).
"""

from __future__ import annotations

import argparse
import dataclasses
import gzip
import json
from dataclasses import asdict
from pathlib import Path
from typing import NamedTuple

import numpy as np
import structlog
from sklearn.metrics import roc_auc_score

from radarvan.logging_config import configure_logging

from .baselines import (
    coin_flip_probs,
    gbdt_probs,
    prior_only_probs,
    static_logistic_probs,
)
from .config import BUCKET_SECONDS, DATA_DIR, Config
from .dataset import encode_all
from .features import FeatureStats
from .predict import PHASES, in_phase, load_run, log_loss_terms, model_curves
from .snapshot import load_snapshot
from .split import write_split
from .train import train

logger = structlog.get_logger(__name__)

DEFAULT_CUTS = (0.55, 0.65, 0.75, 0.85, 0.93)
DEFAULT_BLOCK_FRAC = 0.07

# Absolute-minute windows: the opening is where the bar is interesting and the
# prior matters, and a phase-of-match fraction mixes a 6- and a 40-minute game.
MINUTE_BINS = ((0, 2), (2, 4), (4, 8), (8, 15), (15, 25), (25, 999))

# {predictor: {match_id: [p per window]}}
Preds = dict[str, dict[int, list[float]]]


def _minutes(n: int) -> np.ndarray:
    return np.arange(1, n + 1) * BUCKET_SECONDS / 60


def score(curves: dict[int, list[float]], labels: dict[int, int]) -> dict[str, object]:
    ids = sorted(labels)
    per_match = [np.asarray(curves[m], float) for m in ids]
    p = np.concatenate(per_match)
    y = np.concatenate(
        [np.full(len(c), float(labels[m])) for c, m in zip(per_match, ids, strict=True)]
    )
    minute = np.concatenate([_minutes(len(c)) for c in per_match])
    phase = np.concatenate([np.arange(1, len(c) + 1) / len(c) for c in per_match])
    ll = log_loss_terms(p, y)
    per_game = np.add.reduceat(ll, np.cumsum([0] + [len(c) for c in per_match[:-1]]))
    by_minute = {}
    for lo, hi in MINUTE_BINS:
        sel = (minute > lo) & (minute <= hi)
        if sel.any():
            by_minute[f"{lo}-{hi}m"] = float(ll[sel].mean())
    return {
        "log_loss": float(ll.mean()),
        "per_game_log_loss": float((per_game / [len(c) for c in per_match]).mean()),
        "auc": float(roc_auc_score(y, p)),
        "brier": float(((p - y) ** 2).mean()),
        "by_minute": by_minute,
        "by_phase": {
            name: float(ll[in_phase(phase, lo, hi)].mean()) for lo, hi, name in PHASES
        },
    }


def rolling_eval(
    snapshot: Path,
    out_dir: Path,
    cfg: Config,
    drop: frozenset[str] = frozenset(),
    seeds: tuple[int, ...] = (11, 22, 33),
    cuts: tuple[float, ...] = DEFAULT_CUTS,
    block_frac: float = DEFAULT_BLOCK_FRAC,
    accelerator: str = "auto",
    oof_prior: bool = True,
) -> dict[str, object]:
    records = load_snapshot(snapshot)
    n = len(records)
    preds: Preds = {}
    labels: dict[int, int] = {}

    def add(name: str, ids: list[int], curves: list[np.ndarray]) -> None:
        preds.setdefault(name, {}).update(
            {
                m: [round(float(v), 5) for v in c]
                for m, c in zip(ids, curves, strict=True)
            }
        )

    for cut_frac in cuts:
        cut = int(n * cut_frac)
        end = min(n, cut + int(n * block_frac))
        if end - cut < 10:
            continue
        cut_dir = out_dir / f"cut{int(cut_frac * 100):03d}"
        write_split(
            records[:cut], records[cut:end], cut_dir, drop, {"cut": cut_frac}, oof_prior
        )

        stats = FeatureStats.load(cut_dir / "feature_stats.json")
        dev = encode_all(cut_dir / "dev.jsonl.gz")
        train_seqs = encode_all(cut_dir / "train.jsonl.gz")
        ids = [s.match_id for s in dev]

        seed_curves = []
        for seed in seeds:
            seed_cfg = Config(
                model=cfg.model, train=dataclasses.replace(cfg.train, seed=seed)
            )
            run = load_run(train(cut_dir, seed_cfg, accelerator=accelerator))
            curves = model_curves(run.module, stats, dev, run.temperature)
            seed_curves.append(curves)
            add(f"gru_seed{seed}", ids, curves)
        gru = [np.mean(cs, axis=0) for cs in zip(*seed_curves, strict=True)]
        add("gru", ids, gru)

        gbdt = gbdt_probs(train_seqs, dev, stats)
        add("coin_flip", ids, coin_flip_probs(dev))
        add("prior_only", ids, prior_only_probs(dev))
        add("static_logistic", ids, static_logistic_probs(train_seqs, dev, stats))
        add("gbdt", ids, gbdt)
        # What winprob_inference serves.
        add("blend", ids, [(g + b) / 2 for g, b in zip(gru, gbdt, strict=True)])
        labels.update({s.match_id: s.label for s in dev})
        logger.info("cut done", cut=cut_frac, n_train=cut, n_test=len(dev))

    metrics = {name: score(curves, labels) for name, curves in preds.items()}
    _print_table(metrics, len(labels))
    out_dir.mkdir(parents=True, exist_ok=True)
    with gzip.open(out_dir / "predictions.json.gz", "wt") as fh:
        json.dump({"labels": labels, "preds": preds}, fh)
    payload = {
        "snapshot": snapshot.name,
        "dropped_groups": sorted(drop),
        "oof_prior": oof_prior,
        "cuts": list(cuts),
        "block_frac": block_frac,
        "seeds": list(seeds),
        "n_matches": len(labels),
        "config": asdict(cfg),
        "metrics": metrics,
    }
    (out_dir / "results.json").write_text(json.dumps(payload, indent=2, default=str))
    return payload


def _print_table(metrics: dict[str, dict], n: int) -> None:
    bins = list(next(iter(metrics.values()))["by_minute"])
    print(f"\n=== rolling-origin evaluation ({n} matches) ===")
    print(
        f"{'':<18}{'logloss':>9}{'per-game':>9}{'auc':>7}  "
        + "".join(f"{b:>8}" for b in bins)
    )
    for name, m in metrics.items():
        if name.startswith("gru_seed"):
            continue
        print(
            f"{name:<18}{m['log_loss']:>9.4f}{m['per_game_log_loss']:>9.4f}"
            f"{m['auc']:>7.3f}  "
            + "".join(f"{m['by_minute'].get(b, float('nan')):>8.3f}" for b in bins)
        )


class _Saved(NamedTuple):
    name: str
    curves: dict[int, list[float]]
    labels: dict[int, int]


def _load(spec: str) -> _Saved:
    path, _, name = spec.partition(":")
    with gzip.open(Path(path) / "predictions.json.gz", "rt") as fh:
        d = json.load(fh)
    labels = {int(k): v for k, v in d["labels"].items()}
    return _Saved(
        spec, {int(k): v for k, v in d["preds"][name or "gru"].items()}, labels
    )


def compare(spec_a: str, spec_b: str, n_boot: int = 2000, seed: int = 0) -> None:
    """Paired bootstrap over matches of A minus B (negative = A better)."""
    name_a, a, labels = _load(spec_a)
    name_b, b, labels_b = _load(spec_b)
    ids = sorted(set(a) & set(b) & set(labels))
    if any(labels[m] != labels_b[m] for m in ids):
        raise SystemExit("the two runs disagree on labels; different snapshots?")
    windows = {
        "whole match": (0, 999),
        **{f"{lo}-{hi}m": (lo, hi) for lo, hi in MINUTE_BINS},
    }
    # Per match, per window: (sum of A's loss, sum of B's loss, count).
    sums = np.zeros((len(ids), len(windows), 3))
    for i, m in enumerate(ids):
        pa, pb = np.asarray(a[m], float), np.asarray(b[m], float)
        minute = _minutes(len(pa))
        la = log_loss_terms(pa, float(labels[m]))
        lb = log_loss_terms(pb, float(labels[m]))
        for j, (lo, hi) in enumerate(windows.values()):
            sel = (minute > lo) & (minute <= hi)
            sums[i, j] = la[sel].sum(), lb[sel].sum(), sel.sum()
    rng = np.random.default_rng(seed)
    boot = sums[rng.integers(0, len(ids), size=(n_boot, len(ids)))].sum(axis=1)
    diffs = (boot[..., 0] - boot[..., 1]) / np.maximum(boot[..., 2], 1)
    total = sums.sum(axis=0)
    print(f"\n{name_a}  minus  {name_b}   ({len(ids)} paired matches)")
    print(f"{'window':<14}{'A':>8}{'B':>8}{'diff':>9}{'95% CI':>22}{'P(A better)':>13}")
    for j, w in enumerate(windows):
        la, lb, c = total[j]
        lo, hi = np.percentile(diffs[:, j], [2.5, 97.5])
        print(
            f"{w:<14}{la / c:>8.4f}{lb / c:>8.4f}{(la - lb) / c:>+9.4f}"
            f"{f'[{lo:+.4f}, {hi:+.4f}]':>22}{(diffs[:, j] < 0).mean():>13.2f}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run")
    run.add_argument("snapshot", type=Path)
    run.add_argument("--name", required=True)
    run.add_argument("--drop", nargs="*", default=[])
    run.add_argument("--seeds", nargs="*", type=int, default=[11, 22, 33])
    run.add_argument("--late-weight", type=float, default=None)
    run.add_argument("--hidden", type=int, default=None)
    run.add_argument(
        "--in-sample-prior",
        action="store_true",
        help="the old leaky prior, to measure it",
    )
    run.add_argument("--accelerator", choices=("auto", "cpu", "gpu"), default="auto")
    cmp_ = sub.add_parser("compare")
    cmp_.add_argument("a", help="rolling dir[:predictor], predictor defaults to gru")
    cmp_.add_argument("b")
    args = parser.parse_args()

    configure_logging(dev=True)
    if args.cmd == "compare":
        compare(args.a, args.b)
        return
    cfg = Config()
    if args.late_weight is not None:
        cfg.train.late_weight = args.late_weight
    if args.hidden is not None:
        cfg.model.hidden = args.hidden
    rolling_eval(
        args.snapshot,
        DATA_DIR / f"rolling-{args.name}",
        cfg,
        drop=frozenset(args.drop),
        seeds=tuple(args.seeds),
        accelerator=args.accelerator,
        oof_prior=not args.in_sample_prior,
    )


if __name__ == "__main__":
    main()
