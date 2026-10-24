from collections.abc import Iterator
import secrets

from fastapi import FastAPI
from fastapi.testclient import TestClient
from opentelemetry import trace
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
import pytest
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request

from radarvan.dependencies import USER_LABEL_SESSION_KEY
from radarvan.request_tags import (
    FRONTEND_CLIENT,
    PAGE_HEADER,
    RequestTagsMiddleware,
)
from radarvan.routes import telemetry

_EXPORTER = InMemorySpanExporter()


@pytest.fixture(scope="module", autouse=True)
def _provider() -> None:
    # The global provider can only be set once per process; FastAPI's native
    # telemetry reads it per request.
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(_EXPORTER))
    trace.set_tracer_provider(provider)


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = FastAPI(telemetry={"auto_configure": False})
    app.add_middleware(RequestTagsMiddleware)
    app.add_middleware(SessionMiddleware, secret_key=secrets.token_hex(16))
    app.include_router(telemetry.router)

    @app.get("/api/ping")
    def ping() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/login/{label}")
    def login(label: str, request: Request) -> dict[str, bool]:
        request.session["user_id"] = 7
        request.session[USER_LABEL_SESSION_KEY] = label
        return {"ok": True}

    _EXPORTER.clear()
    with TestClient(app) as c:
        yield c


def _server_span(path: str) -> ReadableSpan:
    spans = [
        s
        for s in _EXPORTER.get_finished_spans()
        if s.kind == trace.SpanKind.SERVER
        and s.attributes
        and s.attributes.get("url.path") == path
    ]
    assert spans, f"no server span for {path}"
    return spans[-1]


def test_app_request_gets_visitor_page_and_client(client: TestClient) -> None:
    client.get(
        "/api/ping",
        headers={
            "X-Client-Id": FRONTEND_CLIENT,
            PAGE_HEADER: "/player-profile?player=Skip",
            "User-Agent": "Mozilla/5.0",
        },
    )
    attrs = _server_span("/api/ping").attributes or {}
    assert attrs["app.client"] == FRONTEND_CLIENT
    assert attrs["app.page"] == "/player-profile"
    assert attrs["app.page.query"] == "player=Skip"
    assert attrs["user_agent.original"] == "Mozilla/5.0"
    assert attrs["app.api_key_tier"] == "none"
    assert attrs["app.logged_in"] is False
    assert len(str(attrs["app.visitor_id"])) == 16
    assert "enduser.id" not in attrs


def test_visitor_id_persists_in_the_session_cookie(client: TestClient) -> None:
    headers = {"X-Client-Id": FRONTEND_CLIENT}
    client.get("/api/ping", headers=headers)
    first = _server_span("/api/ping").attributes or {}
    client.get("/api/ping", headers=headers)
    second = _server_span("/api/ping").attributes or {}
    assert first["app.visitor_id"] == second["app.visitor_id"]


def test_non_app_callers_get_no_visitor_id(client: TestClient) -> None:
    client.get("/api/ping", headers={"User-Agent": "curl/8"})
    attrs = _server_span("/api/ping").attributes or {}
    assert attrs["app.client"] == "unknown"
    assert "app.visitor_id" not in attrs
    # Nothing written to the session, so Starlette sets no cookie at all.
    assert "session" not in client.cookies


def test_logged_in_user_is_tagged(client: TestClient) -> None:
    client.post("/login/Skip")
    client.get("/api/ping", headers={"X-Client-Id": FRONTEND_CLIENT})
    attrs = _server_span("/api/ping").attributes or {}
    assert attrs["enduser.id"] == "Skip"
    assert attrs["app.user_id"] == 7
    assert attrs["app.logged_in"] is True


def test_page_view_records_the_view_on_its_span(client: TestClient) -> None:
    resp = client.post(
        "/api/page_view",
        json={"path": "/game-night", "query": "date=2026-10-23", "referrer": "/"},
        headers={"X-Client-Id": FRONTEND_CLIENT},
    )
    assert resp.status_code == 204
    attrs = _server_span("/api/page_view").attributes or {}
    assert attrs["app.page_view.path"] == "/game-night"
    assert attrs["app.page_view.query"] == "date=2026-10-23"
    assert attrs["app.page_view.referrer"] == "/"


def test_page_view_rejects_oversized_paths(client: TestClient) -> None:
    resp = client.post("/api/page_view", json={"path": "/" + "x" * 600})
    assert resp.status_code == 422
