"""OpenTelemetry tracing setup.

Wiring is a no-op unless ``OTEL_EXPORTER_OTLP_ENDPOINT`` is set - the SDK's
OTLP exporter otherwise defaults to ``http://localhost:4318`` and would just
burn retries against nothing in every environment that hasn't configured a
collector yet. Set the endpoint (and ``OTEL_EXPORTER_OTLP_HEADERS`` for
authenticated backends like Honeycomb/Grafana Cloud) to turn tracing on.
"""

import os

import structlog
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import (
    HTTPX2ClientInstrumentor,
    HTTPXClientInstrumentor,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = structlog.get_logger(__name__)

_OTLP_ENDPOINT_ENV = "OTEL_EXPORTER_OTLP_ENDPOINT"


def configure_tracing(app: FastAPI) -> None:
    """Set up OTLP HTTP tracing and instrument FastAPI + both HTTP clients.

    Call once, right after the ``FastAPI`` app is constructed.
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

    FastAPIInstrumentor.instrument_app(app)
    # Two independent instrumentors, because two HTTP stacks are in the
    # process: our own code and the anthropic SDK are on httpx2, while
    # google-genai and fastapi[standard] still pull plain httpx.
    HTTPX2ClientInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()
    logger.info("tracing configured", endpoint=endpoint)
