"""OpenTelemetry tracing setup.

Wiring is a no-op unless ``OTEL_EXPORTER_OTLP_ENDPOINT`` is set - the SDK's
OTLP exporter otherwise defaults to ``http://localhost:4318`` and would just
burn retries against nothing in every environment that hasn't configured a
collector yet. Set the endpoint (and ``OTEL_EXPORTER_OTLP_HEADERS`` for
authenticated backends like Honeycomb/Grafana Cloud) to turn tracing on.
"""

import os
import re
import resource
import time

import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.botocore import BotocoreInstrumentor
from opentelemetry.instrumentation.httpx import (
    HTTPX2ClientInstrumentor,
    HTTPXClientInstrumentor,
    RequestInfo,
)
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)

_OTLP_ENDPOINT_ENV = "OTEL_EXPORTER_OTLP_ENDPOINT"
_PROCESS_STARTED = time.monotonic()

# Discord webhook URLs carry their secret token as the last path segment, which
# the instrumentor's own redact_url (credentials + query string) leaves intact.
_WEBHOOK_TOKEN = re.compile(r"(/webhooks/\d+/)[^/?#]+")
_URL_ATTRIBUTES = ("http.url", "url.full")


def redact_url(url: str) -> str:
    return _WEBHOOK_TOKEN.sub(r"\1REDACTED", url)


def _redact_span_url(span: trace.Span, _request: RequestInfo) -> None:
    if not isinstance(span, ReadableSpan) or span.attributes is None:
        return
    for key in _URL_ATTRIBUTES:
        url = span.attributes.get(key)
        if isinstance(url, str) and (redacted := redact_url(url)) != url:
            span.set_attribute(key, redacted)


async def _redact_span_url_async(span: trace.Span, request: RequestInfo) -> None:
    _redact_span_url(span, request)


def _peak_rss_mb() -> float:
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)


def record_process_start() -> None:
    with tracer.start_as_current_span("process start"):
        pass


def record_process_stop() -> None:
    # Only a graceful shutdown (deploy, daily cycle) reaches this, so a
    # "process start" with no matching stop for its instance is a crash or
    # SIGKILL (e.g. Heroku R15 memory quota).
    with tracer.start_as_current_span(
        "process stop",
        attributes={
            "process.uptime_s": round(time.monotonic() - _PROCESS_STARTED),
            "process.peak_rss_mb": _peak_rss_mb(),
        },
    ):
        pass


def configure_tracing() -> None:
    """Install the global tracer provider and instrument HTTP, Postgres and S3.

    Server spans come from FastAPI's native telemetry, which reads this global
    provider per request.
    """
    endpoint = os.environ.get(_OTLP_ENDPOINT_ENV)
    if not endpoint:
        logger.info("tracing disabled: OTEL_EXPORTER_OTLP_ENDPOINT not set")
        return

    attributes = {"service.name": os.getenv("OTEL_SERVICE_NAME", "radarvan")}
    # DYNO tells web.1 from run.N/scheduler one-offs; the commit needs Heroku's
    # runtime-dyno-metadata lab feature and is simply absent without it.
    for key, env in (
        ("heroku.dyno", "DYNO"),
        ("heroku.release.commit", "HEROKU_SLUG_COMMIT"),
    ):
        if value := os.environ.get(env):
            attributes[key] = value
    provider = TracerProvider(resource=Resource.create(attributes))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)

    # Two independent instrumentors, because two HTTP stacks are in the
    # process: our own code and the anthropic SDK are on httpx2, while
    # google-genai and fastapi[standard] still pull plain httpx.
    hooks = {
        "request_hook": _redact_span_url,
        "async_request_hook": _redact_span_url_async,
    }
    HTTPX2ClientInstrumentor().instrument(**hooks)
    HTTPXClientInstrumentor().instrument(**hooks)
    # Wraps psycopg2.connect, so it must run before the pool opens a connection
    # (main.py calls this at import time).
    Psycopg2Instrumentor().instrument()
    BotocoreInstrumentor().instrument()  # type: ignore[no-untyped-call]
    logger.info("tracing configured", endpoint=endpoint)
