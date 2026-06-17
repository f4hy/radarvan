"""SAGE map-CRC computation and cncstats push gating."""

import pytest

from radarvan import map_upload, missing_maps
from radarvan.cncstats_client import CncstatsClient
from radarvan.map_upload import MapUpload


def _sage_reference(data: bytes) -> int:
    """Independent reimplementation of the engine CRC, for cross-checking."""
    crc = 0
    for b in data:
        hibit = (crc >> 31) & 1
        crc = ((crc << 1) + b + hibit) & 0xFFFFFFFF
    return crc


def test_compute_map_crc_matches_reference() -> None:
    for sample in (b"", b"\x00", b"\x01", b"\x01\x01", b"the quick brown map"):
        assert missing_maps.compute_map_crc(sample) == _sage_reference(sample)


def test_compute_map_crc_hex_is_uppercase_8_hex() -> None:
    h = missing_maps.compute_map_crc_hex(b"the quick brown map")
    assert len(h) == 8
    assert h == h.upper()
    assert int(h, 16) == missing_maps.compute_map_crc(b"the quick brown map")


def test_compute_map_crc_known_vector() -> None:
    # 0 -> rotate(+byte): 0x01 then 0x01 == 3.
    assert missing_maps.compute_map_crc(b"\x01\x01") == 3


def test_client_add_map_requires_key() -> None:
    assert CncstatsClient(map_api_key=None).map_push_enabled is False
    assert CncstatsClient(map_api_key="k").map_push_enabled is True
    with pytest.raises(RuntimeError):
        CncstatsClient(map_api_key=None).add_map(123, "map", b"data")


def test_client_parse_replay_requires_token() -> None:
    with pytest.raises(RuntimeError):
        CncstatsClient(parse_token=None).parse_replay(b"replay-bytes")


def _stub_convert(monkeypatch: pytest.MonkeyPatch) -> list[tuple]:
    uploaded: list[tuple] = []
    monkeypatch.setattr(missing_maps, "tga_to_webp", lambda b: b"webp")
    monkeypatch.setattr(missing_maps, "mapparse_available", lambda: False)
    monkeypatch.setattr(missing_maps, "s3_webp_exists", lambda name: False)
    monkeypatch.setattr(missing_maps, "cncstats_push_enabled", lambda: False)
    monkeypatch.setattr(
        missing_maps, "upload_map_assets", lambda *a, **k: uploaded.append(a)
    )
    return uploaded


def test_upload_item_carries_crc(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_convert(monkeypatch)
    uploads = [MapUpload(base_name="Brand New", tga=b"t", map_file=b"\x01\x01")]
    items, errors = map_upload.process(uploads, True, object(), is_admin=False)  # type: ignore[arg-type]
    assert errors == []
    assert items[0].crc == missing_maps.compute_map_crc_hex(b"\x01\x01")
    assert items[0].pushed_to_cncstats is False  # push disabled (no key)


def test_upload_pushes_to_cncstats_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_convert(monkeypatch)
    monkeypatch.setattr(missing_maps, "cncstats_push_enabled", lambda: True)
    pushed: list[tuple] = []
    monkeypatch.setattr(
        missing_maps,
        "push_map_to_cncstats",
        lambda map_bytes, **k: pushed.append((map_bytes, k))
        or missing_maps.compute_map_crc_hex(map_bytes),
    )
    uploads = [MapUpload(base_name="Brand New", tga=b"t", map_file=b"\x01\x01")]
    items, errors = map_upload.process(uploads, True, object(), is_admin=False)  # type: ignore[arg-type]
    assert errors == []
    assert items[0].pushed_to_cncstats is True
    assert pushed[0][0] == b"\x01\x01"
    assert pushed[0][1] == {"tga": b"t", "map_name": "Brand New"}
