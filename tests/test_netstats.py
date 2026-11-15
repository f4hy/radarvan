import gzip
import io
import zipfile

from radarvan.netstats import parse_match_netstats

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
    assert (bob.freezes_caused, bob.freeze_ms_caused) == (1, 600)
    assert ann.freezes_caused == 0
    assert (
        ann.pings[0].median_ms == 60
        and ann.pings[0].max_ms == 80
        and ann.pings[0].seconds == 30
    )


def test_no_matching_seed_gives_no_players():
    z = _zip({"Ann/ReleaseLog.txt.gz": _log(0, 111, peers="", stall_on=0)})
    assert parse_match_netstats(z, SEED).players == []
