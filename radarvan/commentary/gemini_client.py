"""Single Gemini client for LLM-generated content (pre-game matchup
commentary, see ``matchup_commentary.py``). Mirrors ``anthropic_client.py``'s
shape so ``matchup_commentary`` can switch between providers uniformly.

Uses the ``google-genai`` package's Interactions API
(``client.interactions.create``) - the current recommended surface per
https://ai.google.dev/gemini-api/docs as of this writing. This is a newer
API shape (not the older ``client.models.generate_content``); if Google
changes it again, this is the one file that needs updating.
"""

from __future__ import annotations

import os
from functools import cache
from typing import Final

import structlog
from google import genai

logger = structlog.get_logger(__name__)

API_KEY_ENV = "GEMINI_API_KEY"

# Single place to change which model generates commentary. Final so mypy
# infers the precise Literal type interactions.create()'s overloads need to
# resolve to the non-streaming Interaction return type (a plain `str`
# annotation doesn't match the SDK's closed model-ID Literal union, and
# overload resolution falls back to the broader Interaction | Stream[...]).
MODEL: Final = "gemini-3.6-flash"


def commentary_available() -> bool:
    """True if a Gemini API key is configured on this server."""
    return bool(os.environ.get(API_KEY_ENV))


@cache
def gemini_client() -> genai.Client:
    """Process-wide Gemini client; reused for the life of the process."""
    logger.info("Building Gemini client")
    return genai.Client(api_key=os.environ[API_KEY_ENV])
