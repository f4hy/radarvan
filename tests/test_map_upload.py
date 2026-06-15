"""Extraction of uploaded maps from a folder zip / a tga+map pair."""

import zipfile
from io import BytesIO

from radarvan.map_upload import maps_from_pair, maps_from_zip


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
