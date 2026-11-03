"""Tags each request's server span with who made it and which page asked."""

import re
from urllib.parse import urlsplit

from fastapi import Request
from opentelemetry import trace
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from .middleware import CLIENT_ID_HEADER, is_crawler

# The SPA route (path + query) the browser was on when it made the call.
PAGE_HEADER = "X-Radarvan-Page"
# Minted client-side (apiConfig.ts) so the concurrent requests of a first page
# load agree on it; a server-minted cookie id would race between them.
VISITOR_HEADER = "X-Radarvan-Visitor"
_VISITOR_ID = re.compile(r"[0-9a-f-]{8,64}")
_MAX_HEADER_CHARS = 512


def _header(request: Request, name: str) -> str | None:
    value = request.headers.get(name)
    return value[:_MAX_HEADER_CHARS] if value else None


def request_attributes(request: Request) -> dict[str, str | bool]:
    attrs: dict[str, str | bool] = {
        "app.client": _header(request, CLIENT_ID_HEADER) or "unknown",
        "app.crawler": is_crawler(request),
    }
    if (agent := _header(request, "user-agent")) is not None:
        attrs["user_agent.original"] = agent
    if (user_id := request.session.get("user_id")) is not None:
        attrs["enduser.id"] = str(user_id)
    if _VISITOR_ID.fullmatch(visitor := request.headers.get(VISITOR_HEADER, "")):
        attrs["enduser.pseudo.id"] = visitor
    if (page := _header(request, PAGE_HEADER)) is not None:
        parts = urlsplit(page)
        attrs["app.page"] = parts.path
        if parts.query:
            attrs["app.page.query"] = parts.query
    return attrs


class RequestTagsMiddleware(BaseHTTPMiddleware):
    """Must sit inside SessionMiddleware, which is what gives it the session."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        span = trace.get_current_span()
        if span.is_recording():
            span.set_attributes(request_attributes(request))
        return await call_next(request)
