"""The mid-game model must not early-stop on the set it is scored against.

Same invariant as ``tests/test_ml_validation_split.py``, same reason: with
``val_frac = 0`` this trainer watched ``dev.jsonl.gz``, which is exactly what
``ml_win_prediction_over_time.predict --eval`` then reports. The bug was found in
the pre-game model first, where it was worth about +0.06 AUC of inflation, and
this module had a verbatim copy of it.

Needs torch, so it runs in ``.venv-ml`` (3.13) - see
``tests/test_ml_venv_imports.py`` for why that venv exists.
"""

import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ML_PYTHON = REPO_ROOT / ".venv-ml" / "bin" / "python"

_PROBE = r"""
import gzip, json, sys
from pathlib import Path

from ml_win_prediction_over_time.dataset import WinProbDataModule
from ml_win_prediction_over_time.features import FeatureStats, match_to_sequence

out = Path(sys.argv[1])


def record(i: int) -> dict:
    # Two 30s buckets of trivial events; enough to encode, shape is irrelevant.
    return {
        "match_id": i,
        "time_stamp_begin": 1700000000 + i,
        "duration_minutes": 2.0,
        "frame_count": 3600,
        "snapshot_interval": 30,
        "label_a_win": i % 2,
        "team_a_players": ["alpha"],
        "team_b_players": ["bravo"],
        "events": [[10, 0, 0, 100], [20, 2, 1, 50]],
        "money": {"0": [1000, 1200, 1400], "1": [1000, 1100, 1300]},
    }


def write(recs, path):
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r))
            fh.write("\n")


train = [record(i) for i in range(100)]
dev = [record(i) for i in range(100, 130)]
write(train, out / "train.jsonl.gz")
write(dev, out / "dev.jsonl.gz")
FeatureStats.fit([match_to_sequence(r) for r in train]).save(out / "feature_stats.json")

dm = WinProbDataModule(out, batch_size=8)
dm.setup()
print(json.dumps({
    "val_frac": dm.val_frac,
    "fit": [s.match_id for s in dm._train],
    "val": [s.match_id for s in dm._val],
    "dev": [s.match_id for s in dm._dev],
}))
"""


@pytest.mark.skipif(
    not ML_PYTHON.exists(), reason=".venv-ml (3.13 + torch) not present"
)
def test_validation_is_carved_from_train_not_dev(tmp_path: Path) -> None:
    probe = tmp_path / "probe.py"
    probe.write_text(_PROBE)
    result = subprocess.run(  # noqa: S603
        [str(ML_PYTHON), str(probe), str(tmp_path)],
        cwd=REPO_ROOT,
        env={"PYTHONPATH": str(REPO_ROOT), "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    got = json.loads(result.stdout.strip().splitlines()[-1])

    fit, val, dev = set(got["fit"]), set(got["val"]), set(got["dev"])
    assert got["val_frac"] > 0, "default must not validate on dev"
    assert val
    assert not (val & dev)
    assert not (fit & val)
    assert fit | val == set(range(100))
    assert dev == set(range(100, 130))
    assert min(val) > max(fit), "validation must be the most recent slice of train"
