"""OpenTelemetry tracing setup.

Wiring is a no-op unless ``OTEL_EXPORTER_OTLP_ENDPOINT`` is set - the SDK's
OTLP exporter otherwise defaults to ``http://localhost:4318`` and would just
burn retries against nothing in every environment that hasn't configured a
collector yet. Set the endpoint (and ``OTEL_EXPORTER_OTLP_HEADERS`` for
authenticated backends like Honeycomb/Grafana Cloud) to turn tracing on.
"""

from collections.abc import Coroutine
import os
from typing import Any

import fsspec.asyn
import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.httpx import (
    HTTPX2ClientInstrumentor,
    HTTPXClientInstrumentor,
)
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = structlog.get_logger(__name__)

_OTLP_ENDPOINT_ENV = "OTEL_EXPORTER_OTLP_ENDPOINT"


def configure_tracing() -> None:
    """Install the global tracer provider and instrument HTTP, Postgres and fsspec/S3.

    Server spans come from FastAPI's native telemetry, which reads this global
    provider per request.
    """
    endpoint = os.environ.get(_OTLP_ENDPOINT_ENV)
    if not endpoint:
        logger.info("tracing disabled: OTEL_EXPORTER_OTLP_ENDPOINT not set")
        return

    resource = Resource.create(
        {"service.name": os.getenv("OTEL_SERVICE_NAME", "radarvan")}
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)

    # Two independent instrumentors, because two HTTP stacks are in the
    # process: our own code and the anthropic SDK are on httpx2, while
    # google-genai and fastapi[standard] still pull plain httpx.
    HTTPX2ClientInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()
    # Wraps psycopg2.connect, so it must run before the pool opens a connection
    # (main.py calls this at import time).
    Psycopg2Instrumentor().instrument()
    _instrument_fsspec()
    logger.info("tracing configured", endpoint=endpoint)


def _instrument_fsspec() -> None:
    # fsspec (s3fs, and the http fs for replay downloads) runs each blocking
    # call as a coroutine on its own IO-loop thread, which starts from an empty
    # context, so spans opened there would be orphaned. `_runner(...)` is
    # evaluated on the caller's thread: open the span there and carry it over.
    tracer = trace.get_tracer(__name__)
    original = fsspec.asyn._runner

    def runner(event: Any, coro: Any, result: Any, timeout: Any = None) -> Any:
        span = tracer.start_span(
            f"fsspec {getattr(coro, '__qualname__', 'call')}",
            attributes=_fsspec_attributes(coro),
        )
        return original(event, _run_in_span(span, coro), result, timeout)

    fsspec.asyn._runner = runner


async def _run_in_span(span: trace.Span, coro: Coroutine[Any, Any, Any]) -> Any:
    with trace.use_span(span, end_on_exit=True):
        return await coro


def _fsspec_attributes(coro: Any) -> dict[str, str]:
    # An unstarted coroutine's frame locals are its arguments.
    frame = getattr(coro, "cr_frame", None)
    if frame is None:
        return {}
    return {
        f"fsspec.{name}": value
        for name in ("path", "bucket", "key")
        if isinstance(value := frame.f_locals.get(name), str)
    }
