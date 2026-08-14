"""FastAPI app construction.

Route handlers live in radarvan.routes.*. This module composes them, wires
middleware/exception handlers, and manages the app lifecycle (scheduler,
cache warming, S3 connection test).
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import Depends, FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import Response

from . import cncstats_client, middleware, replay_files, schedule
from .auth_notify import notify_auth_event
from .cache import warm_caches
from .dependencies import IS_DEV, SESSION_SECRET, db_manager, verify_api_key
from .logging_config import configure_logging
from .notify import notify_async
from .routes import (
    admin,
    auth,
    bracket,
    commentary,
    draft,
    ffa,
    files,
    generals,
    map_upload,
    maps,
    matches,
    players,
    predict,
    profile,
    superlatives,
    teams,
    tournaments,
    votes,
)
from .tracing import configure_tracing

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Setup and shutdown of the webserver."""
    configure_logging(dev=IS_DEV)
    logger.info("hello")
    cncstats_client.cncstats_client()
    replay_files.test_connection()
    logger.info("connection tested")
    # Jobs open their own sessions per run (see radarvan.schedule).
    scheduler = schedule.get_scheduler(db_manager)
    if not IS_DEV:
        scheduler.start()
    warm_caches()
    yield
    if not IS_DEV:
        scheduler.shutdown()
    logger.info("goodbye!")


app = FastAPI(
    title="radarvan",
    description="Stats for generals",
    version="0.1.0",
    lifespan=lifespan,
)

configure_tracing(app)

PROTECTED = [Depends(verify_api_key)]

# Middleware order matters. add_middleware prepends, so the LAST added is the
# outermost. We want, outer→inner: CORS, RequestContext, GZip, RateLimit,
# Session, app - so CORS decorates every response (including the limiter's 429),
# request-id is bound before the limiter logs, the limiter rejects just before
# app work, and Session (innermost) populates request.session for the handlers.
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    same_site="lax",
    https_only=not IS_DEV,
)
app.add_middleware(middleware.RateLimitMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(middleware.RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-Request-ID",
        "Retry-After",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
    ],
)


@app.exception_handler(StarletteHTTPException)
async def handle_http_exception(
    request: Request, exc: StarletteHTTPException
) -> Response:
    """The app's handler for *every* HTTPException - 404s from the StaticFiles
    mount included - which additionally reports 401/403 to the notify webhook.

    Registering it replaces FastAPI's built-in handler wholesale, hence the
    delegation to `http_exception_handler` rather than building a response
    here. Anyone adding custom behaviour for another status should extend this
    function: a second `@app.exception_handler(StarletteHTTPException)` would
    silently replace it, taking the auth notices with it.

    Catching auth rejections here is what makes the reporting total -
    dependencies.verify_api_key / require_admin_key / require_current_user /
    require_admin_login, routes/bracket._require_tournament_admin and any
    future check all raise, so none of them has to remember to notify. The
    flip side is the invariant it rests on: a gate must *raise* 401/403, never
    return one as a plain Response, or the rejection goes unreported.
    """
    if exc.status_code in (401, 403):
        notify_auth_event(request, exc.status_code, str(exc.detail))
    return await http_exception_handler(request, exc)


@app.exception_handler(Exception)
async def my_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled exception", exc_info=exc)
    # notify_async swallows its own errors. Never echo exception details to
    # the client.
    await notify_async(f"Unhandled Exception {request.url.path} {exc!r}")
    response = JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        response.headers[middleware.REQUEST_ID_HEADER] = request_id
    return response


# Routers - all API routes require an API key (any tier); static/index routes
# below do not. Individual routes that need the admin tier tag themselves with
# `dependencies=ADMIN_ONLY` (see dependencies.require_admin_key).
app.include_router(files.router, dependencies=PROTECTED)
app.include_router(matches.router, dependencies=PROTECTED)
app.include_router(players.router, dependencies=PROTECTED)
app.include_router(profile.router, dependencies=PROTECTED)
app.include_router(generals.router, dependencies=PROTECTED)
app.include_router(ffa.router, dependencies=PROTECTED)
app.include_router(teams.router, dependencies=PROTECTED)
app.include_router(maps.router, dependencies=PROTECTED)
app.include_router(draft.router, dependencies=PROTECTED)
app.include_router(superlatives.router, dependencies=PROTECTED)
app.include_router(tournaments.router, dependencies=PROTECTED)
app.include_router(admin.router, dependencies=PROTECTED)
app.include_router(predict.router, dependencies=PROTECTED)
app.include_router(commentary.router, dependencies=PROTECTED)

# Public asset routes - reachable without an API key (browser <img> loads).
app.include_router(maps.public_router)

# Auth routes - browser-/cookie-driven, deliberately not behind the API key.
app.include_router(auth.router)

# Map voting - cookie-identified (like auth), so not behind the API key.
app.include_router(votes.router)

# Map upload - login-gated (like auth), so not behind the API key.
app.include_router(map_upload.router)

# Bracket tournament - public reads, login+admin-gated writes (checked inside
# the route handlers), so not behind the API key.
app.include_router(bracket.router)

# Admin actions the UI drives (reparse) - gated on a logged-in admin via
# ADMIN_LOGIN rather than an API key, since the browser only ships a
# normal-tier key. Not behind the API key for the same reason.
app.include_router(admin.session_router)


@app.get("/", include_in_schema=False)
def serve_index() -> FileResponse:
    return FileResponse(
        "dist/index.html",
        headers={"Cache-Control": "no-cache"},
    )


app.mount("/", StaticFiles(directory="dist", html=True), name="dist")
