"""Error bars on the UNK/UNK faction matrix via a bootstrap + reseed ensemble.

Given how little data there is (~1000 train matches), a single trained model's
matrix cell values shouldn't be read as precise. This resamples the *training
set* with replacement (bootstrap - estimates data uncertainty) and reseeds the
optimizer each time (estimates optimization-noise on top), retraining and
re-exporting K times, then re-derives the 144-cell matrix from each. Training
is cheap here (~10-20s/run on GPU) so K in the 30-50 range is a few minutes,
not an overnight job.

vocab.json is held fixed across replicates (copied from the source split, not
resampled) so every replicate's matrix cells line up on the same general/player
indices. Each replicate holds out the same recent tail of train for early
stopping and the temperature fit, and resamples only the games before it -
dev.jsonl.gz is never read during training.

Usage::

    uv run --group ml --python 3.13 python -m ml.bootstrap_matrix \\
        ml/data/split-YYYYMMDD-temporal/ [--k 30] [--base-seed 1234] [--promote]

Writes ``<split_dir>/bootstrap/results.json``: per-cell mean/std/percentiles
plus the raw KxN_cells array, and prints a summary of which cells' 90% CI
excludes 0.5 (i.e. look real) vs. which don't (indistinguishable from noise
given this much data). Each replicate's split/run/model files are kept under
``<split_dir>/bootstrap/boot-NNN/`` for inspection - safe to delete once
you're happy with the result and have promoted (everything here is
reproducible by rerunning this script against the same split).

``--promote`` copies the K replicate ``model.onnx`` files + the shared
``vocab.json`` into ``ml_ensemble/`` at the repo root (override with
``--ensemble-dir``) - the directory ``radarvan/ml_inference.py`` actually
serves from (``ML_ENSEMBLE_DIR``). This is the one step that changes what's
live; everything else here only writes under ``ml/data/`` (git-ignored).
Without ``--promote``, review ``results.json`` first, then rerun with
``--k 0 --promote`` to promote the replicates already on disk without
retraining (``--k 30 --promote`` in one go retrains a *fresh* set of K
replicates before promoting - fine, just redundant if you already have one
you're happy with).

Must run under the ml-training environment (torch); dump_matrix_worker.py (the
per-replicate inference step) is shelled out to ``uv run python`` instead,
which uses the main app's normal (torch-free) environment - the same one that
actually serves predictions in production.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import random
import shutil
import statistics
import subprocess
from pathlib import Path

import structlog

from radarvan.api_types import General, MatchInfo

from .config import Config
from .export import export
from .snapshot import load_snapshot
from .train import train

logger = structlog.get_logger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENSEMBLE_DIR = REPO_ROOT / "ml_ensemble"


def _write_jsonl_gz(matches: list[MatchInfo], path: Path) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        for m in matches:
            fh.write(m.model_dump_json())
            fh.write("\n")


def _bootstrap_replicate(
    split_dir: Path, boot_dir: Path, train_matches: list[MatchInfo], seed: int
) -> Path:
    """One replicate: resample the fit games, keep the validation tail intact.

    Only the *fit* portion is resampled. The recent tail that early stopping and
    the temperature fit use is held out first and appended unchanged, so it stays
    time-ordered, free of bootstrap duplicates, and disjoint from what the
    weights see - none of which survives resampling the whole block and then
    taking its last 15%.
    """
    cfg = Config()
    cfg.train.seed = seed

    ordered = sorted(train_matches, key=lambda m: m.timestamp)
    n_val = int(len(ordered) * cfg.train.val_frac)
    fit, val = (ordered[: len(ordered) - n_val], ordered[len(ordered) - n_val :])

    rng = random.Random(seed)  # noqa: S311 - resampling data, not crypto
    resampled = sorted(
        (rng.choice(fit) for _ in range(len(fit))), key=lambda m: m.timestamp
    )
    written = [*resampled, *val]
    boot_dir.mkdir(parents=True, exist_ok=True)
    _write_jsonl_gz(written, boot_dir / "train.jsonl.gz")
    # dev is copied only because MatchDataModule expects the file; with
    # val_frac > 0 nothing in training reads it.
    (boot_dir / "dev.jsonl.gz").write_bytes((split_dir / "dev.jsonl.gz").read_bytes())
    (boot_dir / "vocab.json").write_bytes((split_dir / "vocab.json").read_bytes())

    # Re-point val_frac at exactly the games we appended, whatever the resample
    # did to the fit block's length.
    cfg.train.val_frac = len(val) / len(written) if written else 0.0
    run_dir = train(boot_dir, cfg, accelerator="auto")
    export(run_dir)
    return run_dir


def _dump_matrix(run_dir: Path) -> list[dict[str, float]]:
    out_path = run_dir / "matrix.json"
    cmd = [
        "uv",
        "run",
        "python",
        "-m",
        "ml.dump_matrix_worker",
        str(run_dir / "model.onnx"),
        str(run_dir / "vocab.json"),
        str(out_path),
    ]
    subprocess.run(  # noqa: S603 - fixed internal command, not untrusted input
        cmd,
        cwd=REPO_ROOT,
        env=os.environ,
        check=True,
        capture_output=True,
    )
    result: list[dict[str, float]] = json.loads(out_path.read_text())
    return result


def run_bootstrap(split_dir: Path, k: int, base_seed: int) -> dict:
    train_matches = load_snapshot(split_dir / "train.jsonl.gz")
    out_dir = split_dir / "bootstrap"
    out_dir.mkdir(parents=True, exist_ok=True)

    generals = [g for g in General if g.value >= 0]
    per_cell: dict[tuple[int, int], list[float]] = {
        (ga.value, gb.value): [] for ga in generals for gb in generals
    }

    for i in range(k):
        seed = base_seed + i
        boot_dir = out_dir / f"boot-{i:03d}"
        logger.info("replicate", i=i + 1, k=k, seed=seed)
        run_dir = _bootstrap_replicate(split_dir, boot_dir, train_matches, seed)
        cells = _dump_matrix(run_dir)
        for c in cells:
            per_cell[(int(c["general_a"]), int(c["general_b"]))].append(
                c["prob_a_wins"]
            )

    cell_stats = []
    for ga in generals:
        for gb in generals:
            vals = sorted(per_cell[(ga.value, gb.value)])
            n = len(vals)
            lo = vals[max(0, int(n * 0.05))]
            hi = vals[min(n - 1, int(n * 0.95))]
            cell_stats.append(
                {
                    "general_a": ga.value,
                    "general_b": gb.value,
                    "mean": statistics.mean(vals),
                    "std": statistics.stdev(vals) if n > 1 else 0.0,
                    "p05": lo,
                    "p95": hi,
                    "significant": lo > 0.5 or hi < 0.5,
                    "values": vals,
                }
            )

    result = {
        "split_dir": str(split_dir),
        "k": k,
        "base_seed": base_seed,
        "cells": cell_stats,
    }
    (out_dir / "results.json").write_text(json.dumps(result, indent=2))

    sig = [c for c in cell_stats if c["significant"]]
    logger.info("bootstrap done", n_significant=len(sig), n_cells=len(cell_stats))
    for c in sorted(sig, key=lambda c: -abs(c["mean"] - 0.5)):
        logger.info(
            "significant cell",
            general_a=General(c["general_a"]).name,
            general_b=General(c["general_b"]).name,
            mean=round(c["mean"], 3),
            p05=round(c["p05"], 3),
            p95=round(c["p95"], 3),
            std=round(c["std"], 3),
        )
    return result


def promote_ensemble(split_dir: Path, ensemble_dir: Path = DEFAULT_ENSEMBLE_DIR) -> int:
    """Copy every replicate's ``model.onnx`` + the shared ``vocab.json`` into
    ``ensemble_dir`` - the directory ``radarvan/ml_inference.py`` actually
    serves from. Replaces whatever was there before (stale ``model-*.onnx``
    from a smaller/older ensemble are removed first) so ``ensemble_dir``
    always reflects exactly this split's replicates, not a mix of two runs.

    **One model per replicate: the newest run.** Re-running ``--k N`` against a
    split that already has a ``bootstrap/`` rewrites each ``boot-NNN``'s data but
    ``train()`` writes a *new* timestamped run dir beside the old one, so a
    replicate that has been retrained holds several. Taking them all shipped a
    2N-model ensemble, half of it trained under the previous config - which is
    silent, because the count is the only visible symptom. Run dirs are
    ``%Y%m%d-%H%M%S``, so the last by name is the newest.
    """
    boot_dirs = sorted((split_dir / "bootstrap").glob("boot-*"))
    model_paths = []
    stale = 0
    for boot_dir in boot_dirs:
        runs = sorted(boot_dir.glob("runs/*/model.onnx"), key=lambda p: p.parent.name)
        if runs:
            model_paths.append(runs[-1])
            stale += len(runs) - 1
    if stale:
        logger.warning(
            "ignoring older run bundles; promoting the newest per replicate",
            n_ignored=stale,
            n_replicates=len(model_paths),
        )
    if not model_paths:
        raise SystemExit(
            f"no replicate models found under {split_dir / 'bootstrap'} "
            "- run without --promote (or with --k > 0) first"
        )

    ensemble_dir.mkdir(parents=True, exist_ok=True)
    for stale in ensemble_dir.glob("model-*.onnx"):
        stale.unlink()
    for i, model_path in enumerate(model_paths):
        shutil.copy(model_path, ensemble_dir / f"model-{i:03d}.onnx")
    shutil.copy(split_dir / "vocab.json", ensemble_dir / "vocab.json")

    logger.info(
        "promoted ensemble", ensemble_dir=str(ensemble_dir), n_models=len(model_paths)
    )
    return len(model_paths)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("split_dir", type=Path)
    parser.add_argument("--k", type=int, default=30)
    parser.add_argument("--base-seed", type=int, default=1234)
    parser.add_argument(
        "--promote",
        action="store_true",
        help="After training, copy the replicate models into --ensemble-dir "
        "(what the app actually serves).",
    )
    parser.add_argument("--ensemble-dir", type=Path, default=DEFAULT_ENSEMBLE_DIR)
    args = parser.parse_args()
    if args.k > 0:
        run_bootstrap(args.split_dir, args.k, args.base_seed)
    if args.promote:
        promote_ensemble(args.split_dir, args.ensemble_dir)


if __name__ == "__main__":
    main()
