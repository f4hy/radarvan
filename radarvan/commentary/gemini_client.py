"""Gemini client for LLM content; mirrors ``anthropic_client.py``. Uses the Interactions API."""

from __future__ import annotations

import os
from collections.abc import Mapping
from functools import cache
from typing import Final, Protocol

import structlog
from google import genai
from google.genai import types

logger = structlog.get_logger(__name__)

API_KEY_ENV = "GEMINI_API_KEY"

# Ride out "high demand" 503s and 429s for hours rather than fail: every caller
# is a background thread or a scheduled job, and a late blurb beats none. The
# Interactions API counts retries, not elapsed time - 5s doubling to a 15-min
# cap over 32 retries is ~6h (less with its up-to-25% jitter). A server
# Retry-After overrides the computed wait.
RETRY_OPTIONS: Final = types.HttpRetryOptions(
    attempts=32,
    initial_delay=5.0,
    max_delay=15 * 60.0,
    exp_base=2.0,
    http_status_codes=[408, 429, 500, 502, 503, 504],
)

# Single place to change which model generates commentary. Final so mypy
# infers the precise Literal type interactions.create()'s overloads need to
# resolve to the non-streaming Interaction return type (a plain `str`
# annotation doesn't match the SDK's closed model-ID Literal union, and
# overload resolution falls back to the broader Interaction | Stream[...]).
MODEL: Final = "gemini-4-hydrogen"


def commentary_available() -> bool:
    """True if a Gemini API key is configured on this server."""
    return bool(os.environ.get(API_KEY_ENV))


class _Response(Protocol):
    @property
    def status_code(self) -> int: ...
    @property
    def headers(self) -> Mapping[str, str]: ...


def _log_attempt(response: _Response) -> None:
    # The SDK's Interactions retry loop is silent; this hook sees every attempt.
    if response.status_code < 400:
        logger.info("gemini http response", status=response.status_code)
    else:
        logger.warning(
            "gemini http error, may retry",
            status=response.status_code,
            retry_after=response.headers.get("retry-after"),
        )


@cache
def gemini_client() -> genai.Client:
    """Process-wide Gemini client; reused for the life of the process."""
    logger.info("Building Gemini client", model=MODEL)
    return genai.Client(
        api_key=os.environ[API_KEY_ENV],
        http_options=types.HttpOptions(
            retry_options=RETRY_OPTIONS,
            client_args={"event_hooks": {"response": [_log_attempt]}},
        ),
    )
