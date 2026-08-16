"""Map stats, geometry, render, and image endpoints."""

import asyncio

import structlog
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse

from .. import map_render as map_render_module
from .. import map_stats as map_stats_module
from .. import ml_inference
from .. import missing_maps as missing_maps_module
from .. import replay_files
from ..api_types import (
    FetchMissingMapResult,
    MapDataPayload,
    MapMatchCount,
    MapReparseStatus,
    MapRenderRequest,
    MapStatsResponse,
    MapsByPlayerCount,
    MapSummaryRequest,
    MissingMapInfo,
    BackfillMapCrcsResponse,
    PushMapResult,
    PushMapsResponse,
    ReparseMapResult,
    ReparseMapsResponse,
)
from ..cache import (
    competitive_matches,
    maps_by_player_count,
    resolve_map_name_cached,
    sorted_deduped_matches,
)
from ..db_utils import ReplayManager
from ..dependencies import (
    ADMIN_ONLY,
    IS_DEV,
    cache_short,
    get_replay_manager,
    require_dev,
)

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["map"])

# Routes that must be reachable without an API key (e.g. <img src> loads, which
# cannot send the X-API-Key header). Included without auth deps in main.py.
public_router = APIRouter(tags=["map"])

# Map images are static. Presign for the S3 max (7 days) and let browsers cache
# the redirect - max-age must stay under the presign TTL. We keep the cache to
# 1h (well under the 7-day presign) so that if the deployment ever runs on
# temporary/STS credentials - which silently cap the presign at the credential
# lifetime - a cached redirect is unlikely to outlive its presigned URL.
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
    # Best-effort win prediction for this hypothetical matchup (notifies result).
    resolved_map = replay_manager.resolve_map_name(request.map_name) or request.map_name
    prediction = ml_inference.predict_and_notify_features(
        resolved_map, [(p.name, p.general, p.team) for p in request.players]
    )
    return map_stats_module.format_map_summary(summary, prediction)


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
    # Through the cache: the underlying query loads every MapData row *and* its
    # JSON geometry blob. cache.maps_by_player_count exists for exactly this
    # (see its docstring); calling the repo directly re-scanned per request.
    grouped = maps_by_player_count(replay_manager)
    return [MapsByPlayerCount(player_count=k, maps=v) for k, v in grouped.items()]


@router.post("/api/map_data/{map_name}", dependencies=ADMIN_ONLY)
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


@router.delete(
    "/api/map_data/{map_name}",
    include_in_schema=IS_DEV,
    dependencies=[*ADMIN_ONLY, Depends(require_dev)],
)
def delete_map_data(
    map_name: str,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> dict[str, str]:
    """Delete the MapData row for a map (geometry + CRC + sync state). Dev-only.

    Does not touch the `.map`/`.tga`/`.webp` assets in S3 or any match history -
    only the derived MapData row. For an orphaned map (no matches reference it),
    that's a full removal.
    """
    deleted = replay_manager.delete_map_data(map_name)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"No map data for '{map_name}'")
    return {"status": "deleted", "map_name": map_name}


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


@router.post("/api/fetch_map_for_match/{match_id}", dependencies=ADMIN_ONLY)
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


@router.post("/api/backfill_map_crcs", dependencies=ADMIN_ONLY)
def backfill_map_crcs(
    max_to_update: int = 50,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> BackfillMapCrcsResponse:
    """Fill in MapData.crc from a sample match's replay, or the hosted `.map` bytes.

    For each MapData row missing a CRC, finds a match played on that map and
    reads the CRC from its parsed replay JSON; for a map nobody has played,
    computes it from the `.map` bytes we host in S3 instead. Resumable
    (only NULL-CRC rows are touched). Processes up to `max_to_update` rows.
    """
    results = missing_maps_module.backfill_map_crcs(replay_manager, limit=max_to_update)
    resolved = sum(1 for _, crc in results if crc is not None)
    return BackfillMapCrcsResponse(
        processed=len(results), resolved=resolved, results=results
    )


@router.get("/api/map_reparse_status", include_in_schema=IS_DEV)
def map_reparse_status(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> MapReparseStatus:
    """How much work `POST /api/reparse_maps` has left: stale rows + missing maps.

    `stale_maps` compares each MapData row's stored `mapparse_bin_hash` against
    the current binary's hash (recomputed from the file, so a rebuild is
    detected without a manual version bump). `missing_maps` is maps referenced
    by matches with no MapData row at all. Both are what `reparse_maps` works
    through; call it repeatedly (it's resumable) until both hit 0.
    """
    current_hash = missing_maps_module.mapparse_bin_hash()
    total = len(replay_manager.list_map_names())
    stale = (
        replay_manager.count_maps_needing_reparse(current_hash)
        if current_hash is not None
        else total
    )
    missing = len(missing_maps_module.list_missing_maps(replay_manager))
    return MapReparseStatus(
        total_maps=total,
        stale_maps=stale,
        missing_maps=missing,
        mapparse_available=missing_maps_module.mapparse_available(),
        current_mapparse_hash=current_hash,
    )


@router.post("/api/reparse_maps", include_in_schema=IS_DEV, dependencies=ADMIN_ONLY)
def reparse_maps(
    max_to_update: int = 20,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> ReparseMapsResponse:
    """Bring stored map geometry up to date with the current mapparse binary.

    Covers both buckets in one pass, up to `max_to_update` total (stale rows
    first, then missing maps with whatever budget is left):

    - Existing rows whose stored geometry predates the current binary:
      reparsed from the `.map` bytes already in S3, no cncstats call (see
      `missing_maps.reparse_stored_map`) - cheap and always the bulk of the
      work, so it goes first.
    - Maps referenced by matches with no MapData row yet: fetched fresh from
      cncstats and parsed (like the old `fetch_missing_maps`). Some of these
      may be maps cncstats has never seen either, so they fail every call -
      put last so a handful of permanently-missing maps can't crowd out the
      (fast, reliable) stale reparses batch after batch.

    Resumable - call repeatedly (e.g. from a script) until `remaining` is 0.
    Use `GET /api/map_reparse_status` to check progress without doing any work.
    """
    current_hash = missing_maps_module.mapparse_bin_hash()
    if current_hash is None:
        raise HTTPException(status_code=503, detail="mapparse binary not available")

    results: list[ReparseMapResult] = []
    updated = 0

    stale = replay_manager.maps_needing_reparse(current_hash, limit=max_to_update)
    for name in stale:
        try:
            missing_maps_module.reparse_stored_map(name, replay_manager)
            updated += 1
            results.append(ReparseMapResult(map_name=name))
        except Exception as e:
            logger.warning("reparse_maps failed for map", map_name=name, error=repr(e))
            results.append(ReparseMapResult(map_name=name, ok=False, error=str(e)))

    missing_budget = max_to_update - len(stale)
    missing = (
        missing_maps_module.list_missing_maps_with_crc(
            replay_manager, limit=missing_budget
        )
        if missing_budget > 0
        else []
    )
    for m in missing:
        fetched = missing_maps_module.fetch_and_upload(
            m, replay_manager=replay_manager, parse_and_save=True
        )
        if fetched is None:
            results.append(
                ReparseMapResult(
                    map_name=m.map_name,
                    was_missing=True,
                    ok=False,
                    error="fetch failed",
                )
            )
            continue
        updated += 1
        results.append(ReparseMapResult(map_name=m.map_name, was_missing=True))

    remaining = replay_manager.count_maps_needing_reparse(current_hash) + len(
        missing_maps_module.list_missing_maps(replay_manager)
    )
    return ReparseMapsResponse(updated=updated, remaining=remaining, results=results)


# Bound the in-flight pushes so we don't open an unbounded number of S3 reads /
# cncstats connections at once.
_PUSH_CONCURRENCY = 8


@router.post("/api/push_maps_to_cncstats", dependencies=ADMIN_ONLY)
async def push_maps_to_cncstats(
    max_to_update: int = 10,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> PushMapsResponse:
    """Register maps we host (.map + .tga preview, from S3) with cncstats /add_map.

    Only considers maps not already marked synced, and checks cncstats /map_exists
    before pushing - so a map is never sent twice. Pushes run concurrently
    (bounded by `_PUSH_CONCURRENCY`); the CRC + synced mark are then written back
    serially (one DB session). Processes up to `max_to_update` unsynced maps.
    Requires `CNCSTATS_API_KEY`.
    """
    if not missing_maps_module.cncstats_push_enabled():
        raise HTTPException(
            status_code=503, detail="CNCSTATS_API_KEY is not configured"
        )
    pending = replay_manager.unsynced_maps(limit=max_to_update)
    sem = asyncio.Semaphore(_PUSH_CONCURRENCY)

    async def sync_one(
        name: str, crc: str | None
    ) -> tuple[str, str | None, bool, str | None]:
        async with sem:
            try:
                (
                    resolved,
                    pushed,
                ) = await missing_maps_module.sync_stored_map_to_cncstats(name, crc)
                return name, resolved, pushed, None
            except Exception as e:
                return name, None, False, str(e)

    rows = await asyncio.gather(*(sync_one(name, crc) for name, crc in pending))

    results: list[PushMapResult] = []
    pushed = 0
    already_present = 0
    for name, crc, was_pushed, error in rows:
        if error is not None:
            results.append(PushMapResult(map_name=name, error=error))
            continue
        if crc:
            # Record CRC + synced mark in one update (single DB session, serialized).
            replay_manager.record_cncstats_sync(name, crc)
        if was_pushed:
            pushed += 1
        else:
            already_present += 1
        results.append(
            PushMapResult(
                map_name=name,
                crc=crc,
                pushed=was_pushed,
                already_present=not was_pushed,
            )
        )
    return PushMapsResponse(
        requested=len(pending),
        pushed=pushed,
        already_present=already_present,
        results=results,
    )


def _load_map_image_bytes(map_name: str, replay_manager: ReplayManager) -> bytes:
    canonical = resolve_map_name_cached(replay_manager, map_name) or map_name
    s3_uri = missing_maps_module.find_s3_webp(canonical)
    if s3_uri is not None:
        fs = replay_files.get_fs()
        data: bytes = fs.read_bytes(s3_uri)
        return data
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
    image_bytes = _load_map_image_bytes(canonical, replay_manager)
    png = map_render_module.render_map(image_bytes, map_data, request.players)
    base = canonical.removesuffix(".map").split("/")[-1]
    return Response(
        content=png,
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="{base}.png"'},
    )


@public_router.get("/api/map_image/{map_name}", response_model=None)
def get_map_image(
    map_name: str, replay_manager: ReplayManager = Depends(get_replay_manager)
) -> RedirectResponse:
    """Return the WebP for a map, redirecting to its presigned S3 URL.

    Resolves to the canonical `MapData.map_name` first (case-/whitespace-
    insensitive), since that's stored as the exact S3 asset base name; falls
    back to case-insensitive variant guesses in S3 for maps with no MapData row.
    """
    # Map images are static, so cache aggressively. The browser caches the
    # redirect, reusing its presigned URL for up to max-age - which must stay
    # under the presign TTL or a cached redirect would point at an expired URL.
    cache_headers = {"Cache-Control": f"public, max-age={_MAP_IMAGE_CACHE_MAX_AGE}"}
    canonical = resolve_map_name_cached(replay_manager, map_name) or map_name
    s3_uri = missing_maps_module.find_s3_webp(canonical)
    if s3_uri is not None:
        presigned = replay_files.presigned_url(
            s3_uri, expires_in=_MAP_IMAGE_PRESIGN_TTL
        )
        return RedirectResponse(presigned, status_code=302, headers=cache_headers)
    raise HTTPException(status_code=404, detail=f"No image for map '{map_name}'")
