"""The static mount must serve the app shell for client-routed paths.

The frontend routes on the path (``/game-night``, not ``/?page=game-night``), so
a hard refresh or a pasted link lands on a path with no file behind it. What the
fallback must *not* swallow is an API 404 or a missing hashed asset - both are
real answers, and turning either into HTML hides the failure somewhere worse.
"""

import pytest
from fastapi.testclient import TestClient

from radarvan.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    # Not context-managed: the lifespan starts the scheduler and warms caches
    # against a real database. Static serving needs none of that.
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize(
    "path",
    [
        "/game-night",
        "/player-profile",
        "/head-to-head",
        "/matches",
        # A path the router doesn't know either: still the app's to answer, and
        # it renders the client's own not-found rather than the server's.
        "/no-such-page",
    ],
)
def test_a_client_route_serves_the_app_shell(client: TestClient, path: str) -> None:
    resp = client.get(path)
    assert resp.status_code == 200, f"{path} should serve index.html"
    assert resp.headers["content-type"].startswith("text/html")
    assert '<div id="root">' in resp.text
    # index.html must always revalidate - it names the current build's bundles.
    assert resp.headers["cache-control"] == "no-cache"


def test_query_string_links_still_reach_the_shell(client: TestClient) -> None:
    """The old ``?page=`` links pasted into chat resolve at the root, which has
    a real index.html; the client redirects them to the path form."""
    resp = client.get("/?page=game-night&date=2026-08-28")
    assert resp.status_code == 200
    assert '<div id="root">' in resp.text


def test_an_unknown_api_path_still_404s_as_json(client: TestClient) -> None:
    """The mount is registered last, so an unmatched /api path lands here. It
    must keep its JSON 404 rather than being handed the HTML shell."""
    resp = client.get("/api/no_such_endpoint")
    assert resp.status_code == 404
    assert not resp.headers["content-type"].startswith("text/html")


def test_a_missing_hashed_asset_404s(client: TestClient) -> None:
    """A miss under /assets/ means index.html names a build that is gone.
    Serving HTML there would surface as a JS syntax error instead of a 404."""
    resp = client.get("/assets/index-DoesNotExist.js")
    assert resp.status_code == 404
    assert not resp.headers["content-type"].startswith("text/html")
