"""Replay file listing, upload, and URL endpoints."""

from datetime import date
import structlog

from pydantic import BaseModel

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    UploadFile,
)

from .. import matches, ml_inference, replay_files
from ..api_types import (
    GameRecord,
    MatchInfo,
    ParsedReplayJsonSchema,
    ReplayFileSchema,
    ReplayWithoutPlayerStats,
)
from ..cache import invalidate_match_caches
from ..db_utils import ReplayManager
from ..dependencies import get_replay_manager

logger = structlog.get_logger(__name__)

router = APIRouter()


class ReplayFilters(BaseModel):
    match_id: int | None = None
    game_date: date | None = None


@router.get("/api/files/pending_unprocessed")
def list_pending_unprocessed(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> list[ReplayFileSchema]:
    """Return replay files that are pending but have no parsed JSON."""
    files = replay_manager.list_pending_without_parsed()
    return [ReplayFileSchema.model_validate(f) for f in files]


@router.get("/api/files/")
def list_files(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> list[ReplayFileSchema]:
    listed = list(replay_manager.list_files())
    logger.info("found files", count=len(listed))
    return [ReplayFileSchema.model_validate(f) for f in listed]


@router.get("/api/replays/")
def list_replays(
    filters: ReplayFilters = Query(),
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> list[GameRecord]:
    listed = replay_manager.list_jsons(
        match_id=filters.match_id, game_date=filters.game_date
    )
    logger.info("found files", count=len(listed))
    converted = []
    for ls in listed:
        record = GameRecord.model_validate(ls, from_attributes=True)
        record.json_presigned_url = replay_files.presigned_url(ls.json_s3_uri)
        if ls.replay_file is not None:
            record.replay_presigned_url = replay_files.presigned_url(
                ls.replay_file.s3_uri
            )
        converted.append(record)
    return converted


@router.get("/api/replay_url/{match_id}")
def get_match_replay_url(
    match_id: int,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> dict[str, str]:
    """Return a presigned S3 URL for the .rep file of a match."""
    match = replay_manager.get_match(match_id)
    if match is None:
        raise HTTPException(status_code=404, detail=f"Match {match_id} not found")
    parsed = match.replay_json
    if parsed is None or parsed.replay_file is None:
        raise HTTPException(
            status_code=404, detail=f"Replay file for {match_id} not found"
        )
    return {"url": replay_files.presigned_url(parsed.replay_file.s3_uri)}


@router.get("/api/replay")
def get_replay_by_url(
    url_of_replay: str,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> dict[str, str]:
    replay = replay_manager.get_replay_file(url_of_replay)
    if not replay:
        return {}
    return {"original_url": replay.original_url, "status": replay.status.value}


@router.post("/api/upload_replay")
def upload_replay(
    file: UploadFile = File(...),
    mac_id: str | None = Form(None),
    board_id: str | None = Form(None),
    player_name: str | None = Form(None),
    client_version: str | None = Form(None),
    source_tag: str | None = Form(None),
    x_zulu_build: str | None = Header(None),
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> MatchInfo:
    """Upload a .rep file, save it to S3, parse it, and return the match info.

    Optional source identifiers are stored on the ReplayFile row:
    - mac_id: gentool-style MAC-based identifier
    - board_id: stable identifier not tied to a network interface
    - player_name: in-game name the uploader played under
    - client_version: version string of the uploading client
    - source_tag: free-form uploader-supplied label

    The optional X-Zulu-Build request header is captured on the ReplayFile; when
    it starts with "dev-" the replay and its match are flagged is_dev.
    """
    data = file.file.read()
    file_hash = replay_files.compute_hash(data)

    if replay_manager.get_replay_by_hash(file_hash) is not None:
        raise HTTPException(
            status_code=409, detail=f"Replay already uploaded (hash={file_hash})"
        )

    result = replay_files.upload_and_parse(
        data,
        file_hash,
        replay_manager,
        mac_id=mac_id,
        board_id=board_id,
        uploader_name=player_name,
        client_version=client_version,
        source_tag=source_tag,
        zulu_build=x_zulu_build,
    )
    is_dev = replay_files.is_dev_build(x_zulu_build)
    db_match = matches.replay_to_db_match(
        result.replay, result.json_path, is_dev=is_dev
    )
    replay_manager.register_match(db_match)
    replay_manager.compute_and_save_composition(db_match.match_id)
    invalidate_match_caches()

    match_info = matches.match_from_replay(result.replay)
    if match_info is None:
        raise HTTPException(status_code=422, detail="Replay is too short or invalid")
    # Best-effort win prediction for the uploaded match (notifies pred vs actual).
    ml_inference.predict_and_notify(match_info)
    return match_info


@router.post("/api/register_replay_url")
def register_replay_url(
    url_of_replay: str,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> MatchInfo | None:
    """Register and parse a new replay from a URL."""
    existing = replay_manager.get_replay_file(url_of_replay)
    if existing:
        if existing.parsed_replay_json:
            logger.info("Already parsed, skipping")
            return None
    replay = replay_files.parse_replay(url_of_replay, replay_manager)
    return matches.reparse_replay(replay.replay_id, replay_manager)


@router.get("/api/files_for_match", response_model_exclude_none=True)
def get_files_for_match_id(
    match_id: int,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> dict[str, list[ReplayFileSchema] | list[ParsedReplayJsonSchema]]:
    """Get all replay and parsed files for a match."""
    files = replay_manager.all_files_for_id(match_id)
    return {
        "replay_files": [
            ReplayFileSchema.model_validate(r) for r in files.replay_files
        ],
        "parsed_files": [
            ParsedReplayJsonSchema.model_validate(p) for p in files.parsed_files
        ],
    }


@router.get("/api/presigned_urls_for_match", response_model_exclude_none=True)
def get_presigned_for_match_id(
    match_id: int,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> dict[str, str]:
    """Get presigned urls for all files for a match id."""
    files = replay_manager.all_files_for_id(match_id)
    replay_urls = [
        ReplayFileSchema.model_validate(r).s3_uri for r in files.replay_files
    ]
    json_urls = [
        ParsedReplayJsonSchema.model_validate(p).json_s3_uri for p in files.parsed_files
    ]
    presigned = {d: replay_files.presigned_url(d) for d in replay_urls} | {
        d: replay_files.presigned_url(d) for d in json_urls
    }
    logger.debug("presigned urls", presigned=presigned)
    return presigned


@router.get("/api/replays_without_playerstats/")
def replays_without_playerstats(
    max_to_return: int = 10,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> list[ReplayWithoutPlayerStats]:
    missing_player_stats = replay_manager.list_jsons_without_player_stats(max_to_return)
    return [
        ReplayWithoutPlayerStats(
            match_id=row.match_id,
            url=row.url,
            s3_path=row.s3_path,
            version=row.version,
            presigned_url=replay_files.presigned_url(row.s3_path),
            all_replay_urls=row.all_replay_urls,
        )
        for row in missing_player_stats
    ]
