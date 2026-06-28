"""Pull competitive matches' full event streams into a frozen, versioned snapshot.

Unlike ``ml/snapshot.py`` (which stores pre-game ``MatchInfo``), this reads the
parsed replay JSON for each match from S3 and distils the in-game event stream
(builds, kills, captures, per-side money series) into a compact per-match record.
Feature engineering happens later in ``features.py``, so the snapshot stays small
but lossless enough to re-derive features without re-pulling from S3.

Usage::

    DATABASE_URL=... uv run --group ml python -m ml_win_prediction_over_time.snapshot

Writes ``snapshot-<UTCdate>.jsonl.gz`` + ``snapshot-<UTCdate>.manifest.json``.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import subprocess
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

from radarvan import db as dbmod
from radarvan import player_rating
from radarvan import utils as rv_utils
from radarvan.cncstats_model.zhreplay import EnhancedReplayV2
from radarvan.db_utils import DatabaseManager, ReplayManager
from radarvan.logging_config import configure_logging
from radarvan.matches import get_match_infos
from radarvan.replay_files import parse_json

from .config import DATA_DIR, SCHEMA_VERSION

logger = structlog.get_logger(__name__)

# Event type codes packed into each [frame, type, side, value] row.
EV_UNIT = 0  # a (non-structure) unit finished
EV_STRUCT = 1  # a structure finished
EV_KILL = 2  # a kill (value = build cost of the destroyed object)
EV_CAPTURE = 3  # a structure captured

# One distilled per-match snapshot record (heterogeneous JSON-ish payload).
Record = dict[str, Any]


def record_from_replay(replay: EnhancedReplayV2) -> Record | None:
    """Distil one replay into a compact, side-labelled event record.

    Returns ``None`` for replays this first model doesn't handle: no enhanced
    stats, not exactly two human sides, or no decisive winner.
    """
    if replay.stats is None:
        return None
    humans = [
        p for p in replay.summary if p.team >= 0 and p.player_type == "Human"
    ]
    teams = sorted({p.team for p in humans})
    if len(teams) != 2:
        return None
    team_a = teams[0]

    # side 0 == team_a, side 1 == the other team.
    index_side: dict[int, int] = {}
    side_won = {0: False, 1: False}
    for p in humans:
        side = 0 if p.team == team_a else 1
        index_side[p.index] = side
        if p.win:
            side_won[side] = True
    if side_won[0] == side_won[1]:
        return None  # draw / undetermined
    label_a_win = 1 if side_won[0] else 0

    stats = replay.stats

    # Cost lookup to value kills by what was destroyed.
    unit_cost: dict[str, int] = {}
    for b in stats.build_events:
        if b.object not in unit_cost and b.cost > 0:
            unit_cost[b.object] = b.cost

    events: list[list[int]] = []
    for b in stats.build_events:
        owner = index_side.get(b.player)
        if owner is None:
            continue
        kind = EV_STRUCT if b.object_type == "structure" else EV_UNIT
        events.append([b.frame, kind, owner, int(b.cost)])
    for k in stats.kill_events:
        owner = index_side.get(k.killer_player)
        if owner is None:
            continue
        events.append([k.frame, EV_KILL, owner, int(unit_cost.get(k.victim, 0))])
    for c in stats.capture_events:
        owner = index_side.get(c.new_owner)
        if owner is None:
            continue
        events.append([c.frame, EV_CAPTURE, owner, 0])
    events.sort(key=lambda e: e[0])

    # Per-side money series: sum each snapshot across the side's players.
    series_by_index = {tp.index: tp.money for tp in stats.time_series.players}
    present = [series_by_index[i] for i in index_side if i in series_by_index]
    n_snap = min((len(s) for s in present), default=0)
    money: dict[str, list[int]] = {"0": [], "1": []}
    for side in (0, 1):
        idxs = [i for i, s in index_side.items() if s == side and i in series_by_index]
        money[str(side)] = [
            sum(series_by_index[i][t] for i in idxs) for t in range(n_snap)
        ]

    frame_count = (replay.header.frame_count if replay.header else 0) or 0
    snapshot_interval = (
        replay.game_info.snapshot_interval if replay.game_info else 0
    )
    return {
        "match_id": replay.replay_id,
        "time_stamp_begin": replay.header.time_stamp_begin,
        "duration_minutes": rv_utils.duration_minutes(replay),
        "frame_count": frame_count,
        "snapshot_interval": snapshot_interval,
        "label_a_win": label_a_win,
        "events": events,
        "money": money,
    }


def _git_sha() -> str | None:
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=Path(__file__).parent)  # noqa: S607
            .decode()
            .strip()
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def iter_competitive_replays() -> Iterator[tuple[int, str]]:
    """Yield ``(match_id, json_s3_uri)`` for ratable team games (same gate as ml/)."""
    constring = os.getenv("DATABASE_URL")
    if constring is None:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    db_manager = DatabaseManager(constring)
    with db_manager.SessionLocal() as session:
        replay_manager = ReplayManager(session, auto_commit=False, notify=False)
        infos = get_match_infos(replay_manager)
        competitive = {
            m.id for m in infos if player_rating.is_ratable_team_game(m)
        }
        rows = session.query(dbmod.Match.match_id, dbmod.Match.json_s3_uri).all()
    logger.info("matches", total=len(rows), competitive=len(competitive))
    for match_id, uri in rows:
        if match_id in competitive and uri:
            yield match_id, uri


def build_records() -> list[Record]:
    records: list[Record] = []
    skipped = 0
    for match_id, uri in iter_competitive_replays():
        try:
            replay = parse_json(uri)
            rec = record_from_replay(replay)
        except Exception as exc:
            logger.warning("parse failed", match_id=match_id, error=str(exc))
            rec = None
        if rec is None:
            skipped += 1
            continue
        records.append(rec)
        if len(records) % 200 == 0:
            logger.info("progress", kept=len(records), skipped=skipped)
    logger.info("built records", kept=len(records), skipped=skipped)
    return records


def write_snapshot(records: list[Record], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d")
    data_path = out_dir / f"snapshot-{stamp}.jsonl.gz"
    manifest_path = out_dir / f"snapshot-{stamp}.manifest.json"

    ordered = sorted(records, key=lambda r: r["time_stamp_begin"])
    with gzip.open(data_path, "wt", encoding="utf-8") as fh:
        for r in ordered:
            fh.write(json.dumps(r, separators=(",", ":")))
            fh.write("\n")

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "git_sha": _git_sha(),
        "n_matches": len(ordered),
        "filter": "player_rating.is_ratable_team_game + 2 human sides",
        "data_file": data_path.name,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
    logger.info("wrote snapshot", path=str(data_path), n=len(ordered))
    return data_path


def load_snapshot(path: Path) -> list[Record]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DATA_DIR)
    args = parser.parse_args()

    configure_logging(dev=True)
    records = build_records()
    if not records:
        raise SystemExit("No usable matches found — check DATABASE_URL / filters.")
    write_snapshot(records, args.out_dir)


if __name__ == "__main__":
    main()
