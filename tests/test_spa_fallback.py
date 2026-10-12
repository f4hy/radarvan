"""The static mount must serve the app shell for client-routed paths.

The frontend routes on the path (``/game-night``, not ``/?page=game-night``), so
a hard refresh or a pasted link lands on a path with no file behind it. What the
fallback must *not* swallow is an API 404 or a missing hashed asset - both are
real answers, and turning either into HTML hides the failure somewhere worse.
"""

import pytest
from fastapi.testclient import TestClient

from radarvan import seo
from radarvan.main import app


@pytest.fixture(autouse=True)
def _no_db(monkeypatch: pytest.MonkeyPatch) -> None:
    # The shell's per-page tags read the corpus; without one they degrade to
    # page-level tags, which is all these tests look at.
    monkeypatch.setattr(seo, "load_index", lambda: None)


@pytest.fixture(scope="module")
def client() -> TestClient:
    # Not context-managed: the lifespan warms caches against a real database.
    # Static serving needs none of that.
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize(
    "path",
    [
        "/game-night",
        "/player-profile",
        "/head-to-head",
        "/matches",
    ],
)
def test_a_client_route_serves_the_app_shell(client: TestClient, path: str) -> None:
    resp = client.get(path)
    assert resp.status_code == 200, f"{path} should serve index.html"
    assert resp.headers["content-type"].startswith("text/html")
    assert '<div id="root">' in resp.text
    # index.html must always revalidate - it names the current build's bundles.
    assert resp.headers["cache-control"] == "no-cache"


def test_an_unknown_path_is_a_404_that_still_renders_the_app(
    client: TestClient,
) -> None:
    """The client draws its own not-found, but crawlers need the real status."""
    resp = client.get("/no-such-page")
    assert resp.status_code == 404
    assert '<div id="root">' in resp.text


def test_query_string_links_redirect_to_the_path_form(client: TestClient) -> None:
    """The old ``?page=`` links pasted into chat keep working."""
    resp = client.get("/?page=game-night&date=2026-08-28", follow_redirects=False)
    assert resp.status_code == 301
    assert resp.headers["location"] == "/game-night?date=2026-08-28"


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
