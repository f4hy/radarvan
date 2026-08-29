"""Every `radarvan` module `ml/` imports must stay Python 3.13-parseable.

Training runs in `.venv-ml` on 3.13 (torch has no 3.14 wheel) with the repo on
PYTHONPATH, so `ml.train` imports ~40 `radarvan` modules under that
interpreter. Syntax the app's 3.14 accepts is not automatically fine there: an
unparenthesized `except A, B:` (PEP 758) is a SyntaxError on 3.13, and
`ruff format` with `target-version = "py314"` *introduces* that form
unprompted. It cost a training cycle once, dying at `player_role.py` on
import; `# fmt: skip` pins the one occurrence we have.

`ast.parse(..., feature_version=(3, 13))` is the guard that actually runs
everywhere: it needs no 3.13 interpreter, so it works in CI, where `.venv-ml`
does not exist. The subprocess check below is the belt-and-braces version for
machines that do have the venv - it catches import-time problems a parse can't
see, but it can only ever run there.
"""

import ast
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ML_PYTHON = REPO_ROOT / ".venv-ml" / "bin" / "python"
ML_VENV_VERSION = (3, 13)

# The torch-free entry points. Importing these pulls in the whole radarvan
# surface ml/ depends on (api_types, db, matches, repositories, ...).
ML_ENTRY_POINTS = ["ml.features", "ml.snapshot", "ml.split"]


def _radarvan_modules_reachable_from_ml() -> list[Path]:
    """Source files of every radarvan module the ml entry points import.

    Derived by importing them here and reading `sys.modules`, so the list can
    never drift out of date the way a hand-maintained one would.
    """
    for name in ML_ENTRY_POINTS:
        __import__(name)
    paths = {
        Path(mod.__file__)
        for name, mod in sys.modules.items()
        if name.split(".")[0] == "radarvan"
        and getattr(mod, "__file__", None)
        and str(mod.__file__).endswith(".py")
    }
    return sorted(paths)


def _ml_package_sources() -> list[Path]:
    """Every source file in the two ML packages themselves.

    The reachable-set above only covers ``radarvan/`` modules, so nothing
    guarded the ML packages' *own* files - and ``ruff format`` duly rewrote
    ``ml_win_prediction_over_time/snapshot.py``'s except clause into the PEP 758
    bare form, which is a SyntaxError on 3.13 and broke every training entry
    point in that package. These are the files most exposed to the trap,
    because they are the ones that only ever run under the 3.13 venv.
    """
    return sorted(
        path
        for pkg in ("ml", "ml_win_prediction_over_time")
        for path in (REPO_ROOT / pkg).rglob("*.py")
        if "__pycache__" not in path.parts
    )


REACHABLE = _radarvan_modules_reachable_from_ml() + _ml_package_sources()


def test_the_reachable_set_is_not_empty() -> None:
    """Guards the guard: an import change must not silently empty the list."""
    assert len(REACHABLE) > 10


@pytest.mark.parametrize("path", REACHABLE, ids=lambda p: p.name)
def test_module_parses_under_the_ml_venv_python(path: Path) -> None:
    major, minor = ML_VENV_VERSION
    try:
        ast.parse(path.read_text(), filename=str(path), feature_version=minor)
    except SyntaxError as e:  # pragma: no cover - only on a real regression
        pytest.fail(
            f"{path.relative_to(REPO_ROOT)} does not parse on Python "
            f"{major}.{minor}, which is what ml/ trains under: {e}\n"
            "If this is an `except A, B:` clause, parenthesize it and add "
            "`# fmt: skip` so ruff format does not undo it."
        )


@pytest.mark.skipif(
    not ML_PYTHON.exists(), reason="ml training venv (.venv-ml) not built here"
)
@pytest.mark.parametrize(
    "module",
    [
        *ML_ENTRY_POINTS,
        # The other package trains under the same venv and has its own entry
        # points; importing them catches breakage a parse check cannot see.
        "ml_win_prediction_over_time.split",
        "ml_win_prediction_over_time.train",
        "ml_win_prediction_over_time.predict",
        "ml_win_prediction_over_time.export",
    ],
)
def test_module_imports_under_ml_venv(module: str) -> None:
    result = subprocess.run(  # noqa: S603
        [str(ML_PYTHON), "-c", f"import {module}"],
        cwd=REPO_ROOT,
        env={"PYTHONPATH": str(REPO_ROOT), "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, (
        f"{module} does not import under {ML_PYTHON}:\n{result.stderr}"
    )
