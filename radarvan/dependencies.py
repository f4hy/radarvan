"""Shared FastAPI dependencies and module-level singletons.

Imported by all routers. Keep this module side-effect free aside from the
single DB engine + sessionmaker created at import time.
"""

import asyncio
from collections.abc import Generator
import structlog
import os

from fastapi import Depends, HTTPException, Request, Response, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from .db_utils import DatabaseManager, ReplayManager
from .notify import notify

logger = structlog.get_logger(__name__)

conn_str = os.environ["DATABASE_URL"]
db_manager = DatabaseManager(conn_str)
IS_DEV = os.getenv("DEV") is not None

API_KEYS_READ = set(filter(None, os.getenv("API_KEY_READ", "").split(",")))
API_KEYS_WRITE = set(filter(None, os.getenv("API_KEY_WRITE", "").split(",")))
ENFORCE_AUTH = os.getenv("ENFORCE_AUTH") is not None
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Keep strong refs to in-flight fire-and-forget tasks so they aren't GC'd mid-await.
_background_tasks: set[asyncio.Task[None]] = set()


async def verify_api_key(
    request: Request,
    response: Response,
    key: str | None = Security(_api_key_header),
) -> None:
    if not API_KEYS_READ and not API_KEYS_WRITE:
        return
    if key in API_KEYS_WRITE:
        access = "write"
    elif key in API_KEYS_READ:
        access = "read"
    else:
        access = "none"
    response.headers["X-Auth-Valid"] = "true" if access != "none" else "false"
    response.headers["X-Auth-Access"] = access
    is_write_method = request.method not in ("GET", "HEAD", "OPTIONS")
    if not ENFORCE_AUTH:
        logger.info(
            "auth not enforced",
            key_present=key is not None,
            access=access,
            method=request.method,
            path=request.url.path,
        )
        if access == "none":
            task = asyncio.create_task(
                asyncio.to_thread(
                    notify,
                    f"Call to {request.url.path} not authenticated. Check auth",
                )
            )
            _background_tasks.add(task)
            task.add_done_callback(_background_tasks.discard)
        return
    if access == "none":
        raise HTTPException(status_code=403, detail="Forbidden")
    if is_write_method and access != "write":
        raise HTTPException(status_code=403, detail="Forbidden")


def get_db_session() -> Generator[Session]:
    """Dependency that provides a database session.

    Automatically handles commit/rollback and cleanup.
    """
    session = db_manager.SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_replay_manager(session: Session = Depends(get_db_session)) -> ReplayManager:
    """Dependency that provides a ReplayManager instance."""
    return ReplayManager(session, notify=True)


def cache_short(response: Response) -> None:
    """Mark a response privately cacheable for 60s.

    For stats/listing endpoints derived from match data: fresh-ish is fine, it
    needn't be up to the minute. ``private`` because these routes are gated by
    X-API-Key and aren't safe for a shared/CDN cache to serve cross-client.
    Apply via ``dependencies=[Depends(cache_short)]``.
    """
    response.headers["Cache-Control"] = "private, max-age=60"
