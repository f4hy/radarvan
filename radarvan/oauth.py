"""Discord OAuth2 (authorization-code flow) configuration and helpers.

We talk to Discord directly with httpx2 rather than pulling in a full OAuth
client library. The flow:

1. Redirect the browser to Discord's authorize URL with a CSRF ``state``.
2. Discord redirects back to our callback with a ``code``.
3. We exchange the ``code`` for an access token (server-to-server).
4. We fetch the user's Discord identity with that token.

All configuration comes from environment variables (see ``auth.md``).
"""

import os
from functools import cache
from urllib.parse import urlencode

import httpx2

DISCORD_API_BASE = "https://discord.com/api"
DISCORD_AUTHORIZE_URL = "https://discord.com/oauth2/authorize"
DISCORD_TOKEN_URL = f"{DISCORD_API_BASE}/oauth2/token"
DISCORD_USER_URL = f"{DISCORD_API_BASE}/users/@me"

CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")
# Must exactly match a redirect URI registered on the Discord application and
# point at our /api/auth/discord/callback route (through the dev proxy in dev,
# same-origin in prod). See auth.md.
REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "")
# "identify" is enough to read the user's id + username; we don't need email.
SCOPE = "identify"

_HTTP_TIMEOUT = 10.0


@cache
def _client() -> httpx2.AsyncClient:
    """Process-wide async client, reused across the two back-to-back Discord
    calls in one login (token exchange then user fetch hit the same host)."""
    return httpx2.AsyncClient(timeout=_HTTP_TIMEOUT)


def is_configured() -> bool:
    """True only when every credential needed for the OAuth dance is present."""
    return bool(CLIENT_ID and CLIENT_SECRET and REDIRECT_URI)


def authorize_url(state: str) -> str:
    """Build the Discord authorize URL the browser is redirected to."""
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPE,
        "state": state,
        "prompt": "consent",
    }
    return f"{DISCORD_AUTHORIZE_URL}?{urlencode(params)}"


async def exchange_code(code: str) -> str:
    """Exchange an authorization code for a Discord access token."""
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }
    resp = await _client().post(
        DISCORD_TOKEN_URL,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    resp.raise_for_status()
    return str(resp.json()["access_token"])


async def fetch_user(access_token: str) -> dict[str, str]:
    """Fetch the authenticated user's Discord profile (id, username, avatar)."""
    resp = await _client().get(
        DISCORD_USER_URL,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    resp.raise_for_status()
    return dict(resp.json())
