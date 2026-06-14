"""Discord OAuth2 login and in-game-name selection.

These routes are intentionally *not* behind the X-API-Key dependency: they are
driven by browser navigation and a cookie session, not the generated API
client. Identity lives in a signed session cookie (see SessionMiddleware).
"""

import secrets

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from .. import oauth, users
from ..api_types import AuthStatus, CurrentUser, SelectPlayerRequest
from ..db import User
from ..dependencies import (
    FRONTEND_URL,
    get_current_user,
    get_db_session,
    require_current_user,
)
from ..player_ids import PLAYER_NAMES

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

_OAUTH_STATE_KEY = "oauth_state"
_AVAILABLE_PLAYERS = sorted(PLAYER_NAMES)


def _current_user(user: User) -> CurrentUser:
    return CurrentUser(
        discord_id=user.discord_id,
        discord_username=user.discord_username,
        discord_avatar=user.discord_avatar,
        player_name=user.player_name,
        needs_player_selection=user.player_name is None,
    )


def _logged_in_status(user: User) -> AuthStatus:
    return AuthStatus(
        logged_in=True,
        user=_current_user(user),
        available_players=_AVAILABLE_PLAYERS,
    )


@router.get("/discord/login")
def discord_login(request: Request) -> RedirectResponse:
    """Kick off the OAuth flow: redirect the browser to Discord."""
    if not oauth.is_configured():
        raise HTTPException(status_code=503, detail="Discord login is not configured")
    state = secrets.token_urlsafe(16)
    request.session[_OAUTH_STATE_KEY] = state
    return RedirectResponse(oauth.authorize_url(state))


@router.get("/discord/callback")
async def discord_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    session: Session = Depends(get_db_session),
) -> RedirectResponse:
    """Handle Discord's redirect: validate state, upsert the user, set session."""
    expected = request.session.pop(_OAUTH_STATE_KEY, None)
    if not code or not state or not expected or state != expected:
        raise HTTPException(status_code=400, detail="Invalid OAuth state or code")
    access_token = await oauth.exchange_code(code)
    profile = await oauth.fetch_user(access_token)
    discord_id = str(profile["id"])
    username = profile.get("global_name") or profile.get("username") or "unknown"
    avatar = profile.get("avatar")
    user = users.upsert_discord_user(session, discord_id, username, avatar)
    request.session["user_id"] = user.id
    logger.info("discord login", discord_id=discord_id, user_id=user.id)
    return RedirectResponse(FRONTEND_URL, status_code=303)


@router.get("/me", response_model=AuthStatus)
def me(user: User | None = Depends(get_current_user)) -> AuthStatus:
    """Return the current auth status (logged out, or the user + selectable names)."""
    if user is None:
        return AuthStatus(logged_in=False)
    return _logged_in_status(user)


@router.post("/select_player", response_model=AuthStatus)
def select_player(
    req: SelectPlayerRequest,
    user: User = Depends(require_current_user),
    session: Session = Depends(get_db_session),
) -> AuthStatus:
    """Claim an in-game name (first-login step). Name must be in PLAYER_NAMES."""
    if req.player_name not in PLAYER_NAMES:
        raise HTTPException(status_code=400, detail="Unknown player name")
    existing = users.get_user_by_player_name(session, req.player_name)
    if existing is not None and existing.id != user.id:
        raise HTTPException(
            status_code=409, detail="That player name is already claimed"
        )
    users.set_player_name(session, user, req.player_name)
    return _logged_in_status(user)


@router.post("/logout")
def logout(request: Request) -> dict[str, bool]:
    """Clear the session cookie."""
    request.session.clear()
    return {"ok": True}
