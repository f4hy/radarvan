"""Old-vs-new diffs in ml.retrain_report."""

import json
from pathlib import Path

from ml.retrain_report import REPO_ROOT, SCENARIO, _vocab_diff, render, scenario


def test_scenario_against_itself_reports_no_change() -> None:
    path = REPO_ROOT / SCENARIO
    r = scenario(path, path)
    assert r["penalty_changes"] == {}
    assert all(t["max_abs_diff"] == 0 for t in r["tables"].values())


def test_scenario_reports_a_penalty_change(tmp_path: Path) -> None:
    raw = json.loads((REPO_ROOT / SCENARIO).read_text())
    old = tmp_path / "old.json"
    old.write_text(
        json.dumps({**raw, "penalties": {**raw["penalties"], "counter": -1.0}})
    )
    assert scenario(old, REPO_ROOT / SCENARIO)["penalty_changes"] == {
        "counter": [-1.0, raw["penalties"]["counter"]]
    }


def test_vocab_diff_lists_real_additions_not_renumbering(tmp_path: Path) -> None:
    old, new = tmp_path / "old.json", tmp_path / "new.json"
    old.write_text(json.dumps({"map": {"a": 1, "c": 2}, "player": {"x": 1}}))
    new.write_text(json.dumps({"map": {"a": 1, "b": 2, "c": 3}, "player": {"x": 1}}))
    assert _vocab_diff(old, new) == {"map": {"added": ["b"], "removed": []}}


def test_render_handles_a_first_run_without_previous_data() -> None:
    path = REPO_ROOT / SCENARIO
    scores = {"log_loss": 0.69, "auc": 0.5, "accuracy": 0.5, "brier": 0.25}
    text = render(
        {
            "pregame": {
                "n_train": 10,
                "n_dev": 2,
                "dev_scores": {"new_ensemble": scores},
                "vocab_changes": {},
                "n_significant_cells": None,
            },
            "scenario": scenario(path, path),
            "winprob": {
                "n_matches": 3,
                "mean_abs_shift": 0.0,
                "p95_abs_shift": 0.0,
                "max_abs_shift": 0.0,
                "first_window_mean_abs_shift": 0.0,
            },
        }
    )
    assert "vocab changes: none" in text
