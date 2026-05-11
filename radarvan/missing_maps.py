"""Find map images we are missing data for and fetch them from cncstats.

cncstats exposes a `get_map?crc=<decimal>` endpoint that returns a zip with the
`.tga` preview image and the `.map` file. Each parsed replay's header has the
map CRC as a hex string, so for any match we already have we can derive the CRC
of its map. This module:

  1. Lists maps referenced by matches that have no `MapData` row yet.
  2. Extracts the map CRC from a sample replay JSON for each missing map.
  3. Downloads the cncstats zip, extracts the `.tga` and `.map`.
  4. Converts the `.tga` to `.webp` and uploads all three to S3.

The `.map` is uploaded but not parsed here — the geometry payload is produced
by the separate `mapparse` binary which is not run from this module.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image
from sqlalchemy import func, select

from .api_types import MapDataPayload
from .cncstats_model.zhreplay import EnhancedReplayV2
from .db import MapData, Match, ParsedReplayJson
from .db_utils import ReplayManager
from . import replay_files

logger = logging.getLogger(__name__)


CNCSTATS_GET_MAP_URL = "http://cncstats.computersrfun.org:8080/get_map"
S3_MAPS_PREFIX = f"{replay_files.s3_root}maps/"
# The mapparse binary lives at the repo root. Override with MAPPARSE_BIN if elsewhere.
MAPPARSE_BIN = os.environ.get("MAPPARSE_BIN", "./mapparse")


@dataclass(frozen=True)
class MissingMap:
    """A map referenced by matches that has no MapData row."""

    map_name: str  # basename as it appears in Match.map (post split)
    sample_match_id: int  # one match_id known to be on this map
    map_crc_hex: str | None = None  # filled in once we read the JSON


@dataclass(frozen=True)
class FetchedMap:
    """Result of pulling a single map from cncstats."""

    base_name: str  # filename inside the zip, without extension
    tga_s3_uri: str
    webp_s3_uri: str
    map_s3_uri: str


def _basename(map_path: str) -> str:
    """Return the basename of the map path (last `/`-separated component, lowercased)."""
    return replay_files.map_basename(map_path).lower()


def list_missing_maps(replay_manager: ReplayManager) -> list[MissingMap]:
    """Return maps referenced in `Match.map` that have no `MapData` row.

    For each missing map, returns one representative `match_id` so callers
    can fetch the parsed JSON to extract the MapCRC.
    """
    # Existing map_data names (case-insensitive set).
    existing = {
        name.lower()
        for name in replay_manager.session.scalars(select(MapData.map_name)).all()
    }

    # One sample match per distinct Match.map. Use MIN(match_id) so the result
    # is stable and we pick any one match.
    rows = replay_manager.session.execute(
        select(Match.map, func.min(Match.match_id))
        .where(Match.map != "")
        .group_by(Match.map)
    ).all()

    missing: list[MissingMap] = []
    seen_basenames: set[str] = set()
    for raw_path, match_id in rows:
        base = _basename(raw_path or "")
        if not base or base == "unknown":
            continue
        # Strip a trailing .map extension before comparing — MapData entries
        # are stored without extension in some cases.
        compare = base.removesuffix(".map")
        if compare in existing or base in existing:
            continue
        if compare in seen_basenames:
            continue
        seen_basenames.add(compare)
        missing.append(
            MissingMap(map_name=replay_files.map_basename(raw_path), sample_match_id=match_id)
        )
    missing.sort(key=lambda m: m.map_name.lower())
    return missing


def get_map_crc_from_match(
    match_id: int, replay_manager: ReplayManager
) -> str | None:
    """Return the hex MapCRC for the given match, by reading its parsed JSON from S3."""
    json_uri = replay_manager.session.scalar(
        select(ParsedReplayJson.json_s3_uri)
        .where(ParsedReplayJson.match_id == match_id)
        .limit(1)
    )
    if not json_uri:
        logger.warning("No parsed JSON for match %s", match_id)
        return None
    fs = replay_files.get_fs()
    try:
        data = fs.read_text(json_uri)
    except Exception as e:
        logger.warning("Could not read %s: %s", json_uri, e)
        return None
    replay = EnhancedReplayV2.model_validate_json(data)
    return replay.header.metadata.map_crc


def list_missing_maps_with_crc(
    replay_manager: ReplayManager, limit: int | None = None
) -> list[MissingMap]:
    """Return missing maps with their MapCRC (hex) populated from a sample replay.

    Reads the parsed JSON from S3 for each sample match. Skips maps where the
    CRC could not be determined.
    """
    out: list[MissingMap] = []
    for m in list_missing_maps(replay_manager):
        crc = get_map_crc_from_match(m.sample_match_id, replay_manager)
        if not crc:
            continue
        out.append(
            MissingMap(
                map_name=m.map_name,
                sample_match_id=m.sample_match_id,
                map_crc_hex=crc,
            )
        )
        if limit is not None and len(out) >= limit:
            break
    return out


def hex_crc_to_decimal(hex_crc: str) -> int:
    """cncstats CRC is hex in the replay JSON; the API expects a decimal int."""
    return int(hex_crc, 16)


def fetch_map_zip(hex_crc: str) -> bytes:
    """Download the cncstats map zip for the given hex CRC. Raises on HTTP error."""
    decimal = hex_crc_to_decimal(hex_crc)
    url = f"{CNCSTATS_GET_MAP_URL}?crc={decimal}"
    logger.info("Fetching cncstats map zip from %s", url)
    resp = httpx.get(url, timeout=60.0, follow_redirects=True)
    resp.raise_for_status()
    return resp.content


@dataclass(frozen=True)
class ExtractedMap:
    base_name: str  # filename without extension
    tga: bytes
    map_file: bytes


def extract_map_zip(zip_bytes: bytes) -> ExtractedMap:
    """Pull the .tga and .map out of a cncstats zip.

    The zip contains `<name>.map` and `<name>.tga` at the top level.
    """
    tga: bytes | None = None
    map_file: bytes | None = None
    base_name: str | None = None
    with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
        for info in zf.infolist():
            name = info.filename
            lower = name.lower()
            if lower.endswith(".tga"):
                tga = zf.read(info)
                base_name = name[: -len(".tga")]
            elif lower.endswith(".map"):
                map_file = zf.read(info)
                if base_name is None:
                    base_name = name[: -len(".map")]
    if tga is None or map_file is None or base_name is None:
        raise ValueError(
            f"Zip missing .tga or .map files; entries={[i.filename for i in zipfile.ZipFile(BytesIO(zip_bytes)).infolist()]}"
        )
    return ExtractedMap(base_name=base_name, tga=tga, map_file=map_file)


def tga_to_webp(tga_bytes: bytes, quality: int = 80) -> bytes:
    """Convert a TGA image to WebP. Mirrors the legacy `cwebp -q 80` output."""
    img = Image.open(BytesIO(tga_bytes))
    out = BytesIO()
    img.save(out, format="WEBP", quality=quality, method=6)
    return out.getvalue()


def s3_uri_for(base_name: str, ext: str) -> str:
    return f"{S3_MAPS_PREFIX}{base_name}.{ext}"


def upload_map_assets(
    base_name: str, tga: bytes, webp: bytes, map_file: bytes
) -> FetchedMap:
    """Upload the three map artefacts to S3 and return their URIs."""
    fs = replay_files.get_fs()
    tga_uri = s3_uri_for(base_name, "tga")
    webp_uri = s3_uri_for(base_name, "webp")
    map_uri = s3_uri_for(base_name, "map")
    fs.write_bytes(tga_uri, tga)
    fs.write_bytes(webp_uri, webp)
    fs.write_bytes(map_uri, map_file)
    logger.info("Uploaded map assets for %s to %s", base_name, S3_MAPS_PREFIX)
    return FetchedMap(
        base_name=base_name,
        tga_s3_uri=tga_uri,
        webp_s3_uri=webp_uri,
        map_s3_uri=map_uri,
    )


def fetch_and_upload(
    missing: MissingMap,
    replay_manager: ReplayManager | None = None,
    parse_and_save: bool = False,
) -> FetchedMap | None:
    """Run the full cncstats fetch for one missing map. Returns None on failure.

    If `parse_and_save` is True and `replay_manager` is provided, also parses
    the .map via the local mapparse binary and saves the geometry to MapData.
    """
    if not missing.map_crc_hex:
        logger.warning("No CRC for %s; skipping", missing.map_name)
        return None
    try:
        zip_bytes = fetch_map_zip(missing.map_crc_hex)
        extracted = extract_map_zip(zip_bytes)
        webp = tga_to_webp(extracted.tga)
        fetched = upload_map_assets(
            extracted.base_name, extracted.tga, webp, extracted.map_file
        )
        if parse_and_save and replay_manager is not None and mapparse_available():
            payload = parse_map_file(extracted.map_file)
            replay_manager.save_map_data(extracted.base_name, payload)
        return fetched
    except Exception as e:
        logger.warning("Failed to fetch %s (crc=%s): %s", missing.map_name, missing.map_crc_hex, e)
        return None


def mapparse_available() -> bool:
    """Return True if the mapparse binary is reachable on this host."""
    if os.path.isfile(MAPPARSE_BIN) and os.access(MAPPARSE_BIN, os.X_OK):
        return True
    return shutil.which(MAPPARSE_BIN) is not None


def parse_map_file(map_bytes: bytes) -> MapDataPayload:
    """Run the local `mapparse -json` binary on map_bytes and return the payload.

    Writes to a temp file because mapparse reads from disk, not stdin.
    """
    if not mapparse_available():
        raise FileNotFoundError(
            f"mapparse binary not found at {MAPPARSE_BIN!r}; "
            f"set MAPPARSE_BIN to its location"
        )
    with tempfile.NamedTemporaryFile(suffix=".map", delete=False) as tf:
        tf.write(map_bytes)
        tmp_path = tf.name
    try:
        result = subprocess.run(  # noqa: S603 — MAPPARSE_BIN and tmp_path are operator-controlled
            [MAPPARSE_BIN, "-json", tmp_path],
            capture_output=True,
            check=True,
            timeout=60,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"mapparse failed (exit {e.returncode}): {e.stderr.decode(errors='replace')}"
        ) from e
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    return MapDataPayload.model_validate_json(result.stdout)


def fetch_and_upload_for_match(
    match_id: int,
    replay_manager: ReplayManager,
    parse_and_save: bool = True,
) -> tuple[FetchedMap, MapDataPayload | None]:
    """Fetch and upload the map for a single match by reading its JSON for the CRC.

    When `parse_and_save` is True and the mapparse binary is available, the
    .map file is also parsed and the resulting geometry payload is saved to
    `MapData` under the cncstats base name. Returns the upload result and the
    parsed payload (or None if parsing was skipped).

    Raises with a descriptive message if the JSON is missing, the CRC is unset,
    cncstats has no entry for the CRC, or the zip is malformed.
    """
    crc = get_map_crc_from_match(match_id, replay_manager)
    if not crc:
        raise ValueError(f"No MapCRC found for match {match_id}")
    zip_bytes = fetch_map_zip(crc)
    extracted = extract_map_zip(zip_bytes)
    webp = tga_to_webp(extracted.tga)
    fetched = upload_map_assets(
        extracted.base_name, extracted.tga, webp, extracted.map_file
    )
    payload: MapDataPayload | None = None
    if parse_and_save:
        if not mapparse_available():
            logger.warning(
                "mapparse not available; skipping geometry parse for %s",
                extracted.base_name,
            )
        else:
            payload = parse_map_file(extracted.map_file)
            replay_manager.save_map_data(extracted.base_name, payload)
            logger.info(
                "Saved MapData for %s (%d player_starts, %d supply, %d tech)",
                extracted.base_name,
                len(payload.player_starts),
                len(payload.supply),
                len(payload.tech),
            )
    return fetched, payload


def s3_webp_exists(base_name: str) -> bool:
    """Return True if a webp for this map name already lives in S3."""
    fs = replay_files.get_fs()
    return bool(fs.exists(s3_uri_for(base_name, "webp")))


def find_s3_webp(map_name: str) -> str | None:
    """Look up the S3 webp path for a map name (case-insensitive, w/ or w/o .map)."""
    fs = replay_files.get_fs()
    candidates = [
        map_name,
        map_name.removesuffix(".map"),
        map_name.lower(),
        map_name.lower().removesuffix(".map"),
    ]
    seen: set[str] = set()
    for c in candidates:
        if c in seen:
            continue
        seen.add(c)
        uri = s3_uri_for(c, "webp")
        try:
            if fs.exists(uri):
                return uri
        except Exception as e:
            logger.debug("fs.exists failed for %s: %s", uri, e)
            continue
    return None
