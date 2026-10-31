"""Old-vs-new comparison of every served model after a retrain (torch-free).

Usage::

    uv run python -m ml.retrain_report --old ml/data/retrain-<date>/old \\
        --pregame-split ml/data/split-<date>-temporal \\
        --winprob-snapshot ml_win_prediction_over_time/data/snapshot-<date>.jsonl.gz \\
        [--prev-pregame-split ...] [--prev-winprob-snapshot ...] --out ml/data/retrain-<date>
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from radarvan.api_types import General

from .baselines import bt_logistic_probs, score
from .features import Vocab, encode_match
from .snapshot import load_snapshot

REPO_ROOT = Path(__file__).resolve().parent.parent
ENSEMBLE = "ml_ensemble"
SCENARIO = "ml_scenario/scenario_model.json"
WINPROB = "ml_winprob_bundle"
GENERAL_NAMES = [General(i).name for i in range(12)]


def _ensemble_dev_probs(ensemble_dir: Path, dev: Path) -> list[float]:
    # ml_inference binds ML_ENSEMBLE_DIR at import, so each ensemble scores in its own process.
    out = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "ml.retrain_report", "--score-ensemble", str(dev)],
        env={**os.environ, "ML_ENSEMBLE_DIR": str(ensemble_dir)},
        capture_output=True,
        text=True,
        check=True,
        cwd=REPO_ROOT,
    )
    return json.loads(out.stdout.strip().splitlines()[-1])


def _score_ensemble(dev: Path) -> None:
    from radarvan import ml_inference

    probs = [
        ml_inference.predict_match_info(m).prob_team_a_wins
        for m in load_snapshot(dev)
        if encode_match(m, ml_inference._vocab()) is not None
    ]
    print(json.dumps(probs))  # noqa: T201


def _vocab_diff(old: Path, new: Path) -> dict[str, dict[str, list[str]]]:
    o, n = json.loads(old.read_text()), json.loads(new.read_text())
    return {
        k: {
            "added": sorted(set(n[k]) - set(o.get(k, {}))),
            "removed": sorted(set(o.get(k, {})) - set(n[k])),
        }
        for k in n
        if isinstance(n[k], dict) and set(n[k]) != set(o.get(k, {}))
    }


def pregame(old_root: Path, split: Path, prev_split: Path | None) -> dict[str, Any]:
    dev_path = split / "dev.jsonl.gz"
    dev, train = load_snapshot(dev_path), load_snapshot(split / "train.jsonl.gz")
    vocab = Vocab.load(REPO_ROOT / ENSEMBLE / "vocab.json")
    labels = [e.label for m in dev if (e := encode_match(m, vocab)) is not None]
    old_dir = old_root / ENSEMBLE
    scores = {
        "old_ensemble": score(
            "old_ensemble", _ensemble_dev_probs(old_dir, dev_path), labels
        ),
        "new_ensemble": score(
            "new_ensemble", _ensemble_dev_probs(REPO_ROOT / ENSEMBLE, dev_path), labels
        ),
        "bt_logistic": score("bt_logistic", *bt_logistic_probs(train, dev)),
    }
    split_meta = json.loads((split / "split.json").read_text())
    report: dict[str, Any] = {
        "n_train": split_meta["n_train"],
        "n_dev": split_meta["n_dev"],
        "dev_scores": {k: asdict(v) for k, v in scores.items()},
        "vocab_changes": _vocab_diff(
            old_dir / "vocab.json", REPO_ROOT / ENSEMBLE / "vocab.json"
        ),
        "n_significant_cells": _n_significant(split / "bootstrap" / "results.json"),
    }
    if prev_split is not None:
        prev_train = {m.id for m in load_snapshot(prev_split / "train.jsonl.gz")}
        # Non-zero means the old ensemble saw some dev games, so its dev score flatters it.
        report["old_ensemble_trained_on_dev"] = len(prev_train & {m.id for m in dev})
        report["n_train_prev"] = len(prev_train)
        report["n_significant_cells_prev"] = _n_significant(
            prev_split / "bootstrap" / "results.json"
        )
    return report


def _n_significant(results: Path) -> int | None:
    if not results.exists():
        return None
    return sum(
        1 for c in json.loads(results.read_text())["cells"] if c.get("significant")
    )


def scenario(old_path: Path, new_path: Path) -> dict[str, Any]:
    o, n = json.loads(old_path.read_text()), json.loads(new_path.read_text())
    tables = {}
    for k in ("main", "synergy", "counter", "map_slope"):
        a, b = np.asarray(o["point"][k]), np.asarray(n["point"][k])
        tables[k] = {
            "max_abs_old": float(np.abs(a).max()),
            "max_abs_new": float(np.abs(b).max()),
            "max_abs_diff": float(np.abs(a - b).max()),
        }
    return {
        "n_games": [o["n_games"], n["n_games"]],
        "date_max": [o["date_max"], n["date_max"]],
        "half_life_days": [o["half_life_days"], n["half_life_days"]],
        "penalty_changes": {
            k: [o["penalties"].get(k), v]
            for k, v in n["penalties"].items()
            if o["penalties"].get(k) != v
        },
        "evaluation": {
            proto: {
                variant: {
                    "old": o["evaluation"][proto][variant],
                    "new": n["evaluation"][proto][variant],
                }
                for variant in n["evaluation"][proto]
            }
            for proto in n["evaluation"]
        },
        "tables": tables,
        "general_main": {
            GENERAL_NAMES[i]: [o["point"]["main"][i], n["point"]["main"][i]]
            for i in range(len(GENERAL_NAMES))
        },
        "top_pair_shifts": {
            k: _top_pair_shifts(o["point"][k], n["point"][k])
            for k in ("synergy", "counter")
        },
    }


def _top_pair_shifts(
    old: list[list[float]], new: list[list[float]], k: int = 5
) -> list[dict[str, Any]]:
    a, b = np.asarray(old), np.asarray(new)
    pairs = [
        (i, j)
        for i in range(len(a))
        for j in range(i + 1, len(a))
        if a[i, j] != b[i, j]
    ]
    pairs.sort(key=lambda p: -abs(a[p] - b[p]))
    return [
        {
            "pair": f"{GENERAL_NAMES[i]}/{GENERAL_NAMES[j]}",
            "old": float(a[i, j]),
            "new": float(b[i, j]),
        }
        for i, j in pairs[:k]
    ]


def winprob(
    old_dir: Path, snapshot: Path, prev_snapshot: Path | None
) -> dict[str, Any]:
    from ml_win_prediction_over_time.features import (
        FeatureStats,
        match_to_sequence,
        with_deltas,
    )
    from ml_win_prediction_over_time.pregame import PregamePrior
    from ml_win_prediction_over_time.snapshot import load_snapshot as load_records
    from radarvan.ml_inference import cpu_session
    from radarvan.winprob_inference import GBDT_OUTPUT

    def bundle(d: Path) -> Any:
        gru = cpu_session(d / "ml_winprob_over_time.onnx")
        gbdt = cpu_session(d / "ml_winprob_over_time_gbdt.onnx")
        stats = FeatureStats.load(d / "ml_winprob_over_time_stats.json")
        prior = PregamePrior.load(d / "ml_winprob_over_time_prior.json")

        def curve(rec: dict[str, Any]) -> np.ndarray | None:
            seq = match_to_sequence(
                rec,
                prior_logit=prior.logit(rec["team_a_players"], rec["team_b_players"]),
            )
            if seq is None:
                return None
            x = stats.apply(seq.x)
            gru_p = gru.run(["prob_team_a"], {"x": x[None]})[0][0]
            return (gru_p + gbdt.run([GBDT_OUTPUT], {"x": with_deltas(x)})[0][:, 1]) / 2

        return curve

    old, new = bundle(old_dir / WINPROB), bundle(REPO_ROOT / WINPROB)
    prev_ids = (
        {int(r["match_id"]) for r in load_records(prev_snapshot)}
        if prev_snapshot
        else set()
    )
    diffs, first, unseen = [], [], []
    for rec in load_records(snapshot):
        a, b = old(rec), new(rec)
        if a is None or b is None:
            continue
        diffs.append(np.abs(a - b))
        first.append(abs(a[0] - b[0]))
        if prev_snapshot and int(rec["match_id"]) not in prev_ids:
            y, p = int(rec["label_a_win"]), np.clip(a, 1e-6, 1 - 1e-6)
            unseen.append(float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean()))
    d = np.concatenate(diffs)
    report: dict[str, Any] = {
        "n_matches": len(diffs),
        "mean_abs_shift": float(d.mean()),
        "p95_abs_shift": float(np.quantile(d, 0.95)),
        "max_abs_shift": float(d.max()),
        "first_window_mean_abs_shift": float(np.mean(first)),
    }
    if prev_snapshot:
        report["new_matches"] = len(unseen)
        # The new bundle trains on everything (dev-frac 0); only the old one has a holdout here.
        report["old_bundle_logloss_on_new_matches"] = (
            float(np.mean(unseen)) if unseen else None
        )
    return report


def render(r: dict[str, Any]) -> str:
    lines = ["# Retrain report", ""]
    p = r["pregame"]
    lines += [
        "## Pre-game ensemble",
        f"train {p.get('n_train_prev', '?')} -> {p['n_train']}, dev {p['n_dev']}",
        "",
        "| model | log-loss | AUC | acc | brier |",
        "|---|---|---|---|---|",
        *(
            f"| {k} | {s['log_loss']:.4f} | {s['auc']:.3f} | {s['accuracy']:.3f} | {s['brier']:.4f} |"
            for k, s in p["dev_scores"].items()
        ),
        "",
        f"old ensemble trained on dev games: {p.get('old_ensemble_trained_on_dev', '?')}",
        f"significant matchup cells: {p.get('n_significant_cells_prev', '?')} -> {p['n_significant_cells']}",
        f"vocab changes: {json.dumps(p['vocab_changes']) if p['vocab_changes'] else 'none'}",
        "",
        "## Composition (scenario) model",
    ]
    s = r["scenario"]
    lines += [
        f"games {s['n_games'][0]} -> {s['n_games'][1]}, through {s['date_max'][1]}",
        f"penalty changes: {json.dumps(s['penalty_changes']) if s['penalty_changes'] else 'none'}",
        f"half-life: {s['half_life_days'][0]} -> {s['half_life_days'][1]}",
        "",
        "| protocol | variant | old log-loss | new log-loss |",
        "|---|---|---|---|",
        *(
            f"| {proto} | {v} | {e['old']['log_loss']:.4f} | {e['new']['log_loss']:.4f} |"
            for proto, variants in s["evaluation"].items()
            for v, e in variants.items()
            if "log_loss" in e["new"]
        ),
        "",
        "| table | max abs old | max abs new | max abs diff |",
        "|---|---|---|---|",
        *(
            f"| {k} | {t['max_abs_old']:.3f} | {t['max_abs_new']:.3f} | {t['max_abs_diff']:.3f} |"
            for k, t in s["tables"].items()
        ),
        "",
        "general main effects (old -> new): "
        + ", ".join(
            f"{g} {o:+.3f}->{n:+.3f}"
            for g, (o, n) in sorted(s["general_main"].items(), key=lambda x: -x[1][1])
        ),
        *(
            f"biggest {k} shifts: "
            + (
                ", ".join(
                    f"{c['pair']} {c['old']:+.3f}->{c['new']:+.3f}" for c in cells
                )
                or "none"
            )
            for k, cells in s["top_pair_shifts"].items()
        ),
        "",
        "## Win-probability bundle",
    ]
    w = r["winprob"]
    lines += [
        f"matches {w['n_matches']}, new since previous snapshot: {w.get('new_matches', '?')}",
        f"curve shift |dp|: mean {w['mean_abs_shift']:.4f}, p95 {w['p95_abs_shift']:.4f}, "
        f"max {w['max_abs_shift']:.4f}, first window {w['first_window_mean_abs_shift']:.4f}",
        f"old bundle log-loss on new matches (unseen by it): "
        f"{w.get('old_bundle_logloss_on_new_matches') or float('nan'):.4f}",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--score-ensemble", type=Path, help=argparse.SUPPRESS)
    parser.add_argument(
        "--old", type=Path, help="backup holding the pre-retrain artifact dirs"
    )
    parser.add_argument("--pregame-split", type=Path)
    parser.add_argument("--prev-pregame-split", type=Path)
    parser.add_argument("--winprob-snapshot", type=Path)
    parser.add_argument("--prev-winprob-snapshot", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.score_ensemble:
        _score_ensemble(args.score_ensemble)
        return
    if not (args.old and args.pregame_split and args.winprob_snapshot and args.out):
        parser.error(
            "--old, --pregame-split, --winprob-snapshot and --out are required"
        )

    report = {
        "pregame": pregame(args.old, args.pregame_split, args.prev_pregame_split),
        "scenario": scenario(args.old / SCENARIO, REPO_ROOT / SCENARIO),
        "winprob": winprob(args.old, args.winprob_snapshot, args.prev_winprob_snapshot),
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "report.json").write_text(json.dumps(report, indent=2))
    text = render(report)
    (args.out / "report.md").write_text(text)
    print(text)  # noqa: T201


if __name__ == "__main__":
    main()
