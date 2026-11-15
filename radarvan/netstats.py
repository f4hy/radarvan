"""Parse the client logs cncstats stores per match seed into `MatchNetstats`.

The log format is undocumented; the line shapes below were read from real logs.
"""

from __future__ import annotations

import gzip
import io
import re
import statistics
import zipfile
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field

from .api_types import (
    Freeze,
    MatchNetstats,
    NetstatSample,
    NetstatsSummary,
    PingSample,
    PlayerNetstats,
    RosterSlot,
)

# Bump when parsing changes what `NetstatsSummary` would hold for the same logs;
# the netstats job re-derives every stored row from an older version.
PARSER_VERSION = 3

_LOG_FILES = ("ReleaseLog.txt.gz", "ReleaseLog.prev.txt.gz")
# The first NETSTAT window is the map loading, not play.
_LOAD_FRAMES = 600

_LINE = re.compile(r"\[(\d\d):(\d\d):(\d\d)\] (.*)")
_START = re.compile(r"=== Match start: .*seed=(\d+) .*localSlot=(\d+)")
_END = re.compile(r"=== Match end: frame=(\d+) desync=(\d+)")
_ROSTER = re.compile(r"ROSTER slot=(\d+) name=(.+?) (?:\S+ )?template=.*?team=(-?\d+)")
_NETSTAT = re.compile(
    r"NETSTAT frame=(\d+) .*?fps=(\d+) .*?peers=\[([^\]]*)\] (?:rwait=\S+ )?"
    r"client=([\d.]+)/max(\d+) logic=([\d.]+)/max(\d+) objs=(\d+)"
)
_STALL = re.compile(r"NETSTALL frame=(\d+) waited=(\d+)ms on=0x([0-9a-f]+)")
# Every wait in the window, long ones included: count/total/max, then count per slot.
_WINDOW_STALLS = re.compile(r" stall=(\d+)/(\d+)ms/max\d+ on=\[([^\]]*)\]")
_ROUTE = re.compile(r"(\d+):\w/(\d+)ms/")


@dataclass
class _Block:
    slot: int
    t0: int
    teams: dict[int, int] = field(default_factory=dict)
    names: dict[int, str] = field(default_factory=dict)
    samples: list[NetstatSample] = field(default_factory=list)
    pings: list[PingSample] = field(default_factory=list)
    freezes: list[Freeze] = field(default_factory=list)
    # Waits too short for a NETSTALL line, per slot waited on.
    stalls: Counter[int] = field(default_factory=Counter)
    stall_ms: defaultdict[int, float] = field(
        default_factory=lambda: defaultdict(float)
    )
    has_peers: bool = False
    frames: int | None = None
    desync: bool | None = None


def _parse_log(lines: Iterable[str], seed: int) -> _Block | None:
    block: _Block | None = None
    result: _Block | None = None
    window_freezes: list[Freeze] = []
    for raw in lines:
        m = _LINE.match(raw)
        if not m:
            continue
        h, mi, s, body = int(m[1]), int(m[2]), int(m[3]), m[4].rstrip("\r\n")
        now = h * 3600 + mi * 60 + s
        start = body.startswith("=== Match start") and _START.search(body)
        if start:
            block = _Block(int(start[2]), now) if int(start[1]) == seed else None
            continue
        if block is None:
            continue
        rel = now - block.t0 if now >= block.t0 else now + 86400 - block.t0
        if body.startswith("=== Match end") and (end := _END.search(body)):
            block.frames, block.desync = int(end[1]), end[2] != "0"
            result, block = block, None
        elif ros := _ROSTER.match(body):
            block.names[int(ros[1])] = ros[2]
            block.teams[int(ros[1])] = int(ros[3])
        elif (ns := _NETSTAT.match(body)) and int(ns[1]) > _LOAD_FRAMES:
            if ws := _WINDOW_STALLS.search(body):
                _add_short_stalls(block, ws, window_freezes)
            window_freezes = []
            block.has_peers = block.has_peers or bool(ns[3].strip())
            block.samples.append(
                NetstatSample(
                    frame=int(ns[1]),
                    fps=int(ns[2]),
                    client_ms_avg=float(ns[4]),
                    client_ms_max=int(ns[5]),
                    logic_ms_avg=float(ns[6]),
                    logic_ms_max=int(ns[7]),
                    objects=int(ns[8]),
                )
            )
        elif st := _STALL.match(body):
            mask = int(st[3], 16)
            freeze = Freeze(
                frame=int(st[1]),
                waited_ms=int(st[2]),
                slots=[i for i in range(32) if mask >> i & 1],
            )
            block.freezes.append(freeze)
            window_freezes.append(freeze)
        elif body.startswith("GO routes:"):
            ms = [int(r[2]) for r in _ROUTE.finditer(body)]
            if ms:
                block.pings.append(
                    PingSample(
                        seconds=rel, median_ms=statistics.median(ms), max_ms=max(ms)
                    )
                )
    # A match with no "Match end" line (crash, early quit) still has its data.
    return result or block


def _add_short_stalls(
    block: _Block, ws: re.Match[str], window_freezes: list[Freeze]
) -> None:
    """Credit a window's waits, minus its NETSTALLs, to slots by their share of the count."""
    counts = Counter[int]()
    for entry in ws[3].split():
        slot, _, n = entry.partition(":")
        counts[int(slot)] += int(n)
    for f in window_freezes:
        counts.subtract(f.slots)
    ms = int(ws[2]) - sum(f.waited_ms for f in window_freezes)
    counts = +counts
    total = sum(counts.values())
    if ms <= 0 or not total:
        return
    for slot, n in counts.items():
        block.stalls[slot] += n
        block.stall_ms[slot] += ms * n / total


def _read_lines(zf: zipfile.ZipFile, name: str) -> Iterable[str]:
    # Streamed: one 8-player match is ~23 MB of log text once decompressed.
    with zf.open(name) as member, gzip.open(member, "rt", errors="replace") as text:
        yield from text


def parse_match_netstats(zip_bytes: bytes, seed: int) -> MatchNetstats:
    """Build the report from a cncstats `/get_logs` zip (`<player>/<file>.gz`)."""
    blocks: dict[str, _Block] = {}
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for name in sorted(zf.namelist()):
            player, _, fname = name.partition("/")
            if fname not in _LOG_FILES or player in blocks:
                continue
            block = _parse_log(_read_lines(zf, name), seed)
            if block is not None:
                blocks[player] = block

    # Only the router host's log lists every peer, so it sees every freeze.
    view = next((p for p, b in blocks.items() if b.has_peers), None)
    if view is None and blocks:
        view = max(blocks, key=lambda p: len(blocks[p].freezes))
    freezes = blocks[view].freezes if view else []

    players = sorted(
        (
            PlayerNetstats(
                slot=b.slot,
                name=name,
                team=b.teams.get(b.slot),
                samples=b.samples,
                pings=b.pings,
                client_ms_avg=_mean([s.client_ms_avg for s in b.samples]),
                logic_ms_avg=_mean([s.logic_ms_avg for s in b.samples]),
                peak_objects=max((s.objects for s in b.samples), default=None),
                median_ping_ms=(
                    statistics.median(p.median_ms for p in b.pings) if b.pings else None
                ),
                min_fps=min((s.fps for s in b.samples), default=None),
            )
            for name, b in blocks.items()
        ),
        key=lambda p: p.slot,
    )
    ended = next((b for b in blocks.values() if b.frames is not None), None)
    return MatchNetstats(
        seed=seed,
        frames=ended.frames if ended else None,
        desync=ended.desync if ended else None,
        players=players,
        roster=_roster(blocks),
        freezes=freezes,
        freezes_view_slot=blocks[view].slot if view else None,
    )


def _roster(blocks: dict[str, _Block]) -> list[RosterSlot]:
    # A player's own log is excluded: the one with a bad link waits on everyone.
    uploaders = {b.slot: player for player, b in blocks.items()}
    logged: dict[int, str] = {}
    for b in blocks.values():
        logged = b.names | logged
    names = uploaders | logged
    blamed = {s for b in blocks.values() for f in b.freezes for s in f.slots}
    stalled = {s for b in blocks.values() for s in b.stalls}
    roster = []
    for slot in sorted(names.keys() | blamed | stalled):
        views = [b for b in blocks.values() if b.slot != slot]
        mine = [[f for f in b.freezes if slot in f.slots] for b in views]
        roster.append(
            RosterSlot(
                slot=slot,
                name=names.get(slot, f"slot {slot}"),
                has_logs=slot in uploaders,
                views=len(views),
                freezes=_median_int([len(fs) for fs in mine]),
                freeze_ms=_median_int([sum(f.waited_ms for f in fs) for fs in mine]),
                stalls=_median_int([b.stalls[slot] for b in views]),
                stall_ms=_median_int([b.stall_ms.get(slot, 0.0) for b in views]),
            )
        )
    return roster


def summarize(report: MatchNetstats) -> NetstatsSummary:
    return NetstatsSummary.model_validate(report, from_attributes=True)


def _median_int(values: list[float]) -> int:
    return round(statistics.median(values)) if values else 0


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None
