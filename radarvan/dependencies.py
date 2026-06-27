"""Shared FastAPI dependencies and module-level singletons.

Imported by all routers. Keep this module side-effect free aside from the
single DB engine + sessionmaker created at import time.
"""

import asyncio
from collections.abc import Generator
import secrets
import structlog
import os

from fastapi import Depends, HTTPException, Request, Response, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from . import db
from .db_utils import DatabaseManager, ReplayManager
from .notify import notify
from .repositories import MapVoteRepo, UserRepo

logger = structlog.get_logger(__name__)

conn_str = os.environ["DATABASE_URL"]
db_manager = DatabaseManager(conn_str)
IS_DEV = os.getenv("DEV") is not None

# Secret used to sign the session cookie (Starlette SessionMiddleware). Set
# SESSION_SECRET in every real environment; the random fallback keeps dev
# working but invalidates all sessions on each process restart.
_session_secret = os.getenv("SESSION_SECRET")
if not _session_secret:
    logger.warning("SESSION_SECRET not set; using an ephemeral per-process secret")
    _session_secret = secrets.token_urlsafe(32)
SESSION_SECRET: str = _session_secret

# Where to send the browser after a successful Discord login (the SPA root).
FRONTEND_URL = os.getenv("FRONTEND_URL", "/")

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


def get_user_repo(session: Session = Depends(get_db_session)) -> UserRepo:
    """Dependency that provides a UserRepo instance."""
    return UserRepo(session)


def get_map_vote_repo(session: Session = Depends(get_db_session)) -> MapVoteRepo:
    """Dependency that provides a MapVoteRepo instance."""
    return MapVoteRepo(session)


def get_current_user(
    request: Request, repo: UserRepo = Depends(get_user_repo)
) -> db.User | None:
    """Resolve the logged-in user from the signed session cookie, or None.

    Requires SessionMiddleware (added in main.py) so ``request.session`` exists.
    """
    user_id = request.session.get("user_id")
    if user_id is None:
        return None
    return repo.get_by_id(user_id)


def require_current_user(
    user: db.User | None = Depends(get_current_user),
) -> db.User:
    """Like get_current_user but 401s when no user is authenticated."""
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def cache_short(response: Response) -> None:
    """Mark a response privately cacheable for 60s.

    For stats/listing endpoints derived from match data: fresh-ish is fine, it
    needn't be up to the minute. ``private`` because these routes are gated by
    X-API-Key and aren't safe for a shared/CDN cache to serve cross-client.
    Apply via ``dependencies=[Depends(cache_short)]``.
    """
    response.headers["Cache-Control"] = "private, max-age=60"
