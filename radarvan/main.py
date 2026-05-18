"""FastAPI app construction.

Route handlers live in radarvan.routes.*. This module composes them, wires
middleware/exception handlers, and manages the app lifecycle (scheduler,
cache warming, S3 connection test).
"""

import logging
import traceback
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import exception_handling, middleware, replay_files, schedule
from .cache import warm_caches
from .dependencies import IS_DEV, db_manager, verify_api_key
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

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Setup and shutdown of the webserver."""
    logging.basicConfig(level=logging.INFO)
    logger.info("hello")
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
    dependencies=[Depends(verify_api_key)],
)

_DEFAULT_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:8000",
    "https://radarvan-5e9c302c60e6.herokuapp.com",
]
_env_origins = [
    o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()
]
origins = _env_origins or _DEFAULT_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(middleware.RequestTimingMiddleware)


@app.exception_handler(Exception)
async def my_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__, limit=5)
    logger.info("".join(tb_lines))
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Routers
app.include_router(files.router)
app.include_router(matches.router)
app.include_router(players.router)
app.include_router(generals.router)
app.include_router(teams.router)
app.include_router(maps.router)
app.include_router(draft.router)
app.include_router(superlatives.router)
app.include_router(tournaments.router)
app.include_router(admin.router)


@app.get("/", include_in_schema=False)
def serve_index() -> FileResponse:
    return FileResponse(
        "dist/index.html",
        headers={"Cache-Control": "no-cache"},
    )


app.mount("/", StaticFiles(directory="dist", html=True), name="dist")

exception_handling.setup_error_handling(app)
