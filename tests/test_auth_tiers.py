"""API-key auth tiers: normal vs admin.

Two things are pinned here:

1. The dependencies themselves (`verify_api_key`, `require_admin_key`,
   `has_admin_access`) resolve a presented key to the right tier, and enforce
   only when ENFORCE_AUTH is set.
2. Which routes are elevated. Every mutating route in `radarvan.routes` must
   pick one of the three elevated gates or be listed below, so adding an ops
   endpoint without `dependencies=ADMIN_ONLY` / `ADMIN_LOGIN` / `OPS_ADMIN`
   fails this test instead of silently shipping reachable by any key.
3. That the two cookie gates and the routers carrying them stay consistent:
   a route gated on a session cookie must not also sit behind the API key,
   and vice versa.
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
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request
from starlette.responses import Response

from radarvan import dependencies, notify, player_ids, routes
from radarvan.auth_notify import notify_auth_event
from radarvan.db import User
from radarvan.rate_limit import InMemoryRateLimitStore
from radarvan.dependencies import (
    AccessTier,
    has_admin_access,
    require_admin_key,
    require_admin_login,
    require_ops_admin,
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
    path: str = "/api/reparse/1",
    method: str = "POST",
    key: str | None = None,
    forwarded: str | None = None,
) -> Request:
    raw: dict[str, str] = {}
    if key is not None:
        raw["X-API-Key"] = key
    if forwarded is not None:
        raw["x-forwarded-for"] = forwarded
    headers = Headers(raw)
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
    ("POST", "/api/draft/randomize"),  # draft randomization
    ("POST", "/api/predict"),  # win prediction from raw features
}

# Mutating routes on the cookie-session routers whose privilege check is done
# *inside* the handler rather than as a route dependency - see
# player_ids.ADMIN_PLAYERS / TOURNAMENT_ADMINS. The admin/ops routes are not
# listed here: they carry ADMIN_LOGIN / OPS_ADMIN, which `_is_elevated` sees.
COOKIE_AUTH_MUTATIONS = {
    ("POST", "/api/auth/select_player"),
    ("POST", "/api/auth/logout"),
    ("POST", "/api/map_upload"),
    ("POST", "/api/map_vote/{player_count}"),
    ("POST", "/api/map_vote/{player_count}/choose"),
    ("POST", "/api/bracket"),
    ("POST", "/api/bracket/reveal_at"),
    ("POST", "/api/bracket/{match_id}"),
    ("POST", "/api/bracket_games/{match_id}"),
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


# The three elevated gates. ADMIN_ONLY wants an admin-tier key; the other two
# want a logged-in admin (and accept an admin key), and so must live on a
# session router - see `_session_routes`.
ELEVATED_GATES = (require_admin_key, require_admin_login, require_ops_admin)
COOKIE_GATES = (require_admin_login, require_ops_admin)


def _is_elevated(route: APIRoute) -> bool:
    """True if the route opts into any gate above the baseline API key."""
    return any(_tagged_with(route, gate) for gate in ELEVATED_GATES)


def _session_routes() -> set[str]:
    """Paths on every module's ``session_router`` - the routers main.py
    includes *without* ``verify_api_key``, because the credential is a cookie."""
    paths = set()
    for info in pkgutil.iter_modules(routes.__path__):
        module = importlib.import_module(f"{routes.__name__}.{info.name}")
        session_router = getattr(module, "session_router", None)
        if isinstance(session_router, APIRouter):
            paths |= {r.path for r in session_router.routes if isinstance(r, APIRoute)}
    return paths


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
    ungated = {
        (method, route.path)
        for _, route in _all_routes()
        for method in route.methods
        if method not in ("GET", "HEAD", "OPTIONS") and not _is_elevated(route)
    }
    assert ungated == NORMAL_TIER_MUTATIONS | COOKIE_AUTH_MUTATIONS, (
        "a mutating route picks none of the elevated gates and isn't listed as "
        "normal-tier; add dependencies=ADMIN_ONLY (scripts/curl) or OPS_ADMIN "
        "(the admin panel), or add it to NORMAL_TIER_MUTATIONS"
    )


def test_listed_exceptions_still_exist() -> None:
    """The allowlists shouldn't outlive the routes they name."""
    listed = NORMAL_TIER_MUTATIONS | COOKIE_AUTH_MUTATIONS
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
def test_known_ops_routes_are_elevated(path: str) -> None:
    route = next(r for _, r in _all_routes() if r.path == path)
    assert _is_elevated(route)


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
    assert not _is_elevated(route)


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


# --- the ops-admin gate (the control panel) ---------------------------------


def _ops_admin_name() -> str:
    return next(iter(player_ids.OPS_ADMINS))


def test_require_ops_admin_accepts_ops_admin_user(keys: None) -> None:
    require_ops_admin(_request(), User(player_name=_ops_admin_name()))


def test_require_ops_admin_rejects_a_plain_admin(keys: None) -> None:
    """The whole point of the third set: ADMIN_PLAYERS unlocks the debug
    *views*, not scrape/reparse/backfill/delete. An ADMIN_PLAYERS user who is
    not in OPS_ADMINS must be turned away."""
    non_ops_admins = player_ids.ADMIN_PLAYERS - player_ids.OPS_ADMINS
    assert non_ops_admins, "no admin outside OPS_ADMINS left to test the split with"
    for name in non_ops_admins:
        with pytest.raises(HTTPException) as exc:
            require_ops_admin(_request(), User(player_name=name))
        assert exc.value.status_code == 403


def test_require_ops_admin_rejects_non_admin_user(keys: None) -> None:
    with pytest.raises(HTTPException) as exc:
        require_ops_admin(_request(), User(player_name="SomeRandomPlayer"))
    assert exc.value.status_code == 403


def test_require_ops_admin_401s_when_logged_out(keys: None) -> None:
    with pytest.raises(HTTPException) as exc:
        require_ops_admin(_request(), None)
    assert exc.value.status_code == 401


def test_require_ops_admin_rejects_normal_key_without_session(keys: None) -> None:
    """The key the browser ships is normal-tier - it must not be enough."""
    with pytest.raises(HTTPException) as exc:
        require_ops_admin(_request(key=NORMAL_KEY), None)
    assert exc.value.status_code == 401


def test_require_ops_admin_accepts_admin_key_for_scripts(keys: None) -> None:
    """These paths moved off the API-key router; curl with an admin key must
    still reach them, or every ops script breaks."""
    require_ops_admin(_request(key=ADMIN_KEY), None)


def test_ops_admin_is_narrower_than_admin() -> None:
    assert player_ids.OPS_ADMINS < player_ids.ADMIN_PLAYERS


# --- cookie gates and session routers stay in step --------------------------


def _cookie_gated_routes() -> list[tuple[str, APIRoute]]:
    return [
        (module, route)
        for module, route in _all_routes()
        if any(_tagged_with(route, gate) for gate in COOKIE_GATES)
    ]


def test_cookie_gated_routes_exist() -> None:
    """Guard the sweep itself - an empty one would pass the tests below."""
    assert len(_cookie_gated_routes()) > 20


def test_cookie_gated_routes_are_not_behind_the_api_key() -> None:
    """A route gated on the session cookie must live on a ``session_router``,
    which main.py includes without verify_api_key - a browser sends the
    cookie, not an admin key, and would be rejected by the baseline gate
    before its own gate ever ran."""
    session_paths = _session_routes()
    for module, route in _cookie_gated_routes():
        assert route.path in session_paths, f"{module}: {route.path}"


def test_session_routes_all_carry_a_cookie_gate() -> None:
    """The converse: ``session_router`` has no gate of its own, so a route
    parked there without ADMIN_LOGIN/OPS_ADMIN would be wide open."""
    gated = {route.path for _, route in _cookie_gated_routes()}
    assert _session_routes() == gated


def test_cookie_gated_routes_advertise_no_api_key_security() -> None:
    """The cookie is the credential these routes expect, so the OpenAPI spec
    must not name APIKeyHeader as their security scheme (which is what
    declaring the header as a Security param would do)."""
    from radarvan.main import app

    spec = app.openapi()
    for module, route in _cookie_gated_routes():
        for method in route.methods:
            operation = spec["paths"][route.path].get(method.lower())
            if operation is None:
                continue
            assert operation.get("security") is None, f"{module}: {route.path}"


# --- notifying on rejection --------------------------------------------------


@pytest.fixture
def notices(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Capture webhook messages, and start each test with an empty throttle.

    `notify_throttled` resolves `notify_background` through the notify module
    namespace, so patching it there intercepts every path into the webhook.
    """
    sent: list[str] = []
    monkeypatch.setattr(notify, "notify_background", sent.append)
    monkeypatch.setattr(notify, "_throttle_store", InMemoryRateLimitStore())
    return sent


def test_auth_event_reports_who_was_rejected_and_where(notices: list[str]) -> None:
    notify_auth_event(_request(forwarded="1.2.3.4"), 403, "Forbidden")
    assert len(notices) == 1
    assert "rejected 403" in notices[0]
    assert "1.2.3.4" in notices[0]
    assert "/api/reparse/1" in notices[0]
    # No SessionMiddleware behind a bare Request: the message still builds.
    assert "user_id=None" in notices[0]


def test_repeat_rejections_are_throttled(notices: list[str]) -> None:
    """A scanner sweeping one route must not flood the webhook."""
    for _ in range(5):
        notify_auth_event(_request(forwarded="1.2.3.4"), 403, "Forbidden")
    assert len(notices) == 1


def test_throttle_is_per_client_route_and_outcome(notices: list[str]) -> None:
    notify_auth_event(_request(forwarded="1.2.3.4"), 403, "d")
    notify_auth_event(_request(forwarded="5.6.7.8"), 403, "d")
    notify_auth_event(_request(path="/api/other", forwarded="1.2.3.4"), 403, "d")
    notify_auth_event(_request(forwarded="1.2.3.4"), 401, "d")
    assert len(notices) == 4


def test_a_scan_across_distinct_urls_is_capped(notices: list[str]) -> None:
    """Per-key dedupe alone doesn't stop a sweep - every URL is a fresh key -
    so the global budget is what bounds the damage."""
    for i in range(200):
        notify_auth_event(
            _request(path=f"/api/probe/{i}", forwarded="1.2.3.4"), 403, "d"
        )
    assert len(notices) == notify.THROTTLE_BUDGET_PER_WINDOW


@pytest.mark.parametrize(("status", "expected"), [(401, 1), (403, 1), (404, 0)])
def test_handler_notifies_only_on_auth_rejections(
    notices: list[str], status: int, expected: int
) -> None:
    """Catching this centrally is what makes it total - no gate has to remember
    to notify, whichever module raised. The handler owns every other status
    too, so a 404 must still get its normal response and no webhook call.
    """
    from radarvan.main import handle_http_exception

    response = run(
        handle_http_exception(
            _request(forwarded="1.2.3.4"),
            StarletteHTTPException(status_code=status, detail="Nope"),
        )
    )
    assert response.status_code == status
    assert len(notices) == expected


def test_unenforced_missing_key_notifies_without_rejecting(
    keys: None, monkeypatch: pytest.MonkeyPatch, notices: list[str]
) -> None:
    """Observe-only mode is the one case that notifies about a request it let
    through - knowing what *would* have been blocked is the point of it."""
    monkeypatch.setattr(dependencies, "ENFORCE_AUTH", False)
    run(verify_api_key(_request(forwarded="1.2.3.4"), Response(), None))
    assert len(notices) == 1
    assert "allowed" in notices[0]
