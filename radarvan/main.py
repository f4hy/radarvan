"""FastAPI app construction.

Route handlers live in radarvan.routes.*. This module composes them, wires
middleware/exception handlers, and manages the app lifecycle (scheduler,
cache warming, S3 connection test).
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from . import cncstats_client, middleware, replay_files, schedule
from .cache import warm_caches
from .dependencies import IS_DEV, SESSION_SECRET, db_manager, verify_api_key
from .logging_config import configure_logging
from .notify import notify
from .routes import (
    admin,
    auth,
    bracket,
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


@app.exception_handler(Exception)
async def my_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled exception", exc_info=exc)
    # notify() swallows its own errors; to_thread keeps the webhook call off
    # the event loop. Never echo exception details to the client.
    await asyncio.to_thread(notify, f"Unhandled Exception {request.url.path} {exc!r}")
    response = JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        response.headers[middleware.REQUEST_ID_HEADER] = request_id
    return response


# Routers - all API routes require an API key; static/index routes below do not.
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


@app.get("/", include_in_schema=False)
def serve_index() -> FileResponse:
    return FileResponse(
        "dist/index.html",
        headers={"Cache-Control": "no-cache"},
    )


app.mount("/", StaticFiles(directory="dist", html=True), name="dist")
