"""Tags each request's server span with who made it and which page asked.

Honeycomb can then break any route down by person, by anonymous visitor, by
page, or by caller type (the app vs. pollers, crawlers and scripts).
"""

from collections.abc import Mapping
import secrets
from urllib.parse import urlsplit

from fastapi import Request
from opentelemetry import trace
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from .auth_notify import API_KEY_HEADER
from .dependencies import USER_LABEL_SESSION_KEY, resolve_tier
from .middleware import CLIENT_ID_HEADER, is_crawler

# The SPA route (path + query) the browser was on when it made the call.
PAGE_HEADER = "X-Radarvan-Page"
FRONTEND_CLIENT = "react-frontend"
VISITOR_SESSION_KEY = "visitor_id"
_MAX_HEADER_CHARS = 512
_STATE_KEY = "span_tags"

SpanValue = str | bool | int


def tag_request(request: Request, attrs: Mapping[str, SpanValue]) -> None:
    """Add attributes to this request's server span from inside a handler.

    In a handler the current span is FastAPI's `fastapi.endpoint` child, so
    tags set there would miss the span every other request attribute is on.
    """
    pending = getattr(request.state, _STATE_KEY, {})
    setattr(request.state, _STATE_KEY, {**pending, **attrs})


def _header(request: Request, name: str) -> str | None:
    value = request.headers.get(name)
    return value[:_MAX_HEADER_CHARS] if value else None


def visitor_id(request: Request) -> str | None:
    """The browser's random visitor id, minted on its first app request.

    Only the app's own calls get one: pollers and scripts don't keep cookies,
    so minting for them would make every request a new "visitor".
    """
    existing = request.session.get(VISITOR_SESSION_KEY)
    if existing is not None:
        return str(existing)
    if request.headers.get(CLIENT_ID_HEADER) != FRONTEND_CLIENT:
        return None
    minted = secrets.token_hex(8)
    request.session[VISITOR_SESSION_KEY] = minted
    return minted


def request_attributes(request: Request) -> dict[str, SpanValue]:
    attrs: dict[str, SpanValue] = {
        "app.client": request.headers.get(CLIENT_ID_HEADER, "unknown"),
        "app.crawler": is_crawler(request),
        "app.api_key_tier": resolve_tier(request.headers.get(API_KEY_HEADER)).value,
        "app.logged_in": "user_id" in request.session,
    }
    if (agent := _header(request, "user-agent")) is not None:
        attrs["user_agent.original"] = agent
    if (visitor := visitor_id(request)) is not None:
        attrs["app.visitor_id"] = visitor
    if (label := request.session.get(USER_LABEL_SESSION_KEY)) is not None:
        attrs["enduser.id"] = label
    if (user_id := request.session.get("user_id")) is not None:
        attrs["app.user_id"] = user_id
    if (page := _header(request, PAGE_HEADER)) is not None:
        parts = urlsplit(page)
        attrs["app.page"] = parts.path
        if parts.query:
            attrs["app.page.query"] = parts.query
    return attrs


class RequestTagsMiddleware(BaseHTTPMiddleware):
    """Must sit inside SessionMiddleware: it reads the session, and a visitor id
    it mints only reaches the cookie if Session sees the write."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        attrs = request_attributes(request)
        span = trace.get_current_span()
        if span.is_recording():
            span.set_attributes(attrs)
        response = await call_next(request)
        # The server span is still open here: it ends once the body is sent.
        if span.is_recording():
            span.set_attributes(getattr(request.state, _STATE_KEY, {}))
        return response
