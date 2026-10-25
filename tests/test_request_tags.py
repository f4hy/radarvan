import asyncio
from collections.abc import Iterator
import secrets

from fastapi import FastAPI
from fastapi.testclient import TestClient
import httpx
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
from radarvan.request_tags import PAGE_HEADER, VISITOR_HEADER, RequestTagsMiddleware
from radarvan.routes import telemetry

_EXPORTER = InMemorySpanExporter()
_APP_HEADERS = {"X-Client-Id": "react-frontend"}
_VISITOR = "3f2a9c1e-7b4d-4e8a-9c0f-1a2b3c4d5e6f"


@pytest.fixture(scope="module", autouse=True)
def _provider() -> None:
    # The global provider can only be set once per process; FastAPI's native
    # telemetry reads it per request.
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(_EXPORTER))
    trace.set_tracer_provider(provider)


@pytest.fixture
def app() -> FastAPI:
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

    @app.post("/logout")
    def logout(request: Request) -> dict[str, bool]:
        request.session.clear()
        return {"ok": True}

    _EXPORTER.clear()
    return app


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


def _server_spans(path: str) -> list[ReadableSpan]:
    return [
        s
        for s in _EXPORTER.get_finished_spans()
        if s.kind == trace.SpanKind.SERVER
        and s.attributes
        and s.attributes.get("url.path") == path
    ]


def _attrs(path: str) -> dict[str, object]:
    spans = _server_spans(path)
    assert spans, f"no server span for {path}"
    return dict(spans[-1].attributes or {})


def test_app_request_is_tagged_with_caller_page_and_visitor(
    client: TestClient,
) -> None:
    client.get(
        "/api/ping",
        headers={
            **_APP_HEADERS,
            VISITOR_HEADER: _VISITOR,
            PAGE_HEADER: "/player-profile?player=Skip",
            "User-Agent": "Mozilla/5.0",
        },
    )
    attrs = _attrs("/api/ping")
    assert attrs["app.client"] == "react-frontend"
    assert attrs["enduser.pseudo.id"] == _VISITOR
    assert attrs["app.page"] == "/player-profile"
    assert attrs["app.page.query"] == "player=Skip"
    assert attrs["user_agent.original"] == "Mozilla/5.0"
    assert attrs["app.api_key_tier"] == "none"
    assert attrs["app.logged_in"] is False
    assert "enduser.id" not in attrs


def test_a_malformed_visitor_header_is_ignored(client: TestClient) -> None:
    client.get("/api/ping", headers={VISITOR_HEADER: "<script>"})
    assert "enduser.pseudo.id" not in _attrs("/api/ping")


def test_concurrent_first_requests_agree_and_write_no_cookie(app: FastAPI) -> None:
    # A first page load fires several requests at once with no cookie yet. If
    # tagging wrote the session, each would race to set its own.
    async def burst() -> list[httpx.Response]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as c:
            headers = {**_APP_HEADERS, VISITOR_HEADER: _VISITOR}
            return await asyncio.gather(
                *(c.get("/api/ping", headers=headers) for _ in range(5))
            )

    responses = asyncio.run(burst())
    assert all("set-cookie" not in r.headers for r in responses)
    spans = _server_spans("/api/ping")
    assert len(spans) == 5
    assert {(s.attributes or {})["enduser.pseudo.id"] for s in spans} == {_VISITOR}


def test_login_span_carries_the_identity_it_creates(client: TestClient) -> None:
    client.post("/login/Skip", headers=_APP_HEADERS)
    attrs = _attrs("/login/Skip")
    assert attrs["enduser.id"] == "7"
    assert attrs["app.user.name"] == "Skip"
    assert attrs["app.logged_in"] is True


def test_logged_in_user_is_tagged_with_stable_id_and_name(
    client: TestClient,
) -> None:
    client.post("/login/Skip")
    client.get("/api/ping", headers=_APP_HEADERS)
    attrs = _attrs("/api/ping")
    assert attrs["enduser.id"] == "7"
    assert attrs["app.user.name"] == "Skip"


def test_logout_span_keeps_who_logged_out(client: TestClient) -> None:
    client.post("/login/Skip")
    client.post("/logout")
    attrs = _attrs("/logout")
    assert attrs["enduser.id"] == "7"
    assert attrs["app.logged_in"] is False


def test_page_view_records_the_view_on_its_span(client: TestClient) -> None:
    resp = client.post(
        "/api/page_view",
        json={"path": "/game-night", "query": "date=2026-10-23", "referrer": "/"},
        headers=_APP_HEADERS,
    )
    assert resp.status_code == 204
    attrs = _attrs("/api/page_view")
    assert attrs["app.page_view.path"] == "/game-night"
    assert attrs["app.page_view.query"] == "date=2026-10-23"
    assert attrs["app.page_view.referrer"] == "/"


def test_page_view_rejects_oversized_paths(client: TestClient) -> None:
    resp = client.post("/api/page_view", json={"path": "/" + "x" * 600})
    assert resp.status_code == 422
