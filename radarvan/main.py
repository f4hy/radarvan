"""FastAPI app construction.

Route handlers live in radarvan.routes.*. This module composes them, wires
middleware/exception handlers, and manages the app lifecycle (scheduler,
cache warming, S3 connection test).
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import exception_handling, middleware, parse_replay, replay_files, schedule
from .cache import warm_caches
from .dependencies import IS_DEV, db_manager, verify_api_key
from .logging_config import configure_logging
from .routes import (
    admin,
    draft,
    files,
    generals,
    maps,
    matches,
    players,
    superlatives,
    teams,
    tournaments,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Setup and shutdown of the webserver."""
    configure_logging(dev=IS_DEV)
    logger.info("hello")
    parse_replay.http_client()
    replay_files.test_connection()
    logger.info("connection tested")
    with db_manager.get_replay_manager() as replay_manager:
        scheduler = schedule.get_scheduler(replay_manager, db_manager)
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(middleware.RequestContextMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.exception_handler(Exception)
async def my_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled exception", exc_info=exc)
    response = JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        response.headers[middleware.REQUEST_ID_HEADER] = request_id
    return response


# Routers — all API routes require an API key; static/index routes below do not.
app.include_router(files.router, dependencies=PROTECTED)
app.include_router(matches.router, dependencies=PROTECTED)
app.include_router(players.router, dependencies=PROTECTED)
app.include_router(generals.router, dependencies=PROTECTED)
app.include_router(teams.router, dependencies=PROTECTED)
app.include_router(maps.router, dependencies=PROTECTED)
app.include_router(draft.router, dependencies=PROTECTED)
app.include_router(superlatives.router, dependencies=PROTECTED)
app.include_router(tournaments.router, dependencies=PROTECTED)
app.include_router(admin.router, dependencies=PROTECTED)

# Public asset routes — reachable without an API key (browser <img> loads).
app.include_router(maps.public_router)


@app.get("/", include_in_schema=False)
def serve_index() -> FileResponse:
    return FileResponse(
        "dist/index.html",
        headers={"Cache-Control": "no-cache"},
    )


app.mount("/", StaticFiles(directory="dist", html=True), name="dist")

exception_handling.setup_error_handling(app)
