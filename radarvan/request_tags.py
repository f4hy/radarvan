"""Tags each request's server span with who made it and which page asked.

Honeycomb can then break any route down by person, by anonymous visitor, by
page, or by caller type (the app vs. pollers, crawlers and scripts).
"""

from collections.abc import Mapping
import re
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
# A random id the browser generates once and keeps in localStorage. Minted
# client-side so the concurrent requests of a first page load all agree on it;
# minted server-side, each would race to write its own into the session cookie.
VISITOR_HEADER = "X-Radarvan-Visitor"
_VISITOR_ID = re.compile(r"[0-9a-f-]{8,64}")
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


def caller_attributes(request: Request) -> dict[str, SpanValue]:
    attrs: dict[str, SpanValue] = {
        "app.client": request.headers.get(CLIENT_ID_HEADER, "unknown"),
        "app.crawler": is_crawler(request),
        "app.api_key_tier": resolve_tier(request.headers.get(API_KEY_HEADER)).value,
    }
    if (agent := _header(request, "user-agent")) is not None:
        attrs["user_agent.original"] = agent
    visitor = request.headers.get(VISITOR_HEADER, "")
    if _VISITOR_ID.fullmatch(visitor):
        attrs["enduser.pseudo.id"] = visitor
    if (page := _header(request, PAGE_HEADER)) is not None:
        parts = urlsplit(page)
        attrs["app.page"] = parts.path
        if parts.query:
            attrs["app.page.query"] = parts.query
    return attrs


def identity_attributes(request: Request) -> dict[str, SpanValue]:
    # enduser.id is the stable user id; the name can change (Discord name until
    # a player is claimed), so it rides alongside rather than being the key.
    user_id = request.session.get("user_id")
    attrs: dict[str, SpanValue] = {"app.logged_in": user_id is not None}
    if user_id is not None:
        attrs["enduser.id"] = str(user_id)
    if (label := request.session.get(USER_LABEL_SESSION_KEY)) is not None:
        attrs["app.user.name"] = label
    return attrs


class RequestTagsMiddleware(BaseHTTPMiddleware):
    """Must sit inside SessionMiddleware, which is what gives it the session."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        span = trace.get_current_span()
        if span.is_recording():
            span.set_attributes(caller_attributes(request))
            span.set_attributes(identity_attributes(request))
        response = await call_next(request)
        # The server span is still open here: it ends once the body is sent.
        # Identity is re-read so login and name selection are tagged with the
        # session they leave behind; a logout keeps who it was (attributes are
        # only ever overwritten) with app.logged_in now false.
        if span.is_recording():
            span.set_attributes(identity_attributes(request))
            span.set_attributes(getattr(request.state, _STATE_KEY, {}))
        return response
