"""Early stopping must never watch the set we report on.

``ml.train`` selects the best checkpoint, stops early, and fits the calibration
temperature on ``val_loss``. For most of this model's life ``val_loss`` was
computed on ``dev.jsonl.gz`` — the very block ``ml.predict --eval`` and
``ml.rolling_eval`` then scored. That is test-set model selection, and it
inflated every published number; the temperature was worse still, fitted on a
slice of the *fit* block the weights had already memorised, so it came out
below 1 (more confident) on a model that needed less confidence.

The invariant this pins: with the default ``val_frac``, the validation set is
carved out of train, is disjoint from both the fit block and dev, and the fit
block plus the validation set is exactly the train split. It asserts the
property rather than a fixed size, so changing ``val_frac`` doesn't rewrite the
test.

Needs torch, so it runs in ``.venv-ml`` (3.13) like the rest of ml/ — see
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
from datetime import date, datetime, timedelta
from pathlib import Path

from ml.dataset import MatchDataModule
from ml.features import build_vocab
from radarvan.api_types import General, MatchInfo, Player, Team
from radarvan.player_role import PlayerRole

out = Path(sys.argv[1])


def match(i: int) -> MatchInfo:
    day = date(2024, 1, 1) + timedelta(days=i)
    def p(name, team, pos):
        return Player(
            name=name, color="red", team=Team(team), general=General.USA,
            starting_position=pos, role=PlayerRole.HUMAN, won=(team == 1),
        )
    return MatchInfo(
        id=i, timestamp=datetime(day.year, day.month, day.day), date=day,
        map="maps/tournament island", winning_team=Team.ONE,
        players=[p("alpha", 1, 1), p("bravo", 2, 2)],
        duration_minutes=10.0, filename=f"{i}.rep",
    )


def write(ms, path):
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        for m in ms:
            fh.write(m.model_dump_json())
            fh.write("\n")


train = [match(i) for i in range(100)]
dev = [match(i) for i in range(100, 130)]
write(train, out / "train.jsonl.gz")
write(dev, out / "dev.jsonl.gz")
build_vocab(train).save(out / "vocab.json")

dm = MatchDataModule(out, batch_size=8)
dm.setup()
print(json.dumps({
    "val_frac": dm.val_frac,
    "fit": [m.match_id for m in dm._train],
    "val": [m.match_id for m in dm._val],
    "dev": [m.match_id for m in dm._dev],
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
    assert val, "a non-zero val_frac must produce a validation set"
    # The set early stopping watches is disjoint from the reported set...
    assert not (val & dev)
    # ...and from the games the weights are fitted on.
    assert not (fit & val)
    # Nothing is dropped: train == fit + val, and dev is untouched.
    assert fit | val == set(range(100))
    assert dev == set(range(100, 130))
    # It is the most *recent* slice of train — closest in time to dev.
    assert min(val) > max(fit)
