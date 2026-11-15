import gzip
import io
import zipfile

import pytest

from radarvan.api_types import NetstatsSummary, RosterSlot
from radarvan.netstats import (
    CONNECTION_DEFAULTS,
    POTATO_DEFAULTS,
    FlagThresholds,
    lag_flags,
    parse_match_netstats,
)

SEED = 51399702


def _log(slot: int, seed: int, *, peers: str, stall_on: int) -> str:
    return "\n".join(
        [
            f"[23:00:00] === Match start: map='m.map' mode=5 crcInterval=100 seed={seed} logicFps=60 localSlot={slot} resumeTo=0 ===",
            "[23:00:00] ROSTER slot=0 name=Ann human template=2 color=0 start=0 team=0 ip=0.0.0.0:0",
            "[23:00:00] ROSTER slot=1 name=Bob human template=2 color=0 start=0 team=1 ip=0.0.0.1:0",
            "[23:00:05] NETSTAT frame=30 ra=0 fps=0 router=0 lat=1/251 links=[] stall=0/0ms/max0 on=[] hitch=0/max0 rreq=0/0 peers=[] client=4.2/max80 logic=105.5/max3245 objs=227",
            f"[23:00:10] NETSTAT frame=700 ra=20 fps=60 router=0 lat=0/9 links=[] stall=0/0ms/max0 on=[] hitch=0/max0 rreq=0/0 peers=[{peers}] client=3.0/max10 logic=1.0/max5 objs=300",
            f"[23:00:15] NETSTALL frame=800 waited=600ms on=0x{1 << stall_on:02x}",
            f"[23:00:20] NETSTAT frame=1300 ra=20 fps=55 router=0 lat=0/9 links=[] stall=1/600ms/max600 on=[{stall_on}:1] hitch=0/max0 rreq=1/0 peers=[{peers}] rwait=0x02@1300 client=5.0/max12 logic=2.0/max9 objs=320",
            "[23:00:30] GO routes: 1:D/40ms/q1.00/pend0/out0k/qt0ms 2:D/60ms/q1.00/pend0/out0k/qt0ms 10:D/80ms/q1.00/pend0/out0k/qt0ms",
            "[23:00:59] === Match end: frame=2000 desync=0 ===",
        ]
    )


def _zip(files: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, text in files.items():
            zf.writestr(name, gzip.compress(text.encode()))
    return buf.getvalue()


def test_parses_only_the_requested_seed_and_attributes_freezes():
    other = _log(0, 111, peers="", stall_on=0)
    z = _zip(
        {
            # A previous match in the same log must not leak into this one.
            "Ann/ReleaseLog.txt.gz": other
            + "\n"
            + _log(0, SEED, peers="0:200/59 1:200/59", stall_on=1),
            "Bob/ReleaseLog.txt.gz": _log(1, SEED, peers="", stall_on=1),
            "Cat/ReleaseLog.txt.gz": other,
        }
    )
    r = parse_match_netstats(z, SEED)

    assert [p.name for p in r.players] == ["Ann", "Bob"]
    assert (r.frames, r.desync) == (2000, False)
    assert r.freezes_view_slot == 0  # the log that lists peers
    ann, bob = r.players
    assert ann.team == 0 and bob.team == 1
    # The loading window (frame 30) is dropped; both later windows are kept,
    # including the one with an `rwait=` field.
    assert [s.frame for s in ann.samples] == [700, 1300]
    assert ann.client_ms_avg == 4.0 and ann.min_fps == 55 and ann.peak_objects == 320
    r_ann, r_bob = r.roster
    # Bob is judged by Ann's log alone, never his own.
    assert (r_bob.views, r_bob.freezes, r_bob.freeze_ms) == (1, 1, 600)
    assert (r_ann.freezes, r_ann.freeze_ms) == (0, 0)
    # The window's only wait was that NETSTALL, so no short stalls remain.
    assert (r_bob.stalls, r_bob.stall_ms) == (0, 0)
    assert (
        ann.pings[0].median_ms == 60
        and ann.pings[0].max_ms == 80
        and ann.pings[0].seconds == 30
    )


def test_no_matching_seed_gives_no_players():
    z = _zip({"Ann/ReleaseLog.txt.gz": _log(0, 111, peers="", stall_on=0)})
    assert parse_match_netstats(z, SEED).players == []


def _match_log(slot: int, lines: list[str]) -> str:
    return "\n".join(
        [
            f"[23:00:00] === Match start: map='m.map' mode=5 crcInterval=100 seed={SEED} logicFps=60 localSlot={slot} resumeTo=0 ===",
            "[23:00:00] ROSTER slot=0 name=Ann human template=2 color=0 start=0 team=0 ip=0.0.0.0:0",
            "[23:00:00] ROSTER slot=1 name=Bob human template=2 color=0 start=0 team=0 ip=0.0.0.1:0",
            "[23:00:00] ROSTER slot=2 name=Cat human template=2 color=0 start=0 team=-1 ip=0.0.0.2:0",
            *lines,
            "[23:00:59] === Match end: frame=2000 desync=0 ===",
        ]
    )


def _window(frame: int, stalls: str) -> str:
    return f"[23:00:10] NETSTAT frame={frame} ra=20 fps=60 router=0 lat=0/9 links=[] {stalls} hitch=0/max0 rreq=0/0 peers=[] client=3.0/max10 logic=1.0/max5 objs=300"


def test_blame_is_the_median_of_the_other_logs_and_ignores_your_own():
    # Cat uploaded nothing; Ann and Bob both waited on her. Ann's own log
    # blames Bob - the view of a player whose link is the problem - but it is
    # the only one, and Bob's blame needs his *other* views.
    ann = _match_log(
        0,
        [
            "[23:00:15] NETSTALL frame=800 waited=9000ms on=0x04",
            "[23:00:16] NETSTALL frame=900 waited=3000ms on=0x02",
            _window(1000, "stall=2/12000ms/max9000 on=[2:1 1:1]"),
        ],
    )
    bob = _match_log(
        1,
        [
            "[23:00:15] NETSTALL frame=800 waited=8000ms on=0x04",
            _window(1000, "stall=1/8000ms/max8000 on=[2:1]"),
        ],
    )
    r = parse_match_netstats(
        _zip({"Ann/ReleaseLog.txt.gz": ann, "Bob/ReleaseLog.txt.gz": bob}), SEED
    )
    cat = next(s for s in r.roster if s.slot == 2)
    assert (cat.name, cat.team, cat.has_logs, cat.views) == ("Cat", -1, False, 2)
    assert (cat.freezes, cat.freeze_ms) == (1, 8500)
    bob_slot = next(s for s in r.roster if s.slot == 1)
    assert (bob_slot.views, bob_slot.freeze_ms) == (1, 3000)


def test_short_stalls_are_the_window_minus_its_freezes():
    ann = _match_log(
        0,
        [
            "[23:00:15] NETSTALL frame=800 waited=1000ms on=0x02",
            # 1 long wait on Bob plus 40 short ones on Bob and 10 on Cat.
            _window(1000, "stall=51/2000ms/max1000 on=[1:41 2:10]"),
        ],
    )
    r = parse_match_netstats(_zip({"Ann/ReleaseLog.txt.gz": ann}), SEED)
    bob = next(s for s in r.roster if s.slot == 1)
    cat = next(s for s in r.roster if s.slot == 2)
    assert (bob.stalls, bob.stall_ms) == (40, 800)
    assert (cat.stalls, cat.stall_ms) == (10, 200)
    assert bob.freezes == 1


def _slot(i: int, name: str, freeze_ms: int = 0, stall_ms: int = 0) -> RosterSlot:
    return RosterSlot(
        slot=i,
        name=name,
        has_logs=True,
        views=3,
        freezes=freeze_ms // 1000,
        freeze_ms=freeze_ms,
        stalls=stall_ms // 30,
        stall_ms=stall_ms,
    )


def test_stutter_and_connection_are_flagged_separately():
    # 951595898's medians: Neo stutters, Pancake's link keeps dropping.
    s = NetstatsSummary(
        roster=[
            _slot(0, "Pancake", freeze_ms=24000, stall_ms=48000),
            _slot(1, "Neo", freeze_ms=7900, stall_ms=163000),
            _slot(2, "Modus", freeze_ms=4400, stall_ms=1000),
            _slot(3, "OneThree111", freeze_ms=7900, stall_ms=6000),
        ]
    )
    flags = lag_flags(s, 17.6)
    assert flags.potato is not None and flags.potato.name == "Neo"
    assert flags.connection is not None and flags.connection.name == "Pancake"
    assert flags.connection.wait_ms == 24000 and flags.connection.count == 24


def test_no_flag_when_waiting_is_shared_or_minor():
    shared = [
        _slot(i, n, freeze_ms=ms)
        for i, (n, ms) in enumerate(
            {"Ann": 12000, "Bob": 9600, "Cat": 7500, "Dan": 7400}.items()
        )
    ]
    assert lag_flags(NetstatsSummary(roster=shared), 41).connection is None
    minor = [_slot(0, "Ann", stall_ms=20000), _slot(1, "Bob")]
    assert lag_flags(NetstatsSummary(roster=minor), 10).potato is None
    # 40 s of stutter over a 20 min game is under 3 s/min.
    slow = [_slot(0, "Ann", stall_ms=40000), _slot(1, "Bob")]
    assert lag_flags(NetstatsSummary(roster=slow), 20).potato is None


def test_a_lone_log_cannot_flag_anyone():
    lone = [
        _slot(0, "Ann", freeze_ms=30000).model_copy(update={"has_logs": False}),
        _slot(1, "Bob").model_copy(update={"views": 0}),
        _slot(2, "Cat", freeze_ms=0).model_copy(update={"has_logs": False}),
    ]
    assert lag_flags(NetstatsSummary(roster=lone), 10).connection is None


def test_thresholds_come_from_the_environment(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("POTATO_MIN_SHARE", "0.9")
    monkeypatch.setenv("CONNECTION_MIN_MS", "1")
    assert FlagThresholds.from_env("POTATO", POTATO_DEFAULTS).min_share == 0.9
    assert FlagThresholds.from_env("CONNECTION", CONNECTION_DEFAULTS).min_ms == 1
