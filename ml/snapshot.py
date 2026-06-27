"""Pull competitive matches from the DB into a frozen, versioned snapshot.

Training never touches the live DB — it reads an immutable snapshot so runs are
reproducible. We persist the full ``MatchInfo`` (lossless pydantic JSON) rather
than pre-encoded features, so we can change feature engineering without
re-pulling.

Usage::

    DATABASE_URL=... uv run python -m ml.snapshot [--out-dir ml/data]

Writes ``snapshot-<UTCdate>.jsonl.gz`` + ``snapshot-<UTCdate>.manifest.json``.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import structlog

from radarvan import db as dbmod
from radarvan import player_rating
from radarvan.api_types import MatchInfo
from radarvan.db_utils import DatabaseManager, ReplayManager
from radarvan.logging_config import configure_logging
from radarvan.matches import get_match_infos

from .config import DATA_DIR, SCHEMA_VERSION
from .map_features import build_table

logger = structlog.get_logger(__name__)


def _git_sha() -> str | None:
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=Path(__file__).parent)  # noqa: S607
            .decode()
            .strip()
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def fetch_competitive_matches() -> list[MatchInfo]:
    """All ratable, competitive team games — the same gate the rating model uses."""
    constring = os.getenv("DATABASE_URL")
    if constring is None:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    db_manager = DatabaseManager(constring)
    with db_manager.SessionLocal() as session:
        replay_manager = ReplayManager(session, auto_commit=False, notify=False)
        matches = get_match_infos(replay_manager)
    competitive = [m for m in matches if player_rating.is_ratable_team_game(m)]
    logger.info(
        "fetched matches", total=len(matches), competitive=len(competitive)
    )
    return competitive


def fetch_map_feature_table() -> dict[str, list[float]]:
    """Numeric geometry features for *every* map with a MapData row.

    Frozen into the snapshot so training is reproducible and serving can score
    any map that has geometry (not just trained ones). Torch-free.
    """
    constring = os.getenv("DATABASE_URL")
    if constring is None:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    db_manager = DatabaseManager(constring)
    with db_manager.SessionLocal() as session:
        rows = session.query(dbmod.MapData.map_name, dbmod.MapData.data).all()
    table = build_table((name, data) for name, data in rows)
    logger.info("map feature table", n_maps=len(table), n_rows=len(rows))
    return table


def write_snapshot(
    matches: list[MatchInfo],
    out_dir: Path,
    map_feat_table: dict[str, list[float]] | None = None,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d")
    data_path = out_dir / f"snapshot-{stamp}.jsonl.gz"
    manifest_path = out_dir / f"snapshot-{stamp}.manifest.json"
    map_feat_path = out_dir / f"map_features-{stamp}.json"

    # Sort by timestamp so temporal splitting is trivial downstream.
    ordered = sorted(matches, key=lambda m: m.timestamp)
    with gzip.open(data_path, "wt", encoding="utf-8") as fh:
        for m in ordered:
            fh.write(m.model_dump_json())
            fh.write("\n")

    if map_feat_table is not None:
        map_feat_path.write_text(json.dumps(map_feat_table, indent=2, sort_keys=True))

    dates = [m.date for m in ordered]
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "git_sha": _git_sha(),
        "n_matches": len(ordered),
        "date_min": min(dates).isoformat() if dates else None,
        "date_max": max(dates).isoformat() if dates else None,
        "filter": "player_rating.is_ratable_team_game",
        "data_file": data_path.name,
        "map_features_file": map_feat_path.name if map_feat_table is not None else None,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    logger.info("wrote snapshot", path=str(data_path), n=len(ordered))
    return data_path


def load_snapshot(path: Path) -> list[MatchInfo]:
    """Read a snapshot's matches back into ``MatchInfo`` (lossless)."""
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as fh:  # type: ignore[operator]
        return [MatchInfo.model_validate_json(line) for line in fh if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DATA_DIR)
    args = parser.parse_args()

    configure_logging(dev=True)
    matches = fetch_competitive_matches()
    if not matches:
        raise SystemExit("No competitive matches found — check DATABASE_URL / filters.")
    map_feat_table = fetch_map_feature_table()
    write_snapshot(matches, args.out_dir, map_feat_table)


if __name__ == "__main__":
    main()
