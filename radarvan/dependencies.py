"""Shared FastAPI dependencies and module-level singletons.

Imported by all routers. Keep this module side-effect free aside from the
single DB engine + sessionmaker created at import time.
"""

from collections.abc import Generator
from enum import StrEnum
import secrets
import structlog
import os

from fastapi import Depends, HTTPException, Request, Response, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from . import db, player_ids
from .auth_notify import API_KEY_HEADER, notify_auth_event
from .db_utils import DatabaseManager, ReplayManager
from .repositories import BracketPredictionRepo, BracketRepo, MapVoteRepo, UserRepo

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


class AccessTier(StrEnum):
    """What an ``X-API-Key`` entitles its holder to.

    Two tiers, not read/write: the split is *privilege*, not HTTP method.
    ``NORMAL`` covers everything the app itself does, including mutations that
    are part of normal play (uploading a replay). ``ADMIN`` covers operational
    endpoints - reparses, backfills, overrides, deletes, cache clears - and is
    opted into per route via ``Depends(require_admin_key)``.
    """

    NONE = "none"
    NORMAL = "normal"
    ADMIN = "admin"


def _keys_from_env(name: str, legacy: str) -> set[str]:
    """Read a comma-separated key list, falling back to the pre-rename var.

    The tiers used to be API_KEY_READ/API_KEY_WRITE. An environment that only
    sets the old names still authenticates (read->normal, write->admin) rather
    than silently configuring *no* keys, which disables auth entirely.
    """
    raw = os.getenv(name)
    if raw is None:
        raw = os.getenv(legacy)
        if raw:
            logger.warning("using deprecated env var; rename it", old=legacy, new=name)
    return set(filter(None, (raw or "").split(",")))


API_KEYS_NORMAL = _keys_from_env("API_KEY_NORMAL", "API_KEY_READ")
API_KEYS_ADMIN = _keys_from_env("API_KEY_ADMIN", "API_KEY_WRITE")
ENFORCE_AUTH = os.getenv("ENFORCE_AUTH") is not None
_api_key_header = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)


def _keys_configured() -> bool:
    return bool(API_KEYS_NORMAL or API_KEYS_ADMIN)


def _resolve_tier(key: str | None) -> AccessTier:
    """Map a presented key to its tier. An admin key also satisfies NORMAL."""
    if key is not None and key in API_KEYS_ADMIN:
        return AccessTier.ADMIN
    if key is not None and key in API_KEYS_NORMAL:
        return AccessTier.NORMAL
    return AccessTier.NONE


async def verify_api_key(
    request: Request,
    response: Response,
    key: str | None = Security(_api_key_header),
) -> None:
    """Baseline gate: any valid key (normal or admin) may pass.

    Applied to whole routers in main.py. It does not care about the HTTP
    method - a route that needs more than this tags itself with
    ``Depends(require_admin_key)``.
    """
    if not _keys_configured():
        return
    tier = _resolve_tier(key)
    response.headers["X-Auth-Valid"] = "true" if tier != AccessTier.NONE else "false"
    response.headers["X-Auth-Access"] = tier.value
    if not ENFORCE_AUTH:
        logger.info(
            "auth not enforced",
            key_present=key is not None,
            access=tier.value,
            method=request.method,
            path=request.url.path,
        )
        if tier == AccessTier.NONE:
            notify_auth_event(
                request, None, "no valid API key, but ENFORCE_AUTH is unset"
            )
        return
    if tier == AccessTier.NONE:
        raise HTTPException(status_code=403, detail="Forbidden")


async def require_admin_key(
    request: Request,
    key: str | None = Security(_api_key_header),
) -> None:
    """Elevated gate: only an admin-tier key may pass.

    Tag operational routes with ``dependencies=ADMIN_ONLY`` - reparse,
    backfill, override, delete, recompute, and anything else that costs real
    work or rewrites stored data. Layers on top of ``verify_api_key``
    (which the router already carries); it repeats the tier check so it is
    also correct on a router that isn't otherwise protected.
    """
    if not _keys_configured():
        return
    tier = _resolve_tier(key)
    if not ENFORCE_AUTH:
        logger.info(
            "admin auth not enforced",
            key_present=key is not None,
            access=tier.value,
            method=request.method,
            path=request.url.path,
        )
        if tier != AccessTier.ADMIN:
            notify_auth_event(
                request, None, "admin key required, but ENFORCE_AUTH is unset"
            )
        return
    if tier != AccessTier.ADMIN:
        raise HTTPException(status_code=403, detail="Admin API key required")


# Tag for elevated routes: `@router.post(..., dependencies=ADMIN_ONLY)`.
ADMIN_ONLY = [Depends(require_admin_key)]


def has_admin_access(key: str | None = Security(_api_key_header)) -> bool:
    """True when the caller holds an admin-tier API key.

    For routes reachable at the normal tier that expose an admin-only *option*
    (see routes/commentary.py's force_refresh, which forces a billed LLM
    call). Mirrors the dependencies' stances: no keys configured at all, or
    auth not enforced, means everything is permitted.
    """
    if not _keys_configured():
        return True
    if not ENFORCE_AUTH:
        return True
    return _resolve_tier(key) == AccessTier.ADMIN


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


def get_bracket_repo(session: Session = Depends(get_db_session)) -> BracketRepo:
    """Dependency that provides a BracketRepo instance."""
    return BracketRepo(session)


def get_bracket_prediction_repo(
    session: Session = Depends(get_db_session),
) -> BracketPredictionRepo:
    """Dependency that provides a BracketPredictionRepo instance."""
    return BracketPredictionRepo(session)


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


def require_admin_login(
    request: Request,
    user: db.User | None = Depends(get_current_user),
) -> None:
    """Admin gate for routes a *browser* reaches: the caller must be logged in
    as a ``player_ids.ADMIN_PLAYERS`` user.

    Use this instead of ``require_admin_key`` when the action is driven from
    the UI. The frontend ships a single API key to every visitor, so an
    admin-tier key can't live there; the signed session cookie identifies an
    actual person. Routes carrying this must be on a router included *without*
    ``verify_api_key`` (the browser sends the cookie, not a key) - see
    ``admin.session_router``.

    An admin-tier API key is accepted too, so scripts and curl keep working;
    that also means the gate is open in dev, where ``has_admin_access`` is
    permissive because no keys are configured. The header is read off the
    request rather than declared as a ``Security`` param on purpose - declaring
    it would advertise APIKeyHeader as this route's security scheme in the
    OpenAPI spec, when the credential callers actually send is the cookie.
    """
    if has_admin_access(request.headers.get(API_KEY_HEADER)):
        return
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if not player_ids.is_admin(user.player_name):
        raise HTTPException(status_code=403, detail="Forbidden")


# Tag for admin routes driven from the UI: `dependencies=ADMIN_LOGIN`.
ADMIN_LOGIN = [Depends(require_admin_login)]


def require_dev() -> None:
    """404s unless running in dev mode (`DEV` env var set).

    For routes that must be genuinely unreachable in prod, not just hidden
    from the OpenAPI docs (`include_in_schema=IS_DEV`, used elsewhere, still
    leaves the route routable). Apply via ``dependencies=[Depends(require_dev)]``.
    """
    if not IS_DEV:
        raise HTTPException(status_code=404, detail="Not found")


def cache_short(response: Response) -> None:
    """Mark a response privately cacheable for 60s.

    For stats/listing endpoints derived from match data: fresh-ish is fine, it
    needn't be up to the minute. ``private`` because these routes are gated by
    X-API-Key and aren't safe for a shared/CDN cache to serve cross-client.
    Apply via ``dependencies=[Depends(cache_short)]``.
    """
    response.headers["Cache-Control"] = "private, max-age=60"
