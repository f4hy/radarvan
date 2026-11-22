import httpx
from opentelemetry.instrumentation.httpx import RequestInfo
from opentelemetry.sdk.trace import TracerProvider

from radarvan.tracing import _redact_span_url, redact_url

WEBHOOK = "https://discord.com/api/webhooks/1234567890/s3cr3t-T0ken_x"


def test_redact_url_hides_webhook_token() -> None:
    assert redact_url(WEBHOOK) == "https://discord.com/api/webhooks/1234567890/REDACTED"
    assert (
        redact_url(WEBHOOK + "?wait=true")
        == "https://discord.com/api/webhooks/1234567890/REDACTED?wait=true"
    )


def test_redact_url_leaves_other_urls_alone() -> None:
    for url in (
        "https://cncstats.computersrfun.org/replay",
        "https://discord.com/api/oauth2/token",
    ):
        assert redact_url(url) == url


def test_request_hook_rewrites_span_url() -> None:
    tracer = TracerProvider().get_tracer(__name__)
    request = RequestInfo(b"POST", httpx.URL(WEBHOOK), httpx.Headers(), None, {})
    with tracer.start_as_current_span("POST", attributes={"http.url": WEBHOOK}) as span:
        _redact_span_url(span, request)
        assert span.attributes["http.url"].endswith("/1234567890/REDACTED")
        assert "url.full" not in span.attributes
