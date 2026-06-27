"""Ingest user-uploaded maps: a .tga + .map pair, or a zip of map folders.

Reuses the conversion / upload / parse helpers in `missing_maps`. A two-phase
flow is driven by the `commit` flag in the route: preview (convert tga->webp and
return the image, write nothing) then commit (upload the assets to S3 and save
the parsed geometry to MapData).
"""

from __future__ import annotations

import base64
import zipfile
from dataclasses import dataclass
from io import BytesIO

import structlog

from . import missing_maps
from .api_types import MapUploadItem
from .db_utils import ReplayManager

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class MapUpload:
    """One map to ingest: its base name plus the raw .tga and .map bytes."""

    base_name: str
    tga: bytes
    map_file: bytes


def _base_name(filename: str) -> str:
    """Strip any directory path and a .tga/.map extension."""
    name = filename.replace("\\", "/").rsplit("/", 1)[-1]
    for ext in (".tga", ".map"):
        if name.lower().endswith(ext):
            return name[: -len(ext)]
    return name


def maps_from_pair(
    tga_name: str, tga: bytes, map_name: str, map_file: bytes
) -> list[MapUpload]:
    """A single map from an uploaded .tga + .map pair."""
    base = _base_name(map_name) or _base_name(tga_name)
    return [MapUpload(base_name=base, tga=tga, map_file=map_file)]


@dataclass
class _DirFiles:
    tga: bytes | None = None
    map_file: bytes | None = None
    map_name: str = ""


def maps_from_zip(zip_bytes: bytes) -> list[MapUpload]:
    """One map per folder that holds both a .map and a .tga; other files ignored."""
    dirs: dict[str, _DirFiles] = {}
    with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            raw = info.filename.replace("\\", "/")
            folder = raw.rsplit("/", 1)[0] if "/" in raw else ""
            lower = raw.lower()
            if lower.endswith(".tga"):
                dirs.setdefault(folder, _DirFiles()).tga = zf.read(info)
            elif lower.endswith(".map"):
                entry = dirs.setdefault(folder, _DirFiles())
                entry.map_file = zf.read(info)
                entry.map_name = raw
    maps: list[MapUpload] = []
    for folder, files in dirs.items():
        if files.tga is None or files.map_file is None:
            continue
        base = _base_name(files.map_name) or folder.rsplit("/", 1)[-1] or "map"
        maps.append(MapUpload(base_name=base, tga=files.tga, map_file=files.map_file))
    maps.sort(key=lambda m: m.base_name.lower())
    return maps


def _data_url(webp: bytes) -> str:
    return "data:image/webp;base64," + base64.b64encode(webp).decode("ascii")


def process(
    uploads: list[MapUpload],
    commit: bool,
    replay_manager: ReplayManager,
    is_admin: bool,
) -> tuple[list[MapUploadItem], list[str]]:
    """Convert (and, when committing, save) each map. Returns (items, errors).

    Preview (commit=False): convert tga->webp, parse geometry if the mapparse
    binary is available, and return the image — no writes. Commit: also upload
    the .tga/.webp/.map to S3 and save the geometry to MapData when parsed.
    Overwriting a map that already exists requires admin; non-admin overwrite
    attempts are skipped and reported.
    """
    items: list[MapUploadItem] = []
    errors: list[str] = []
    parse_ok = missing_maps.mapparse_available()
    push_ok = missing_maps.cncstats_push_enabled()
    for u in uploads:
        try:
            webp = missing_maps.tga_to_webp(u.tga)
        except Exception as e:
            errors.append(f"{u.base_name}: could not convert image ({e})")
            continue
        crc = missing_maps.compute_map_crc_hex(u.map_file)
        player_count: int | None = None
        payload = None
        if parse_ok:
            try:
                payload = missing_maps.parse_map_file(u.map_file)
                player_count = len(payload.player_starts)
            except Exception as e:
                logger.warning(
                    "map geometry parse failed", base_name=u.base_name, error=repr(e)
                )
        already_exists = missing_maps.s3_webp_exists(u.base_name)
        blocked = commit and already_exists and not is_admin
        if blocked:
            errors.append(f"{u.base_name}: already exists — overwrite requires admin")
        saved = False
        pushed = False
        if commit and not blocked:
            missing_maps.upload_map_assets(u.base_name, u.tga, webp, u.map_file)
            if payload is not None:
                replay_manager.save_map_data(u.base_name, payload, crc=crc)
            saved = True
            if push_ok:
                try:
                    missing_maps.push_map_to_cncstats(
                        u.map_file, tga=u.tga, map_name=u.base_name
                    )
                    pushed = True
                except Exception as e:
                    # Best-effort: the map is saved either way, just not on cncstats.
                    errors.append(
                        f"{u.base_name}: saved but cncstats push failed ({e})"
                    )
        items.append(
            MapUploadItem(
                base_name=u.base_name,
                # Image only in preview; the commit response stays small.
                image=None if commit else _data_url(webp),
                player_count=player_count,
                already_exists=already_exists,
                saved=saved,
                crc=crc,
                pushed_to_cncstats=pushed,
            )
        )
    return items, errors
