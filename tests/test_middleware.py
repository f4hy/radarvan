from collections.abc import Iterator

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.testclient import TestClient
import pytest
import structlog

from radarvan.middleware import REQUEST_ID_HEADER, RateLimit, RequestContextMiddleware

_LIMIT = 2


def _app() -> FastAPI:
    app = FastAPI(dependencies=[Depends(RateLimit(limit_per_minute=_LIMIT))])
    app.add_middleware(RequestContextMiddleware)

    @app.get("/api/ping")
    def ping() -> dict[str, object]:
        return {"ctx": structlog.contextvars.get_contextvars()}

    @app.get("/api/map_image/{name}")
    def map_image(name: str) -> dict[str, str]:
        return {"name": name}

    @app.get("/api/redirect")
    def redirect() -> RedirectResponse:
        return RedirectResponse("/elsewhere")

    @app.get("/api/missing")
    def missing() -> None:
        raise HTTPException(status_code=404)

    @app.get("/page")
    def page() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/api/whoami")
    def whoami(request: Request) -> dict[str, str]:
        return {"request_id": request.state.request_id}

    return app


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(_app()) as c:
        yield c


def test_request_id_is_echoed_and_bound_for_logging(client: TestClient) -> None:
    resp = client.get(
        "/api/ping", headers={REQUEST_ID_HEADER: "abc", "X-Client-Id": "react"}
    )
    assert resp.headers[REQUEST_ID_HEADER] == "abc"
    assert resp.json()["ctx"] == {"request_id": "abc", "client": "react"}


def test_request_id_is_generated_and_shared_with_state(client: TestClient) -> None:
    resp = client.get("/api/whoami")
    assert resp.headers[REQUEST_ID_HEADER] == resp.json()["request_id"]


def test_headers_reach_error_and_raw_responses(client: TestClient) -> None:
    for path in ("/api/missing", "/api/redirect"):
        resp = client.get(path, follow_redirects=False)
        assert REQUEST_ID_HEADER in resp.headers, path
        assert resp.headers["X-Robots-Tag"] == "noindex", path


def test_noindex_spares_map_images_and_pages(client: TestClient) -> None:
    assert "X-Robots-Tag" not in client.get("/api/map_image/foo").headers
    assert "X-Robots-Tag" not in client.get("/page").headers


def test_over_the_limit_is_429_with_retry_after(client: TestClient) -> None:
    for _ in range(_LIMIT):
        assert client.get("/api/ping").status_code == 200
    resp = client.get("/api/ping")
    assert resp.status_code == 429
    assert int(resp.headers["Retry-After"]) >= 1
    assert resp.headers["X-RateLimit-Remaining"] == "0"
    assert REQUEST_ID_HEADER in resp.headers


def test_non_api_paths_are_never_limited(client: TestClient) -> None:
    for _ in range(_LIMIT + 3):
        assert client.get("/page").status_code == 200


def test_clients_are_limited_separately(client: TestClient) -> None:
    for _ in range(_LIMIT):
        client.get("/api/ping", headers={"X-Forwarded-For": "1.1.1.1"})
    assert (
        client.get("/api/ping", headers={"X-Forwarded-For": "2.2.2.2"}).status_code
        == 200
    )


def test_zero_disables_the_limit() -> None:
    app = FastAPI(dependencies=[Depends(RateLimit(limit_per_minute=0))])

    @app.get("/api/ping")
    def ping() -> dict[str, bool]:
        return {"ok": True}

    with TestClient(app) as c:
        assert all(c.get("/api/ping").status_code == 200 for _ in range(5))
