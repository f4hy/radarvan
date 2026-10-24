"""Usage beacons from the app, recorded as span attributes only."""

from fastapi import APIRouter, Request

from ..api_types import PageView
from ..request_tags import tag_request

router = APIRouter(tags=["telemetry"])


# The span is the record: request_tags.py already tags it with who is looking,
# so this adds what they looked at. Nothing is stored.
@router.post("/api/page_view", status_code=204)
async def page_view(view: PageView, request: Request) -> None:
    tag_request(
        request,
        {
            "app.page_view.path": view.path,
            "app.page_view.query": view.query,
            "app.page_view.referrer": view.referrer or "",
        },
    )
