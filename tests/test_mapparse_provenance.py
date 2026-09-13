"""Pins the committed mapparse binary. A rebuild is expected to fail these."""

import hashlib
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MAPPARSE = REPO_ROOT / "mapparse"
README = REPO_ROOT / "README.md"

EXPECTED_SHA256 = "f1463691d74e439058cde85b4ad960648e582b771de784e35e08d6a527ad0e8c"
EXPECTED_VCS_REVISION = "673567269893914c9a8c073f1375127e99a38242"


def test_the_binary_is_committed_and_executable() -> None:
    assert MAPPARSE.is_file()
    # _resolve_mapparse_path needs the +x bit; git tracks the mode.
    assert MAPPARSE.stat().st_mode & 0o111


def test_the_binary_matches_the_recorded_hash() -> None:
    actual = hashlib.sha256(MAPPARSE.read_bytes()).hexdigest()
    assert actual == EXPECTED_SHA256, (
        "mapparse changed. If deliberate: update this hash and the provenance "
        "table in README.md, then plan a POST /api/reparse_maps - every MapData "
        "row now has a stale mapparse_bin_hash."
    )


def test_the_readme_records_the_same_hash() -> None:
    assert EXPECTED_SHA256 in README.read_text()


def test_the_readme_names_the_upstream_repository() -> None:
    # The one fact not recoverable from the binary itself.
    assert "github.com/bill-rich/mapparse" in README.read_text()


@pytest.mark.skipif(
    not Path("/usr/bin/go").exists() and not Path("/usr/local/go/bin/go").exists(),
    reason="go toolchain not installed here",
)
def test_the_binary_reports_the_recorded_upstream_revision() -> None:
    result = subprocess.run(  # noqa: S603
        ["go", "version", "-m", str(MAPPARSE)],  # noqa: S607
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        pytest.skip(f"go version -m failed: {result.stderr.strip()}")
    match = re.search(r"vcs\.revision=(\S+)", result.stdout)
    assert match is not None
    assert match.group(1) == EXPECTED_VCS_REVISION
