"""Parse the client logs cncstats stores per match seed into `MatchNetstats`.

The log format is undocumented; the line shapes below were read from real logs.
"""

from __future__ import annotations

import gzip
import io
import re
import statistics
import zipfile
from dataclasses import dataclass, field

from .api_types import (
    Freeze,
    MatchNetstats,
    NetstatSample,
    PingSample,
    PlayerNetstats,
)

_LOG_FILES = ("ReleaseLog.txt.gz", "ReleaseLog.prev.txt.gz")
# The first NETSTAT window is the map loading, not play.
_LOAD_FRAMES = 600

_LINE = re.compile(r"\[(\d\d):(\d\d):(\d\d)\] (.*)")
_START = re.compile(r"=== Match start: .*seed=(\d+) .*localSlot=(\d+)")
_END = re.compile(r"=== Match end: frame=(\d+) desync=(\d+)")
_ROSTER = re.compile(r"ROSTER slot=(\d+) name=\S+ .*team=(\d+)")
_NETSTAT = re.compile(
    r"NETSTAT frame=(\d+) .*?fps=(\d+) .*?peers=\[([^\]]*)\] (?:rwait=\S+ )?"
    r"client=([\d.]+)/max(\d+) logic=([\d.]+)/max(\d+) objs=(\d+)"
)
_STALL = re.compile(r"NETSTALL frame=(\d+) waited=(\d+)ms on=0x([0-9a-f]+)")
_ROUTE = re.compile(r"(\d+):\w/(\d+)ms/")


@dataclass
class _Block:
    slot: int
    t0: int
    teams: dict[int, int] = field(default_factory=dict)
    samples: list[NetstatSample] = field(default_factory=list)
    pings: list[PingSample] = field(default_factory=list)
    freezes: list[Freeze] = field(default_factory=list)
    has_peers: bool = False
    frames: int | None = None
    desync: bool | None = None


def _gunzip(data: bytes) -> str:
    return gzip.decompress(data).decode("utf-8", errors="replace")


def _parse_log(text: str, seed: int) -> _Block | None:
    block: _Block | None = None
    result: _Block | None = None
    for raw in text.splitlines():
        m = _LINE.match(raw)
        if not m:
            continue
        h, mi, s, body = int(m[1]), int(m[2]), int(m[3]), m[4]
        now = h * 3600 + mi * 60 + s
        start = _START.search(body)
        if start:
            block = _Block(int(start[2]), now) if int(start[1]) == seed else None
            continue
        if block is None:
            continue
        rel = now - block.t0 if now >= block.t0 else now + 86400 - block.t0
        if end := _END.search(body):
            block.frames, block.desync = int(end[1]), end[2] != "0"
            result, block = block, None
        elif ros := _ROSTER.match(body):
            block.teams[int(ros[1])] = int(ros[2])
        elif (ns := _NETSTAT.match(body)) and int(ns[1]) > _LOAD_FRAMES:
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
            block.freezes.append(
                Freeze(
                    frame=int(st[1]),
                    waited_ms=int(st[2]),
                    slots=[i for i in range(32) if mask >> i & 1],
                )
            )
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


def parse_match_netstats(zip_bytes: bytes, seed: int) -> MatchNetstats:
    """Build the report from a cncstats `/get_logs` zip (`<player>/<file>.gz`)."""
    blocks: dict[str, _Block] = {}
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = set(zf.namelist())
        for name in sorted(names):
            player, _, fname = name.partition("/")
            if fname not in _LOG_FILES or player in blocks:
                continue
            block = _parse_log(_gunzip(zf.read(name)), seed)
            if block is not None:
                blocks[player] = block

    # Only the router host's log lists every peer, so it sees every freeze.
    view = next((p for p, b in blocks.items() if b.has_peers), None)
    if view is None and blocks:
        view = max(blocks, key=lambda p: len(blocks[p].freezes))
    freezes = blocks[view].freezes if view else []

    players = []
    for name, b in blocks.items():
        mine = [f for f in freezes if b.slot in f.slots]
        players.append(
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
                freezes_caused=len(mine),
                freeze_ms_caused=sum(f.waited_ms for f in mine),
            )
        )
    players.sort(key=lambda p: p.slot)
    ended = next((b for b in blocks.values() if b.frames is not None), None)
    return MatchNetstats(
        seed=seed,
        frames=ended.frames if ended else None,
        desync=ended.desync if ended else None,
        players=players,
        freezes=freezes,
        freezes_view_slot=blocks[view].slot if view else None,
    )


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None
