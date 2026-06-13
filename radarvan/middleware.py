import math
import os
import random
import time
import uuid

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from .rate_limit import InMemoryRateLimitStore, RateLimitStore

logger = structlog.get_logger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"
CLIENT_ID_HEADER = "X-Client-Id"

# Rate-limit config (env-overridable). 0 disables the limiter entirely.
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))
# Max random seconds added to the advertised Retry-After so a burst of throttled
# clients don't all retry on the same tick (thundering herd).
RATE_LIMIT_RETRY_JITTER_SECONDS = float(os.getenv("RATE_LIMIT_RETRY_JITTER", "5"))
_WINDOW_SECONDS = 60.0


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assign a request id, identify the caller, and log timing per request.

    Reuses an incoming X-Request-ID if the caller supplied one, otherwise
    generates a uuid4. The id and caller are bound to structlog's contextvars
    so every log line emitted while handling the request carries them, and the
    id is echoed back in the response headers. Callers identify themselves via
    X-Client-Id (the React app sends "react-frontend").
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        client_id = request.headers.get(CLIENT_ID_HEADER, "unknown")
        # Stored on state so the app-level exception handler can echo the id
        # back on the 500 path, where call_next raises past this point.
        request.state.request_id = request_id
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id, client=client_id)

        start_time = time.time()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        finally:
            logger.info(
                "request",
                method=request.method,
                path=request.url.path,
                status=status,
                took=round(time.time() - start_time, 4),
            )
            structlog.contextvars.clear_contextvars()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-client sliding-window request rate limit on /api routes.

    Limits each client to `limit_per_minute` requests in any trailing 60s
    window. On exceed it returns 429 with `Retry-After` (seconds to wait, with
    random jitter so throttled clients don't retry in lockstep) plus
    `X-RateLimit-Limit/Remaining/Reset` headers.

    Only /api/* is limited — static assets and the SPA shell are left alone so
    the app still loads under throttling. Hit storage is delegated to a
    `RateLimitStore` (default in-memory, per worker); pass a shared
    Redis/DB-backed store to enforce a global limit across workers/dynos.
    Clients are keyed by the first X-Forwarded-For hop (Heroku sets it) falling
    back to the socket peer.
    """

    def __init__(
        self,
        app: ASGIApp,
        limit_per_minute: int = RATE_LIMIT_PER_MINUTE,
        store: RateLimitStore | None = None,
    ) -> None:
        super().__init__(app)
        self.limit = limit_per_minute
        self.store: RateLimitStore = store or InMemoryRateLimitStore()

    @staticmethod
    def _client_key(request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if self.limit <= 0 or not request.url.path.startswith("/api"):
            return await call_next(request)

        key = self._client_key(request)
        decision = self.store.check(key, self.limit, _WINDOW_SECONDS)

        if not decision.allowed:
            # Non-crypto jitter: only spreads out retry timing, never a secret.
            jitter = random.uniform(0, RATE_LIMIT_RETRY_JITTER_SECONDS)  # noqa: S311
            retry_after = max(1, math.ceil(decision.retry_after + jitter))
            logger.warning(
                "rate limited",
                client=key,
                path=request.url.path,
                retry_after=retry_after,
            )
            return JSONResponse(
                status_code=429,
                content={"detail": f"Rate limit exceeded. Retry after {retry_after}s."},
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(decision.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(retry_after),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(decision.limit)
        response.headers["X-RateLimit-Remaining"] = str(decision.remaining)
        return response
