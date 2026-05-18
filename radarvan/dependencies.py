"""Shared FastAPI dependencies and module-level singletons.

Imported by all routers. Keep this module side-effect free aside from the
single DB engine + sessionmaker created at import time.
"""

from collections.abc import Generator
import logging
import os

from fastapi import HTTPException, Request, Response, Security
from fastapi.security import APIKeyHeader

from sqlalchemy.orm import Session

from fastapi import Depends

from .db_utils import DatabaseManager, ReplayManager

logger = logging.getLogger(__name__)

conn_str = os.environ["DATABASE_URL"]
db_manager = DatabaseManager(conn_str)
IS_DEV = os.getenv("DEV") is not None

API_KEYS_READ = set(filter(None, os.getenv("API_KEY_READ", "").split(",")))
API_KEYS_WRITE = set(filter(None, os.getenv("API_KEY_WRITE", "").split(",")))
ENFORCE_AUTH = os.getenv("ENFORCE_AUTH") is not None
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


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
            "Auth not enforced: key_present=%s access=%s method=%s path=%s",
            key is not None,
            access,
            request.method,
            request.url.path,
        )
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
