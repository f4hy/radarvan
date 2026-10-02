"""Pull competitive matches' full event streams into a frozen, versioned snapshot.

Unlike ``ml/snapshot.py`` (which stores pre-game ``MatchInfo``), this reads the
parsed replay JSON for each match from S3 and distils the in-game event stream
(builds, kills, captures, eliminations, per-side money and income series) into a
compact per-match record, labelled with the result as the app shows it.
Feature engineering happens later in ``features.py``, so the snapshot stays small
but lossless enough to re-derive features without re-pulling from S3.

Usage::

    DATABASE_URL=... uv run --group ml python -m ml_win_prediction_over_time.snapshot

Writes ``snapshot-<UTCdate>.jsonl.gz`` + ``snapshot-<UTCdate>.manifest.json``.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import subprocess
from collections import Counter
from collections.abc import Iterator
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, NamedTuple

import structlog

from radarvan import db as dbmod
from radarvan import player_rating
from radarvan import utils as rv_utils
from radarvan.api_types import MatchInfo, Team
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
EV_KILL = 2  # an enemy non-structure killed (value = its build cost)
EV_CAPTURE = 3  # a structure captured
EV_KILL_STRUCT = 4  # an enemy structure destroyed (value = its build cost)
EV_DEATH = 5  # a player eliminated (side = the eliminated player's side)

# One distilled per-match snapshot record (heterogeneous JSON-ish payload).
Record = dict[str, Any]


def higher_slot_is_side_a(match_id: int) -> bool:
    """Stable per-match coin flip: should the *higher* team slot be side A?

    If side A were always the lower lobby team-slot, the model keys on lobby
    order — and in our data the lower slot wins only ~42% of games, so the
    sequence model's t=0 prior (no events yet) sits at ~0.42 instead of 0.5.
    Team-slot order is arbitrary, so we assign sides by a deterministic hash of
    the match id; that balances ``label_a_win`` to ~0.5 and removes the spurious
    order signal. Deterministic (not ``random``) so training and serving — which
    both call this on the same ``match_id`` — always agree.

    This is a *training-time* device only. Anything user-facing must un-flip it
    back to "team A == lower team id" so it agrees with the pre-game model's
    A/B labelling — see ``radarvan.winprob_inference.predict_over_time``.
    """
    digest = hashlib.blake2b(str(match_id).encode(), digest_size=2).digest()
    return bool(digest[0] & 1)


def record_from_replay(replay: EnhancedReplayV2) -> Record | None:
    """Distil one replay into a compact, side-labelled event record.

    ``None`` unless the replay has enhanced stats and exactly two human sides of
    equal size with a decisive winner. ``label_a_win`` is the replay's own
    verdict; the snapshot swaps in the app's (``app_label``).
    """
    if replay.stats is None:
        return None
    humans = [p for p in replay.summary if p.team >= 0 and p.player_type == "Human"]
    teams = sorted({p.team for p in humans})
    if len(teams) != 2:
        return None
    # Uneven games (2v3) are out of scope for training, evaluation and serving.
    if sum(p.team == teams[0] for p in humans) != sum(
        p.team == teams[1] for p in humans
    ):
        return None
    # Side A is one of the two team slots, chosen by a stable per-match hash
    # rather than "lowest slot" so the model can't key on arbitrary lobby order.
    team_a = teams[1] if higher_slot_is_side_a(replay.replay_id) else teams[0]

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
    # Rosters per canonical side, derived here so serving never re-splits the
    # teams (and so the names can't drift from label_a_win / prob_team_a).
    team_a_players = [p.name for p in humans if p.team == team_a]
    team_b_players = [p.name for p in humans if p.team != team_a]

    stats = replay.stats

    unit_cost: dict[str, int] = {}
    object_type: dict[str, str] = {}
    for b in stats.build_events:
        if b.object not in unit_cost and b.cost > 0:
            unit_cost[b.object] = b.cost
        if b.object_type:
            object_type.setdefault(b.object, b.object_type)

    events: list[list[int]] = []
    for b in stats.build_events:
        owner = index_side.get(b.player)
        if owner is None:
            continue
        kind = EV_STRUCT if b.object_type == "structure" else EV_UNIT
        events.append([b.frame, kind, owner, int(b.cost)])
    for k in stats.kill_events:
        owner = index_side.get(k.killer_player)
        victim = index_side.get(k.victim_player)
        # Only kills of the enemy: friendly fire, civilians and neutral props
        # say nothing about who is winning.
        if owner is None or victim is None or owner == victim:
            continue
        value = unit_cost.get(k.victim, 0)
        # Zero-cost victims are projectiles, debris, hulls and mines (a Tunnel
        # Defender's missiles alone can outnumber real kills).
        if value <= 0:
            continue
        is_struct = (k.victim_type or object_type.get(k.victim)) == "structure"
        events.append(
            [k.frame, EV_KILL_STRUCT if is_struct else EV_KILL, owner, int(value)]
        )
    for c in stats.capture_events:
        owner = index_side.get(c.new_owner)
        if owner is None:
            continue
        events.append([c.frame, EV_CAPTURE, owner, 0])
    dead: set[int] = set()
    for d in stats.death_events:
        dead_side = index_side.get(d.player)
        if dead_side is None or d.player in dead:
            continue
        dead.add(d.player)
        events.append([d.frame, EV_DEATH, dead_side, 0])
    events.sort(key=lambda e: e[0])

    # Per-side cash on hand and cumulative income: each snapshot summed over
    # the side's players.
    ts_by_index = {tp.index: tp for tp in stats.time_series.players}
    present = [ts_by_index[i].money for i in index_side if i in ts_by_index]
    n_snap = min((len(s) for s in present), default=0)
    money: dict[str, list[int]] = {"0": [], "1": []}
    earned: dict[str, list[int]] = {"0": [], "1": []}
    for side in (0, 1):
        idxs = [i for i, s in index_side.items() if s == side and i in ts_by_index]
        money[str(side)] = [
            sum(ts_by_index[i].money[t] for i in idxs) for t in range(n_snap)
        ]
        earned[str(side)] = [
            sum(_at(ts_by_index[i].money_earned, t) for i in idxs)
            for t in range(n_snap)
        ]

    frame_count = (replay.header.frame_count if replay.header else 0) or 0
    snapshot_interval = replay.game_info.snapshot_interval if replay.game_info else 0
    return {
        "match_id": replay.replay_id,
        "time_stamp_begin": replay.header.time_stamp_begin,
        "duration_minutes": rv_utils.duration_minutes(replay),
        "frame_count": frame_count,
        "snapshot_interval": snapshot_interval,
        "label_a_win": label_a_win,
        "team_a_id": team_a,
        "team_size": len(team_a_players),
        "win_method": replay.win_method,
        "team_a_players": team_a_players,
        "team_b_players": team_b_players,
        "events": events,
        "money": money,
        "earned": earned,
    }


def _at(series: list[int], t: int) -> int:
    return series[t] if t < len(series) else (series[-1] if series else 0)


class Drop(StrEnum):
    NO_WINNER = "no_app_winner"
    ESTIMATED = "estimated_winner"
    MISMATCH = "replay_disagrees_with_app"


def app_label(rec: Record, info: MatchInfo, has_override: bool) -> int | Drop:
    """``label_a_win`` as the app shows the result, or why the match is unusable.

    An admin override is ground truth, but cncstats' ``estimatedWinner`` guess is
    not, and a replay whose own flags disagree with the app is dropped rather
    than trusted either way.
    """
    if info.winning_team == Team.NONE:
        return Drop.NO_WINNER
    if rec["win_method"] == "estimatedWinner" and not has_override:
        return Drop.ESTIMATED
    app_a_won = int(int(info.winning_team) == rec["team_a_id"])
    if app_a_won != rec["label_a_win"]:
        return Drop.MISMATCH
    return app_a_won


def _git_sha() -> str | None:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=Path(__file__).parent
            )
            .decode()
            .strip()
        )
    # Parens pinned, and the formatter told to leave them: PEP 758 makes the bare
    # form valid on the app's 3.14 (ruff format rewrites to it unprompted), but
    # this module is imported under the 3.13 training venv - no torch wheel for
    # 3.14 - where it is a SyntaxError. Same constraint as radarvan/player_role.py.
    except (subprocess.CalledProcessError, FileNotFoundError):  # fmt: skip
        return None


class CompetitiveReplay(NamedTuple):
    info: MatchInfo
    json_uri: str
    has_override: bool


def iter_competitive_replays() -> Iterator[CompetitiveReplay]:
    """Ratable team games (same gate as ml/) with the app's view of the result."""
    constring = os.getenv("DATABASE_URL")
    if constring is None:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    db_manager = DatabaseManager(constring)
    with db_manager.SessionLocal() as session:
        replay_manager = ReplayManager(session, auto_commit=False, notify=False)
        infos = {
            m.id: m
            for m in get_match_infos(replay_manager)
            if player_rating.is_ratable_team_game(m)
        }
        overridden = {
            mid
            for mid, o in replay_manager.get_overrides().items()
            if o.winning_team_id is not None
        }
        rows = session.query(dbmod.Match.match_id, dbmod.Match.json_s3_uri).all()
    logger.info("matches", total=len(rows), competitive=len(infos))
    for match_id, uri in rows:
        if match_id in infos and uri:
            yield CompetitiveReplay(infos[match_id], uri, match_id in overridden)


class BuiltRecords(NamedTuple):
    records: list[Record]
    skipped: Counter[str]  # count per reason a match was left out


def build_records() -> BuiltRecords:
    records: list[Record] = []
    skipped: Counter[str] = Counter()
    for comp in iter_competitive_replays():
        try:
            rec = record_from_replay(parse_json(comp.json_uri))
        except Exception as exc:
            logger.warning("parse failed", match_id=comp.info.id, error=str(exc))
            skipped["parse_failed"] += 1
            continue
        if rec is None:
            skipped["not_two_even_sides"] += 1
            continue
        label = app_label(rec, comp.info, comp.has_override)
        if isinstance(label, Drop):
            skipped[label.value] += 1
            continue
        records.append({**rec, "label_a_win": label})
        if len(records) % 200 == 0:
            logger.info("progress", kept=len(records), skipped=sum(skipped.values()))
    logger.info("built records", kept=len(records), skipped=dict(skipped))
    return BuiltRecords(records, skipped)


def write_snapshot(records: list[Record], out_dir: Path, skipped: Counter[str]) -> Path:
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
        "filter": "player_rating.is_ratable_team_game + 2 equal human sides",
        "label": "app winner (overrides apply); estimated/disagreeing dropped",
        "skipped": dict(skipped),
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
    records, skipped = build_records()
    if not records:
        raise SystemExit("No usable matches found — check DATABASE_URL / filters.")
    write_snapshot(records, args.out_dir, skipped)


if __name__ == "__main__":
    main()
