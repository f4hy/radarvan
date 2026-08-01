"""Single Anthropic client for LLM-generated content (pre-game matchup
commentary, see ``matchup_commentary.py``).

Get the process-wide instance via the ``anthropic_client()`` factory - it is
``@cache``d so one client (and its connection pool) is reused for the
lifetime of the process, same pattern as ``cncstats_client()``.
"""

from __future__ import annotations

import os
from functools import cache

import anthropic
import structlog

logger = structlog.get_logger(__name__)

API_KEY_ENV = "CLAUDE_API_KEY"

# Single place to change which model generates commentary.
MODEL = "claude-sonnet-5"


def commentary_available() -> bool:
    """True if a Claude API key is configured on this server."""
    return bool(os.environ.get(API_KEY_ENV))


@cache
def anthropic_client() -> anthropic.Anthropic:
    """Process-wide Anthropic client; reused for the life of the process."""
    logger.info("Building Anthropic client")
    return anthropic.Anthropic(api_key=os.environ[API_KEY_ENV])
