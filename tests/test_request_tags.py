from collections.abc import Iterator
import secrets

from fastapi import FastAPI
from fastapi.testclient import TestClient
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
import pytest
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request

from radarvan.request_tags import PAGE_HEADER, VISITOR_HEADER, RequestTagsMiddleware

_EXPORTER = InMemorySpanExporter()
_VISITOR = "3f2a9c1e-7b4d-4e8a-9c0f-1a2b3c4d5e6f"


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

    @app.get("/api/ping")
    def ping() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/login")
    def login(request: Request) -> dict[str, bool]:
        request.session["user_id"] = 7
        return {"ok": True}

    _EXPORTER.clear()
    with TestClient(app) as c:
        yield c


def _ping_attrs() -> dict[str, object]:
    spans = [
        s
        for s in _EXPORTER.get_finished_spans()
        if s.kind == trace.SpanKind.SERVER
        and (s.attributes or {}).get("url.path") == "/api/ping"
    ]
    assert spans, "no server span for /api/ping"
    return dict(spans[-1].attributes or {})


def test_app_request_is_tagged_with_caller_page_and_visitor(
    client: TestClient,
) -> None:
    client.get(
        "/api/ping",
        headers={
            "X-Client-Id": "react-frontend",
            VISITOR_HEADER: _VISITOR,
            PAGE_HEADER: "/player-profile?player=Skip",
            "User-Agent": "Mozilla/5.0",
        },
    )
    attrs = _ping_attrs()
    assert attrs["app.client"] == "react-frontend"
    assert attrs["app.crawler"] is False
    assert attrs["enduser.pseudo.id"] == _VISITOR
    assert attrs["app.page"] == "/player-profile"
    assert attrs["app.page.query"] == "player=Skip"
    assert attrs["user_agent.original"] == "Mozilla/5.0"
    assert "enduser.id" not in attrs


def test_non_app_caller_is_unknown(client: TestClient) -> None:
    client.get("/api/ping", headers={"User-Agent": "curl/8.0"})
    attrs = _ping_attrs()
    assert attrs["app.client"] == "unknown"
    assert "app.page" not in attrs
    assert "enduser.pseudo.id" not in attrs


def test_a_malformed_visitor_header_is_ignored(client: TestClient) -> None:
    client.get("/api/ping", headers={VISITOR_HEADER: "<script>"})
    assert "enduser.pseudo.id" not in _ping_attrs()


def test_logged_in_user_is_tagged_with_their_id(client: TestClient) -> None:
    client.post("/login")
    client.get("/api/ping")
    assert _ping_attrs()["enduser.id"] == "7"
