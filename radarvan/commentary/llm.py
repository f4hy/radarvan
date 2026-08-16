"""Provider dispatch shared by every LLM-generated blurb in this package.

Two features generate text through the same two providers with the same
budget and the same failure modes - the pre-game hype
(``matchup_commentary``) and the post-game recap (``postgame_summary``) -
so the provider selection, the streaming Anthropic call, the Gemini
interaction call, the empty-output guard, the usage logging and the Discord
notification all live here once. A caller supplies a ``Prompt`` plus a
``kind``/``label`` pair used purely for logging and the notification line.

**Provider switch**: set env var ``COMMENTARY_PROVIDER`` to ``"anthropic"``
or ``"gemini"``; defaults to ``DEFAULT_PROVIDER`` below. We're evaluating
Gemini against Claude for this feature - same prompt/data either way, only
the model call differs.
"""

from __future__ import annotations

import os
import time
from typing import NamedTuple

import structlog
from anthropic.types import TextBlock

from ..notify import notify
from . import anthropic_client, gemini_client

logger = structlog.get_logger(__name__)

PROVIDER_ENV = "COMMENTARY_PROVIDER"
# Evaluating Gemini vs Claude for commentary quality/cost - Gemini default
# for now. Override per-process with COMMENTARY_PROVIDER=anthropic.
DEFAULT_PROVIDER = "gemini"

# Total output budget (thinking + final text), shared by both providers.
# Generous on purpose: a high-history matchup can push the input well past
# 100K tokens, and thinking at high effort sizes its reasoning to the data
# it's given - a too-small budget gets consumed entirely by thinking,
# leaving zero text (see the two _generate_with_* error messages). The
# Anthropic call is streamed because a non-streaming request this large
# risks the SDK's ~10-minute timeout guard.
MAX_TOKENS = 16000


class Prompt(NamedTuple):
    """The exact system + user content that would be sent to the active LLM
    provider - split out from the generate calls so it can be inspected (see
    the prompt_preview routes) without spending a real call. Identical
    regardless of which provider is active.
    """

    system: str
    user_message: str


class CommentaryGenerationError(RuntimeError):
    """Raised when the LLM provider call fails or returns no text content."""


def active_provider() -> str:
    return os.environ.get(PROVIDER_ENV, DEFAULT_PROVIDER).strip().lower()


def commentary_available() -> bool:
    """True if the currently-selected provider has its API key configured."""
    if active_provider() == "anthropic":
        return anthropic_client.commentary_available()
    return gemini_client.commentary_available()


def _notify_generated(
    kind: str,
    provider: str,
    label: str,
    input_tokens: int | None,
    output_tokens: int | None,
    text: str,
) -> None:
    """Fired on every real LLM call (i.e. every cache miss - the routes only
    reach generation when nothing was already saved)."""
    notify(
        "\n".join(
            [
                f"🎙️ {kind} generated for {label} ({provider})",
                f"Tokens: input={input_tokens}, output={output_tokens}",
                text,
            ]
        )
    )


def _generate_with_anthropic(prompt: Prompt, kind: str, label: str) -> str:
    start = time.monotonic()
    try:
        with anthropic_client.anthropic_client().messages.stream(
            model=anthropic_client.MODEL,
            max_tokens=MAX_TOKENS,
            thinking={"type": "adaptive"},
            output_config={"effort": "high"},
            system=prompt.system,
            messages=[{"role": "user", "content": prompt.user_message}],
        ) as stream:
            response = stream.get_final_message()
    except Exception as e:
        logger.error(
            "llm generation failed",
            provider="anthropic",
            kind=kind,
            exc_info=e,
            duration_s=round(time.monotonic() - start, 2),
        )
        raise CommentaryGenerationError(str(e)) from e

    usage = response.usage
    logger.info(
        "llm text generated",
        provider="anthropic",
        kind=kind,
        label=label,
        duration_s=round(time.monotonic() - start, 2),
        stop_reason=response.stop_reason,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cache_creation_input_tokens=usage.cache_creation_input_tokens,
        cache_read_input_tokens=usage.cache_read_input_tokens,
    )

    text = "".join(
        block.text for block in response.content if isinstance(block, TextBlock)
    )
    if not text:
        # Most likely cause: max_tokens was consumed entirely by thinking
        # before any text block was written - stop_reason/output_tokens
        # pinpoint that without needing the full response dump.
        raise CommentaryGenerationError(
            f"model returned no text content (stop_reason={response.stop_reason!r}, "
            f"output_tokens={usage.output_tokens})"
        )
    _notify_generated(
        kind, "anthropic", label, usage.input_tokens, usage.output_tokens, text
    )
    return text


def _generate_with_gemini(prompt: Prompt, kind: str, label: str) -> str:
    start = time.monotonic()
    try:
        interaction = gemini_client.gemini_client().interactions.create(
            model=gemini_client.MODEL,
            system_instruction=prompt.system,
            input=prompt.user_message,
            generation_config={
                "thinking_level": "high",
                "max_output_tokens": MAX_TOKENS,
            },
        )
    except Exception as e:
        logger.error(
            "llm generation failed",
            provider="gemini",
            kind=kind,
            exc_info=e,
            duration_s=round(time.monotonic() - start, 2),
        )
        raise CommentaryGenerationError(str(e)) from e

    usage = interaction.usage
    input_tokens = usage.total_input_tokens if usage else None
    output_tokens = usage.total_output_tokens if usage else None
    thought_tokens = usage.total_thought_tokens if usage else None
    logger.info(
        "llm text generated",
        provider="gemini",
        kind=kind,
        label=label,
        duration_s=round(time.monotonic() - start, 2),
        status=interaction.status,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        thought_tokens=thought_tokens,
    )

    text = interaction.output_text
    if not text:
        raise CommentaryGenerationError(
            f"model returned no text content (status={interaction.status!r}, "
            f"output_tokens={output_tokens})"
        )
    _notify_generated(kind, "gemini", label, input_tokens, output_tokens, text)
    return text


def generate(prompt: Prompt, *, kind: str, label: str) -> str:
    """Run ``prompt`` through whichever provider COMMENTARY_PROVIDER selects.

    ``kind`` ("matchup commentary", "post-game summary") and ``label`` (the
    matchup it's about) only ever reach the logs and the Discord notification
    - the model sees nothing but ``prompt``.
    """
    if active_provider() == "anthropic":
        return _generate_with_anthropic(prompt, kind, label)
    return _generate_with_gemini(prompt, kind, label)
