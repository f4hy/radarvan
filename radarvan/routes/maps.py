"""Map stats, geometry, render, and image endpoints."""

import os
import re

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import FileResponse, RedirectResponse

from .. import map_render as map_render_module
from .. import map_stats as map_stats_module
from .. import missing_maps as missing_maps_module
from .. import replay_files
from ..api_types import (
    FetchMissingMapResult,
    FetchMissingMapsResponse,
    MapDataPayload,
    MapMatchCount,
    MapRenderRequest,
    MapStatsResponse,
    MapsByPlayerCount,
    MapSummaryRequest,
    MissingMapInfo,
)
from ..cache import competitive_matches, sorted_deduped_matches
from ..db_utils import ReplayManager
from ..dependencies import cache_short, get_replay_manager

router = APIRouter()

# Routes that must be reachable without an API key (e.g. <img src> loads, which
# cannot send the X-API-Key header). Included without auth deps in main.py.
public_router = APIRouter()

# Map images are static. Presign for the S3 max (7 days) and let browsers cache
# the redirect — max-age must stay under the presign TTL. We keep the cache to
# 1h (well under the 7-day presign) so that if the deployment ever runs on
# temporary/STS credentials — which silently cap the presign at the credential
# lifetime — a cached redirect is unlikely to outlive its presigned URL.
_MAP_IMAGE_PRESIGN_TTL = 7 * 24 * 3600
_MAP_IMAGE_CACHE_MAX_AGE = 3600


@router.get("/api/map_stats/", dependencies=[Depends(cache_short)])
def get_map_stats(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> MapStatsResponse:
    """Get player and general win rates grouped by map."""
    games = competitive_matches(replay_manager)
    return map_stats_module.get_map_stats(list(games.values()))


@router.post("/api/map_summary/")
def get_map_summary(
    request: MapSummaryRequest,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> str:
    """Return a pre-game summary: map history, team h2h, and per-player records."""
    games = competitive_matches(replay_manager)
    summary = map_stats_module.map_summary(
        list(games.values()), request.map_name.replace(".map", ""), request.players
    )
    return map_stats_module.format_map_summary(summary)


@router.get("/api/map_match_counts", dependencies=[Depends(cache_short)])
def get_map_match_counts(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> list[MapMatchCount]:
    """List every map that appears in our match history, with its match count.

    Sorted by match count descending.
    """
    games = sorted_deduped_matches(replay_manager)
    counts: dict[str, int] = {}
    for m in games.values():
        counts[m.map] = counts.get(m.map, 0) + 1
    return [
        MapMatchCount(map=name, match_count=count)
        for name, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    ]


@router.get("/api/maps_by_player_count", dependencies=[Depends(cache_short)])
def get_maps_by_player_count(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> list[MapsByPlayerCount]:
    """Return all maps grouped by number of player starting positions."""
    grouped = replay_manager.list_maps_by_player_count()
    return [MapsByPlayerCount(player_count=k, maps=v) for k, v in grouped.items()]


@router.post("/api/map_data/{map_name}")
def save_map_data(
    map_name: str,
    payload: MapDataPayload,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> MapDataPayload:
    replay_manager.save_map_data(map_name, payload)
    return payload


@router.get("/api/map_data/{map_name}")
def get_map_data(
    map_name: str,
    response: Response,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> MapDataPayload:
    result = replay_manager.get_map_data(map_name)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No map data for '{map_name}'")
    response.headers["Cache-Control"] = "private, max-age=86400"
    return result


@router.get("/api/missing_maps")
def list_missing_maps_endpoint(
    limit: int | None = None,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> list[MissingMapInfo]:
    """Maps referenced by matches that have no MapData row, with their CRC."""
    missing = missing_maps_module.list_missing_maps_with_crc(
        replay_manager, limit=limit
    )
    return [
        MissingMapInfo(
            map_name=m.map_name,
            sample_match_id=m.sample_match_id,
            map_crc_hex=m.map_crc_hex,
        )
        for m in missing
    ]


@router.post("/api/fetch_map_for_match/{match_id}")
def fetch_map_for_match(
    match_id: int,
    parse_map: bool = True,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> FetchMissingMapResult:
    """Fetch the cncstats map for a single match's MapCRC and upload to S3.

    When `parse_map` is true and the local mapparse binary is available, also
    parse the .map and store the geometry payload in `MapData`.
    """
    try:
        fetched, payload = missing_maps_module.fetch_and_upload_for_match(
            match_id, replay_manager, parse_and_save=parse_map
        )
    except Exception as e:
        return FetchMissingMapResult(map_name=str(match_id), error=str(e))
    return FetchMissingMapResult(
        map_name=fetched.base_name,
        base_name=fetched.base_name,
        tga_s3_uri=fetched.tga_s3_uri,
        webp_s3_uri=fetched.webp_s3_uri,
        map_s3_uri=fetched.map_s3_uri,
        map_data_saved=payload is not None,
    )


@router.post("/api/fetch_missing_maps")
def fetch_missing_maps(
    max_to_update: int = 10,
    parse_map: bool = True,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> FetchMissingMapsResponse:
    """Pull up to `max_to_update` missing maps from cncstats and upload to S3.

    When `parse_map` is true and the local mapparse binary is available, the
    .map file is also parsed and saved to MapData.
    """
    missing = missing_maps_module.list_missing_maps_with_crc(
        replay_manager, limit=max_to_update
    )
    results: list[FetchMissingMapResult] = []
    fetched = 0
    for m in missing:
        try:
            result = missing_maps_module.fetch_and_upload(
                m, replay_manager=replay_manager, parse_and_save=parse_map
            )
        except Exception as e:
            results.append(FetchMissingMapResult(map_name=m.map_name, error=str(e)))
            continue
        if result is None:
            results.append(
                FetchMissingMapResult(map_name=m.map_name, error="fetch failed")
            )
            continue
        fetched += 1
        results.append(
            FetchMissingMapResult(
                map_name=m.map_name,
                base_name=result.base_name,
                tga_s3_uri=result.tga_s3_uri,
                webp_s3_uri=result.webp_s3_uri,
                map_s3_uri=result.map_s3_uri,
                map_data_saved=parse_map and missing_maps_module.mapparse_available(),
            )
        )
    return FetchMissingMapsResponse(
        requested=len(missing), fetched=fetched, results=results
    )


_MAPS_DIR = "dist/maps"


def _map_match_key(name: str) -> str:
    """Alphanumeric-lowercase key so spaces, underscores, brackets, and case
    don't block matching (e.g. `[RANK] Territorial Dispute ZH v1` vs the bundled
    `userdata_maps_[rank] territorial dispute zh v1_...webp`)."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _find_dist_map_path(map_name: str) -> str | None:
    """Resolve a map name to a bundled webp in dist/maps, or None.

    Tries exact filenames first, then a normalized exact match, then a
    normalized substring match (bundled filenames carry prefixes that embed the
    map name, e.g. `userdata_maps_<name>_<name>.webp`).
    """
    base = map_name.removesuffix(".map")
    for candidate in (f"{_MAPS_DIR}/{base}.webp", f"{_MAPS_DIR}/{map_name}.webp"):
        if os.path.exists(candidate):
            return candidate
    if not os.path.isdir(_MAPS_DIR):
        return None
    needle = _map_match_key(base)
    if not needle:
        return None
    webps = [f for f in os.listdir(_MAPS_DIR) if f.endswith(".webp")]
    for fname in webps:
        if _map_match_key(fname.removesuffix(".webp")) == needle:
            return os.path.join(_MAPS_DIR, fname)
    for fname in webps:
        if needle in _map_match_key(fname.removesuffix(".webp")):
            return os.path.join(_MAPS_DIR, fname)
    return None


def _load_map_image_bytes(map_name: str) -> bytes:
    s3_uri = missing_maps_module.find_s3_webp(map_name)
    if s3_uri is not None:
        fs = replay_files.get_fs()
        data: bytes = fs.read_bytes(s3_uri)
        return data
    path = _find_dist_map_path(map_name)
    if path is not None:
        with open(path, "rb") as f:
            return f.read()
    raise HTTPException(status_code=404, detail=f"No image for map '{map_name}'")


@router.post("/api/map_render", response_model=None)
def render_map_with_players(
    request: MapRenderRequest,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> Response:
    """Render a map image with player positions (name, general, team color) baked in."""
    canonical = replay_manager.resolve_map_name(request.map_name)
    if canonical is None:
        raise HTTPException(
            status_code=404, detail=f"No map data for '{request.map_name}'"
        )
    map_data = replay_manager.get_map_data(canonical)
    if map_data is None:
        raise HTTPException(
            status_code=404, detail=f"No map data for '{request.map_name}'"
        )
    image_bytes = _load_map_image_bytes(canonical)
    png = map_render_module.render_map(image_bytes, map_data, request.players)
    base = canonical.removesuffix(".map").split("/")[-1]
    return Response(
        content=png,
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="{base}.png"'},
    )


@public_router.get("/api/map_image/{map_name}", response_model=None)
def get_map_image(map_name: str) -> RedirectResponse | FileResponse:
    """Return the WebP for a map, preferring S3 (dynamic) over public/maps (legacy).

    Strips a trailing `.map` extension and tries case-insensitive variants in S3.
    Falls back to the bundled `dist/maps/<name>.webp` for legacy maps that
    haven't been migrated yet.
    """
    # Map images are static, so cache aggressively. The browser caches the
    # redirect, reusing its presigned URL for up to max-age — which must stay
    # under the presign TTL or a cached redirect would point at an expired URL.
    cache_headers = {"Cache-Control": f"public, max-age={_MAP_IMAGE_CACHE_MAX_AGE}"}
    s3_uri = missing_maps_module.find_s3_webp(map_name)
    if s3_uri is not None:
        presigned = replay_files.presigned_url(
            s3_uri, expires_in=_MAP_IMAGE_PRESIGN_TTL
        )
        return RedirectResponse(presigned, status_code=302, headers=cache_headers)
    path = _find_dist_map_path(map_name)
    if path is not None:
        return FileResponse(path, headers=cache_headers)
    raise HTTPException(status_code=404, detail=f"No image for map '{map_name}'")
