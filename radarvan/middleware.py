"""Request plumbing: request-id binding and timing (ASGI middleware), and the
in-memory rate limit (an app-wide dependency)."""

import math
import os
import random
import time
import uuid

import structlog
from fastapi import HTTPException, Request
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .rate_limit import InMemoryRateLimitStore, RateLimitStore

logger = structlog.get_logger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"
CLIENT_ID_HEADER = "X-Client-Id"


def client_key(request: Request) -> str:
    """Best available identity for a caller: the first X-Forwarded-For hop
    (Heroku sets it) falling back to the socket peer.

    Shared by the rate limiter and the auth-rejection notices in
    dependencies.py so "one client" means the same thing in both.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


_CRAWLER_MARKERS = (
    "bot",
    "crawler",
    "spider",
    "slurp",
    "bingpreview",
    "facebookexternalhit",
    "embedly",
)


def is_crawler(request: Request) -> bool:
    ua = request.headers.get("user-agent", "").lower()
    return any(marker in ua for marker in _CRAWLER_MARKERS)


# Rate-limit config (env-overridable). 0 disables the limiter entirely.
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "1200"))
# Max random seconds added to the advertised Retry-After so a burst of throttled
# clients don't all retry on the same tick (thundering herd).
RATE_LIMIT_RETRY_JITTER_SECONDS = float(os.getenv("RATE_LIMIT_RETRY_JITTER", "5"))
_WINDOW_SECONDS = 60.0


class RequestContextMiddleware:
    """Assign a request id, identify the caller, and log timing per request.

    Reuses an incoming X-Request-ID or generates a uuid4, binds it and the
    X-Client-Id caller to structlog's contextvars for every log line of the
    request, and echoes the id back on the response.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request = Request(scope)
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        # On state so the app-level 500 handler, which runs outside this
        # middleware, can still echo the id.
        request.state.request_id = request_id
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            client=request.headers.get(CLIENT_ID_HEADER, "unknown"),
        )
        path = request.url.path
        # The SPA's data, not pages; map images may still be indexed.
        noindex = path.startswith("/api") and not path.startswith("/api/map_image/")
        status = 500

        async def send_with_headers(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = MutableHeaders(scope=message)
                headers[REQUEST_ID_HEADER] = request_id
                if noindex:
                    headers["X-Robots-Tag"] = "noindex"
            await send(message)

        start_time = time.time()
        try:
            await self.app(scope, receive, send_with_headers)
        finally:
            logger.info(
                "request",
                method=request.method,
                path=path,
                status=status,
                took=round(time.time() - start_time, 4),
            )
            structlog.contextvars.clear_contextvars()


class RateLimit:
    """Per-client sliding-window request rate limit on /api routes.

    An app-wide dependency, so it runs before every router's auth check and a
    flood of bad keys can't become a flood of auth notices. Over the limit it
    raises 429 with a jittered `Retry-After`, which apiConfig.ts waits out.
    Async on purpose: the store is called on the event loop, never the
    threadpool.
    """

    def __init__(
        self,
        limit_per_minute: int = RATE_LIMIT_PER_MINUTE,
        store: RateLimitStore | None = None,
    ) -> None:
        self.limit = limit_per_minute
        self.store: RateLimitStore = store or InMemoryRateLimitStore()

    async def __call__(self, request: Request) -> None:
        if self.limit <= 0 or not request.url.path.startswith("/api"):
            return
        key = client_key(request)
        decision = self.store.check(key, self.limit, _WINDOW_SECONDS)
        if decision.allowed:
            return
        # Non-crypto jitter: only spreads out retry timing, never a secret.
        jitter = random.uniform(0, RATE_LIMIT_RETRY_JITTER_SECONDS)  # noqa: S311
        retry_after = max(1, math.ceil(decision.retry_after + jitter))
        logger.warning(
            "rate limited", client=key, path=request.url.path, retry_after=retry_after
        )
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Retry after {retry_after}s.",
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(decision.limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(retry_after),
            },
        )
