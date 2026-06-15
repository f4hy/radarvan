"""Extraction of uploaded maps from a folder zip / a tga+map pair."""

import zipfile
from io import BytesIO

import pytest

from radarvan import map_upload, missing_maps
from radarvan.map_upload import MapUpload, maps_from_pair, maps_from_zip


def _zip(entries: dict[str, bytes]) -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


def test_maps_from_zip_one_per_folder_ignoring_extras() -> None:
    data = _zip(
        {
            "Alpha/Alpha.map": b"alpha-map",
            "Alpha/Alpha.tga": b"alpha-tga",
            "Alpha/readme.txt": b"ignored",  # extra file ignored
            "Beta/beta.map": b"beta-map",
            "Beta/beta.tga": b"beta-tga",
            "Gamma/gamma.map": b"gamma-map",  # no .tga -> skipped
        }
    )
    maps = maps_from_zip(data)
    assert [m.base_name for m in maps] == ["Alpha", "beta"]  # sorted, gamma dropped
    alpha = maps[0]
    assert alpha.tga == b"alpha-tga"
    assert alpha.map_file == b"alpha-map"


def test_maps_from_zip_skips_folder_missing_tga() -> None:
    data = _zip({"Solo/solo.map": b"m"})  # only a map, no tga
    assert maps_from_zip(data) == []


def test_maps_from_pair_uses_map_stem() -> None:
    maps = maps_from_pair("preview.tga", b"tga", "My Map.map", b"map")
    assert len(maps) == 1
    assert maps[0].base_name == "My Map"
    assert maps[0].tga == b"tga"
    assert maps[0].map_file == b"map"


def _stub_convert(monkeypatch: pytest.MonkeyPatch, exists: bool) -> list[tuple]:
    """Stub out conversion/parse/S3 so process() can be unit-tested. Returns the
    list that captures upload_map_assets calls."""
    uploaded: list[tuple] = []
    monkeypatch.setattr(missing_maps, "tga_to_webp", lambda b: b"webp")
    monkeypatch.setattr(missing_maps, "mapparse_available", lambda: False)
    monkeypatch.setattr(missing_maps, "s3_webp_exists", lambda name: exists)
    monkeypatch.setattr(
        missing_maps, "upload_map_assets", lambda *a, **k: uploaded.append(a)
    )
    return uploaded


def test_overwrite_blocked_for_non_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    uploaded = _stub_convert(monkeypatch, exists=True)
    uploads = [MapUpload(base_name="Existing", tga=b"t", map_file=b"m")]

    items, errors = map_upload.process(uploads, True, object(), is_admin=False)  # type: ignore[arg-type]
    assert uploaded == []  # nothing written
    assert items[0].saved is False
    assert items[0].already_exists is True
    assert any("admin" in e for e in errors)


def test_admin_can_overwrite(monkeypatch: pytest.MonkeyPatch) -> None:
    uploaded = _stub_convert(monkeypatch, exists=True)
    uploads = [MapUpload(base_name="Existing", tga=b"t", map_file=b"m")]

    items, errors = map_upload.process(uploads, True, object(), is_admin=True)  # type: ignore[arg-type]
    assert len(uploaded) == 1
    assert items[0].saved is True
    assert errors == []


def test_non_admin_can_save_new_map(monkeypatch: pytest.MonkeyPatch) -> None:
    uploaded = _stub_convert(monkeypatch, exists=False)
    uploads = [MapUpload(base_name="Brand New", tga=b"t", map_file=b"m")]

    items, errors = map_upload.process(uploads, True, object(), is_admin=False)  # type: ignore[arg-type]
    assert len(uploaded) == 1
    assert items[0].saved is True
    assert errors == []
