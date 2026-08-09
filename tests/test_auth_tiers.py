"""API-key auth tiers: normal vs admin.

Two things are pinned here:

1. The dependencies themselves (`verify_api_key`, `require_admin_key`,
   `has_admin_access`) resolve a presented key to the right tier, and enforce
   only when ENFORCE_AUTH is set.
2. Which routes are elevated. Every mutating route in `radarvan.routes` must
   be admin-tagged or listed below, so adding an ops endpoint without
   `dependencies=ADMIN_ONLY` fails this test instead of silently shipping
   reachable by any key.
"""

import asyncio
import importlib
import pkgutil
from collections.abc import Coroutine
from typing import Any, TypeVar

import pytest
from fastapi import APIRouter, HTTPException
from fastapi.params import Depends as DependsParam
from fastapi.routing import APIRoute
from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.responses import Response

from radarvan import dependencies, player_ids, routes
from radarvan.db import User
from radarvan.routes import admin
from radarvan.dependencies import (
    AccessTier,
    has_admin_access,
    require_admin_key,
    require_admin_login,
    verify_api_key,
)

NORMAL_KEY = "normal-key"
ADMIN_KEY = "admin-key"

T = TypeVar("T")


def run(coro: Coroutine[Any, Any, T]) -> T:
    return asyncio.run(coro)


@pytest.fixture
def keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dependencies, "API_KEYS_NORMAL", {NORMAL_KEY})
    monkeypatch.setattr(dependencies, "API_KEYS_ADMIN", {ADMIN_KEY})
    monkeypatch.setattr(dependencies, "ENFORCE_AUTH", True)


def _request(
    path: str = "/api/reparse/1", method: str = "POST", key: str | None = None
) -> Request:
    headers = Headers({} if key is None else {"X-API-Key": key})
    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "headers": headers.raw,
            "query_string": b"",
        }
    )


# --- the dependencies themselves -------------------------------------------


@pytest.mark.parametrize(
    ("key", "tier"),
    [
        (ADMIN_KEY, AccessTier.ADMIN),
        (NORMAL_KEY, AccessTier.NORMAL),
        ("nonsense", AccessTier.NONE),
        (None, AccessTier.NONE),
    ],
)
def test_resolve_tier(keys: None, key: str | None, tier: AccessTier) -> None:
    assert dependencies._resolve_tier(key) == tier


@pytest.mark.parametrize("key", [NORMAL_KEY, ADMIN_KEY])
def test_verify_api_key_accepts_any_tier(keys: None, key: str) -> None:
    """The baseline gate no longer cares about the HTTP method: a normal key
    may POST (uploading a replay is normal-tier)."""
    response = Response()
    run(verify_api_key(_request(method="POST"), response, key))
    assert response.headers["X-Auth-Valid"] == "true"


def test_verify_api_key_rejects_unknown_key(keys: None) -> None:
    with pytest.raises(HTTPException) as exc:
        run(verify_api_key(_request(), Response(), "nonsense"))
    assert exc.value.status_code == 403


def test_require_admin_key_rejects_normal_tier(keys: None) -> None:
    with pytest.raises(HTTPException) as exc:
        run(require_admin_key(_request(), NORMAL_KEY))
    assert exc.value.status_code == 403


def test_require_admin_key_accepts_admin_tier(keys: None) -> None:
    run(require_admin_key(_request(), ADMIN_KEY))


def test_nothing_enforced_without_enforce_auth(
    keys: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ENFORCE_AUTH unset = observe-and-log only, for both tiers."""
    monkeypatch.setattr(dependencies, "ENFORCE_AUTH", False)
    run(verify_api_key(_request(), Response(), None))
    run(require_admin_key(_request(), None))
    assert has_admin_access(None) is True


def test_no_keys_configured_is_wide_open(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dependencies, "API_KEYS_NORMAL", set())
    monkeypatch.setattr(dependencies, "API_KEYS_ADMIN", set())
    monkeypatch.setattr(dependencies, "ENFORCE_AUTH", True)
    run(verify_api_key(_request(), Response(), None))
    run(require_admin_key(_request(), None))
    assert has_admin_access(None) is True


def test_has_admin_access(keys: None) -> None:
    assert has_admin_access(ADMIN_KEY) is True
    assert has_admin_access(NORMAL_KEY) is False
    assert has_admin_access(None) is False


# --- which routes are elevated ---------------------------------------------

# Mutating API-key routes deliberately left at the normal tier: part of normal
# play, or read-shaped POSTs (a query that needs a request body).
NORMAL_TIER_MUTATIONS = {
    ("POST", "/api/upload_replay"),  # the game client's ingestion path
    ("POST", "/api/map_summary/"),  # pre-game summary for a hypothetical matchup
    ("POST", "/api/map_render"),  # renders an overlay from a posted payload
    ("POST", "/api/draft/randomize"),  # draft randomization
    ("POST", "/api/predict"),  # win prediction from raw features
}

# Admin actions the UI drives: gated on a logged-in ADMIN_PLAYERS user
# (dependencies=ADMIN_LOGIN) rather than an admin key, because the browser only
# ever ships a normal-tier key.
ADMIN_LOGIN_MUTATIONS = {
    ("POST", "/api/reparse/{match_id}"),
}

# Mutating routes on the cookie-session routers (not behind X-API-Key at all).
# Their privilege check is a logged-in user, done inside the handler - see
# player_ids.ADMIN_PLAYERS / TOURNAMENT_ADMINS.
COOKIE_AUTH_MUTATIONS = {
    ("POST", "/api/auth/select_player"),
    ("POST", "/api/auth/logout"),
    ("POST", "/api/map_upload"),
    ("POST", "/api/map_vote/{player_count}"),
    ("POST", "/api/map_vote/{player_count}/choose"),
    ("POST", "/api/bracket"),
    ("POST", "/api/bracket/reveal_at"),
    ("POST", "/api/bracket/{match_id}"),
    ("POST", "/api/bracket_predictions/{match_id}"),
}


def _all_routes() -> list[tuple[str, APIRoute]]:
    """Every APIRoute declared in radarvan.routes, with its module name."""
    found = []
    for info in pkgutil.iter_modules(routes.__path__):
        module = importlib.import_module(f"{routes.__name__}.{info.name}")
        for attr in vars(module).values():
            if isinstance(attr, APIRouter):
                found += [
                    (info.name, r) for r in attr.routes if isinstance(r, APIRoute)
                ]
    return found


def _tagged_with(route: APIRoute, dependency: object) -> bool:
    return any(
        isinstance(d, DependsParam) and d.dependency is dependency
        for d in route.dependencies
    )


def _is_admin_tagged(route: APIRoute) -> bool:
    return _tagged_with(route, require_admin_key)


def _mutations() -> set[tuple[str, str]]:
    return {
        (method, route.path)
        for _, route in _all_routes()
        for method in route.methods
        if method not in ("GET", "HEAD", "OPTIONS")
    }


def test_routes_were_actually_collected() -> None:
    """Guard the introspection itself: an empty sweep would pass everything."""
    assert len(_all_routes()) > 50


def test_every_mutating_route_picks_a_tier() -> None:
    untagged = {
        (method, route.path)
        for _, route in _all_routes()
        for method in route.methods
        if method not in ("GET", "HEAD", "OPTIONS") and not _is_admin_tagged(route)
    }
    assert (
        untagged
        == NORMAL_TIER_MUTATIONS | COOKIE_AUTH_MUTATIONS | ADMIN_LOGIN_MUTATIONS
    ), (
        "a mutating route is neither admin-tagged nor listed as normal-tier; "
        "add dependencies=ADMIN_ONLY, or add it to NORMAL_TIER_MUTATIONS"
    )


def test_listed_exceptions_still_exist() -> None:
    """The allowlists shouldn't outlive the routes they name."""
    listed = NORMAL_TIER_MUTATIONS | COOKIE_AUTH_MUTATIONS | ADMIN_LOGIN_MUTATIONS
    assert listed <= _mutations()


@pytest.mark.parametrize(
    "path",
    [
        "/api/scrape/{days}",
        "/api/set_override/",
        "/api/backfill_player_roles/",
        "/api/superlatives/recompute",
        "/api/reparse_maps",
        "/api/register_replay_url",
    ],
)
def test_known_ops_routes_are_admin(path: str) -> None:
    route = next(r for _, r in _all_routes() if r.path == path)
    assert _is_admin_tagged(route)


@pytest.mark.parametrize(
    "path",
    [
        "/api/matches/by_date/{date}",
        "/api/details/{match_id}",
        "/api/playerstats",
        "/api/debug/match/{match_id}",
        "/api/overrides",
    ],
)
def test_reads_stay_normal_tier(path: str) -> None:
    """Read-only routes are never elevated - including the debug listings the
    DebugData page loads with the browser's normal-tier key."""
    route = next(r for _, r in _all_routes() if r.path == path)
    assert not _is_admin_tagged(route)


# --- admin actions the UI drives -------------------------------------------


def _admin_name() -> str:
    return next(iter(player_ids.ADMIN_PLAYERS))


def test_require_admin_login_accepts_admin_user(keys: None) -> None:
    require_admin_login(_request(), User(player_name=_admin_name()))


def test_require_admin_login_rejects_non_admin_user(keys: None) -> None:
    with pytest.raises(HTTPException) as exc:
        require_admin_login(_request(), User(player_name="SomeRandomPlayer"))
    assert exc.value.status_code == 403


def test_require_admin_login_rejects_normal_key_without_session(keys: None) -> None:
    """The key the browser ships is normal-tier - it must not be enough."""
    with pytest.raises(HTTPException) as exc:
        require_admin_login(_request(key=NORMAL_KEY), None)
    assert exc.value.status_code == 401


def test_require_admin_login_401s_when_logged_out(keys: None) -> None:
    with pytest.raises(HTTPException) as exc:
        require_admin_login(_request(), None)
    assert exc.value.status_code == 401


def test_require_admin_login_accepts_admin_key_for_scripts(keys: None) -> None:
    """curl/ops keep working without a session."""
    require_admin_login(_request(key=ADMIN_KEY), None)


def test_require_admin_login_open_in_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    """No keys configured (the dev default) = permissive, like every other
    gate here - so local curl and a logged-out DebugData still work."""
    monkeypatch.setattr(dependencies, "API_KEYS_NORMAL", set())
    monkeypatch.setattr(dependencies, "API_KEYS_ADMIN", set())
    require_admin_login(_request(), None)


def test_ui_admin_routes_are_login_tagged() -> None:
    for _, path in ADMIN_LOGIN_MUTATIONS:
        route = next(r for _, r in _all_routes() if r.path == path)
        assert _tagged_with(route, require_admin_login)


def test_ui_admin_routes_advertise_no_api_key_security() -> None:
    """The cookie is the credential these routes expect, so the OpenAPI spec
    must not name APIKeyHeader as their security scheme (which is what
    declaring the header as a Security param would do)."""
    from radarvan.main import app

    spec = app.openapi()
    for method, path in ADMIN_LOGIN_MUTATIONS:
        operation = spec["paths"][path][method.lower()]
        assert operation.get("security") is None, path


def test_ui_admin_routes_are_not_behind_the_api_key() -> None:
    """They must live on admin.session_router, which main.py includes without
    verify_api_key - a browser sends the cookie, not an admin key."""
    session_paths = {
        r.path for r in admin.session_router.routes if isinstance(r, APIRoute)
    }
    assert {path for _, path in ADMIN_LOGIN_MUTATIONS} == session_paths
