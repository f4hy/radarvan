"""User map upload: preview (convert) then commit (save) maps.

Cookie/login-gated like the other community routes (not behind the API key);
requires a logged-in user to upload.
"""

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from .. import map_upload as map_upload_module
from .. import player_ids
from ..api_types import MapUploadResponse
from ..db import User
from ..db_utils import ReplayManager
from ..dependencies import get_replay_manager, require_current_user

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/map_upload", tags=["map_upload"])


@router.post("", response_model=MapUploadResponse)
def upload_maps(
    commit: bool = Form(False),
    tga: UploadFile | None = File(None),
    map_file: UploadFile | None = File(None),
    zip_file: UploadFile | None = File(None),
    user: User = Depends(require_current_user),
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> MapUploadResponse:
    """Preview (commit=false) or save (commit=true) uploaded maps.

    Provide either a `.tga` + `.map` pair, or a `.zip` of folders that each hold
    a `.map` and a `.tga` (any other files in a folder are ignored).
    """
    if zip_file is not None:
        uploads = map_upload_module.maps_from_zip(zip_file.file.read())
    elif tga is not None and map_file is not None:
        uploads = map_upload_module.maps_from_pair(
            tga.filename or "",
            tga.file.read(),
            map_file.filename or "",
            map_file.file.read(),
        )
    else:
        raise HTTPException(
            status_code=400, detail="Provide a .tga and .map, or a .zip"
        )
    if not uploads:
        raise HTTPException(
            status_code=400,
            detail="No valid maps found (each needs both a .map and a .tga)",
        )
    processed = map_upload_module.process(
        uploads, commit, replay_manager, player_ids.is_admin(user.discord_id)
    )
    logger.info(
        "map upload",
        user_id=user.id,
        commit=commit,
        count=len(processed.items),
        errors=len(processed.errors),
    )
    return MapUploadResponse(
        committed=commit, maps=processed.items, errors=processed.errors
    )
