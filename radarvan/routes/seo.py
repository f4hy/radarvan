"""Crawler-facing routes: the sitemap. Public - search engines send no API key."""

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from .. import seo
from ..db_utils import ReplayManager
from ..dependencies import get_replay_manager

router = APIRouter(tags=["seo"])


@router.get("/sitemap.xml", include_in_schema=False)
def sitemap(replay_manager: ReplayManager = Depends(get_replay_manager)) -> Response:
    return Response(
        seo.sitemap_xml(seo.site_index(replay_manager)),
        media_type="application/xml",
        headers={"Cache-Control": "public, max-age=3600"},
    )
