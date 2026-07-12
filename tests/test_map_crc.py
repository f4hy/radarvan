"""SAGE map-CRC computation and cncstats push gating."""

import pytest

import asyncio

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


class _FakeAsyncClient:
    """Records add_map_async calls and answers map_exists with a fixed value."""

    def __init__(self, exists: bool = False) -> None:
        self.calls: list[tuple[int, str, bytes, str | None]] = []
        self.exists = exists
        self.exists_checks: list[int] = []

    async def add_map_async(
        self, crc_decimal: int, file_type: str, data: bytes, *, map_name: str | None = None
    ) -> None:
        self.calls.append((crc_decimal, file_type, data, map_name))

    async def map_exists_async(self, crc_decimal: int) -> bool:
        self.exists_checks.append(crc_decimal)
        return self.exists


class _FakeFS:
    """Minimal fsspec stand-in for the stored .map / .tga reads."""

    def __init__(self, files: dict[str, bytes]) -> None:
        self.files = files

    def read_bytes(self, uri: str) -> bytes:
        return self.files[uri]

    def exists(self, uri: str) -> bool:
        return uri in self.files


def test_push_map_async_posts_map_and_preview(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeAsyncClient()
    monkeypatch.setattr(missing_maps.cncstats_client, "cncstats_client", lambda: fake)
    crc = asyncio.run(
        missing_maps.push_map_to_cncstats_async(b"\x01\x01", tga=b"t", map_name="X")
    )
    assert crc == missing_maps.compute_map_crc_hex(b"\x01\x01")
    crc_dec = missing_maps.hex_crc_to_decimal(crc)
    assert {c[1] for c in fake.calls} == {"map", "preview"}  # both assets pushed
    assert all(c[0] == crc_dec and c[3] == "X" for c in fake.calls)


def test_push_map_async_skips_preview_without_tga(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeAsyncClient()
    monkeypatch.setattr(missing_maps.cncstats_client, "cncstats_client", lambda: fake)
    asyncio.run(missing_maps.push_map_to_cncstats_async(b"\x01\x01", map_name="X"))
    assert [c[1] for c in fake.calls] == ["map"]  # no preview without a tga


def test_sync_skips_push_when_cncstats_has_it(monkeypatch: pytest.MonkeyPatch) -> None:
    # Known CRC already on cncstats: no push, and no S3 read at all.
    fake = _FakeAsyncClient(exists=True)
    monkeypatch.setattr(missing_maps.cncstats_client, "cncstats_client", lambda: fake)

    def _boom() -> object:
        raise AssertionError("should not read S3 when CRC is known and present")

    monkeypatch.setattr(missing_maps.replay_files, "get_fs", _boom)

    crc, pushed = asyncio.run(
        missing_maps.sync_stored_map_to_cncstats("X", crc_hint="DEADBEEF")
    )
    assert (crc, pushed) == ("DEADBEEF", False)
    assert fake.exists_checks == [missing_maps.hex_crc_to_decimal("DEADBEEF")]
    assert fake.calls == []  # nothing pushed


def test_sync_pushes_when_cncstats_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeAsyncClient(exists=False)
    monkeypatch.setattr(missing_maps.cncstats_client, "cncstats_client", lambda: fake)
    fs = _FakeFS(
        {
            missing_maps.s3_uri_for("X", "map"): b"\x01\x01",
            missing_maps.s3_uri_for("X", "tga"): b"tga",
        }
    )
    monkeypatch.setattr(missing_maps.replay_files, "get_fs", lambda: fs)

    crc, pushed = asyncio.run(missing_maps.sync_stored_map_to_cncstats("X"))
    assert pushed is True
    assert crc == missing_maps.compute_map_crc_hex(b"\x01\x01")
    assert {c[1] for c in fake.calls} == {"map", "preview"}


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


class _FakeSyncClient:
    """Blocking cncstats stand-in: records add_map calls, canned map_exists."""

    def __init__(self, exists: bool = False, push_enabled: bool = True) -> None:
        self.calls: list[tuple[int, str, bytes, str | None]] = []
        self.exists = exists
        self.exists_checks: list[int] = []
        self.map_push_enabled = push_enabled

    def map_exists(self, crc_decimal: int) -> bool:
        self.exists_checks.append(crc_decimal)
        return self.exists

    def add_map(
        self,
        crc_decimal: int,
        file_type: str,
        data: bytes,
        *,
        map_name: str | None = None,
    ) -> None:
        self.calls.append((crc_decimal, file_type, data, map_name))


class _FakeManager:
    """Records CRC write-backs; stands in for ReplayManager."""

    def __init__(self) -> None:
        self.written: list[tuple[str, str]] = []

    def set_map_crc(self, map_name: str, crc: str) -> bool:
        self.written.append((map_name, crc))
        return True


def test_resolve_map_crc_falls_back_to_the_map_we_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Never played, no stored CRC: the .map bytes in S3 are the only source.
    monkeypatch.setattr(missing_maps, "crc_for_map", lambda name, rm: None)
    fs = _FakeFS({missing_maps.s3_uri_for("Brand New", "map"): b"\x01\x01"})
    monkeypatch.setattr(missing_maps.replay_files, "get_fs", lambda: fs)

    manager = _FakeManager()
    crc = missing_maps.resolve_map_crc("Brand New", manager)  # type: ignore[arg-type]
    assert crc == missing_maps.compute_map_crc_hex(b"\x01\x01")
    assert manager.written == [("Brand New", crc)]  # written back to MapData


def test_resolve_map_crc_is_none_when_we_cannot_supply_the_map(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(missing_maps, "crc_for_map", lambda name, rm: None)
    monkeypatch.setattr(missing_maps.replay_files, "get_fs", lambda: _FakeFS({}))
    manager = _FakeManager()
    assert missing_maps.resolve_map_crc("Nowhere", manager) is None  # type: ignore[arg-type]
    assert manager.written == []


def test_blocking_sync_skips_push_when_cncstats_has_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeSyncClient(exists=True)
    monkeypatch.setattr(missing_maps.cncstats_client, "cncstats_client", lambda: fake)

    def _boom() -> object:
        raise AssertionError("should not read S3 when CRC is known and present")

    monkeypatch.setattr(missing_maps.replay_files, "get_fs", _boom)

    synced = missing_maps.sync_stored_map_to_cncstats_blocking("X", "DEADBEEF")
    assert synced is not None
    assert (synced.crc_hex, synced.pushed) == ("DEADBEEF", False)
    assert fake.calls == []


def test_blocking_sync_pushes_map_and_preview(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeSyncClient(exists=False)
    monkeypatch.setattr(missing_maps.cncstats_client, "cncstats_client", lambda: fake)
    fs = _FakeFS(
        {
            missing_maps.s3_uri_for("X", "map"): b"\x01\x01",
            missing_maps.s3_uri_for("X", "tga"): b"tga",
        }
    )
    monkeypatch.setattr(missing_maps.replay_files, "get_fs", lambda: fs)

    synced = missing_maps.sync_stored_map_to_cncstats_blocking("X")
    assert synced is not None
    assert synced.pushed is True
    assert synced.pushed_preview is True
    assert synced.crc_hex == missing_maps.compute_map_crc_hex(b"\x01\x01")
    assert {c[1] for c in fake.calls} == {"map", "preview"}


def test_blocking_sync_returns_none_when_map_not_hosted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeSyncClient(exists=False)
    monkeypatch.setattr(missing_maps.cncstats_client, "cncstats_client", lambda: fake)
    monkeypatch.setattr(missing_maps.replay_files, "get_fs", lambda: _FakeFS({}))
    assert missing_maps.sync_stored_map_to_cncstats_blocking("X", "DEADBEEF") is None
    assert fake.calls == []
