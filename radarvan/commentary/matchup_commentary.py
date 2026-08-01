"""Pre-game matchup commentary: given two players and a round description,
use ``commentary_prompts.GUIDELINES`` as the system prompt and the two
players' actual profile/head-to-head data as the user message, call
whichever LLM provider is active, and return the generated commentary text.

**Provider switch**: set env var ``COMMENTARY_PROVIDER`` to ``"anthropic"``
or ``"gemini"``; defaults to ``DEFAULT_PROVIDER`` below. We're evaluating
Gemini against Claude for this feature - same prompt/data either way, only
the model call differs (``_generate_with_anthropic`` / `_generate_with_gemini`).

Data fetch deliberately calls the existing route handler functions directly
(``radarvan.routes.profile.get_player_profile``,
``radarvan.routes.players.get_player_head_to_head``) rather than
re-deriving the same games/synergy assembly and calling the lower-level
logic those routes wrap. This inverts the usual "routes depend on logic
modules" direction on purpose: any future improvement to those endpoints -
new fields, better computation, bug fixes - flows into commentary
generation automatically instead of drifting out of sync with a second
implementation. The fetched ``PlayerProfile``/``HeadToHeadDetail`` are then
reduced to ``hype_data.HypePlayerData``/``HypeHeadToHead`` - a purpose-built
shape holding only what the guidelines reference, rendered as plain text
rather than JSON (see ``hype_data``'s module docstring for why).

This module always regenerates - the cache check/write lives at the route
layer (routes/commentary.py), keyed on (player1, player2, round_name) via
repositories.commentary.MatchupCommentaryRepo, so this module and its
callers stay unaware caching exists.
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import NamedTuple

import structlog
from anthropic.types import TextBlock

from ..db_utils import ReplayManager
from ..notify import notify
from ..routes import players as players_routes
from ..routes import profile as profile_routes
from . import anthropic_client, gemini_client, hype_data
from .commentary_prompts import GUIDELINES

logger = structlog.get_logger(__name__)

SYSTEM_PROMPT = GUIDELINES

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


def active_provider() -> str:
    return os.environ.get(PROVIDER_ENV, DEFAULT_PROVIDER).strip().lower()


def commentary_available() -> bool:
    """True if the currently-selected provider has its API key configured."""
    if active_provider() == "anthropic":
        return anthropic_client.commentary_available()
    return gemini_client.commentary_available()


class CommentaryGenerationError(RuntimeError):
    """Raised when the LLM provider call fails or returns no text content."""


class MatchupPrompt(NamedTuple):
    """The exact system + user content that would be sent to the active LLM
    provider for a matchup - split out from generate_commentary so it can be
    inspected (see routes/commentary.py's prompt_preview) without spending a
    real call. Identical regardless of which provider is active.
    """

    system: str
    user_message: str


def build_user_message(
    round_name: str,
    player1: str,
    player2: str,
    player1_data: hype_data.HypePlayerData,
    player2_data: hype_data.HypePlayerData,
    h2h_1v1: hype_data.HypeHeadToHead,
    h2h_all: hype_data.HypeHeadToHead,
) -> str:
    """Assemble the user turn: the ask plus all four data payloads, clearly
    labeled. Kept separate from generate_commentary so it's unit-testable
    without a network call. Payloads are rendered as plain text (see
    hype_data's module docstring), not JSON.
    """
    return (
        f"Generate the pre-game hype commentary for {round_name}: {player1} vs {player2}.\n\n"
        f'<player1_profile player="{player1}">\n'
        f"{hype_data.render_player_data(player1_data)}\n"
        "</player1_profile>\n\n"
        f'<player2_profile player="{player2}">\n'
        f"{hype_data.render_player_data(player2_data)}\n"
        "</player2_profile>\n\n"
        "<head_to_head_1v1>\n"
        f"{hype_data.render_head_to_head(h2h_1v1)}\n"
        "</head_to_head_1v1>\n\n"
        "<head_to_head_all_formats>\n"
        f"{hype_data.render_head_to_head(h2h_all)}\n"
        "</head_to_head_all_formats>"
    )


def build_prompt(
    replay_manager: ReplayManager, player1: str, player2: str, round_name: str
) -> MatchupPrompt:
    """Fetch both players' data and assemble the system + user content that
    would be sent to the active LLM provider for round_name - without
    calling the API. Identical regardless of which provider is active.

    player1/player2 must already be alias-resolved - PlayerName validation
    on MatchupCommentaryRequest handles this before it reaches here.
    """
    profile1 = profile_routes.get_player_profile(
        player=player1, replay_manager=replay_manager
    )
    profile2 = profile_routes.get_player_profile(
        player=player2, replay_manager=replay_manager
    )
    # get_player_head_to_head is async (it loads kill data for value
    # destroyed) but build_prompt is always called from a sync context (a
    # sync FastAPI route runs in starlette's threadpool, with no event loop
    # of its own) - asyncio.run() bridges that safely here.
    h2h_1v1 = asyncio.run(
        players_routes.get_player_head_to_head(
            player1=player1,
            player2=player2,
            game_format="1v1",
            replay_manager=replay_manager,
        )
    )
    h2h_all = asyncio.run(
        players_routes.get_player_head_to_head(
            player1=player1,
            player2=player2,
            game_format=None,
            replay_manager=replay_manager,
        )
    )
    user_message = build_user_message(
        round_name,
        player1,
        player2,
        hype_data.build_hype_player_data(profile1),
        hype_data.build_hype_player_data(profile2),
        hype_data.build_hype_head_to_head(h2h_1v1),
        hype_data.build_hype_head_to_head(h2h_all),
    )
    return MatchupPrompt(system=SYSTEM_PROMPT, user_message=user_message)


def _notify_generated(
    provider: str,
    player1: str,
    player2: str,
    input_tokens: int | None,
    output_tokens: int | None,
    text: str,
) -> None:
    """Fired on every real LLM call (i.e. every cache miss - see
    routes/commentary.py, which only reaches generate_commentary when
    nothing was already saved for this matchup)."""
    notify(
        "\n".join(
            [
                f"🎙️ Matchup commentary generated for {player1} vs {player2} ({provider})",
                f"Tokens: input={input_tokens}, output={output_tokens}",
                text,
            ]
        )
    )


def _generate_with_anthropic(prompt: MatchupPrompt, player1: str, player2: str) -> str:
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
            "commentary generation failed",
            provider="anthropic",
            exc_info=e,
            duration_s=round(time.monotonic() - start, 2),
        )
        raise CommentaryGenerationError(str(e)) from e

    usage = response.usage
    logger.info(
        "commentary generated",
        provider="anthropic",
        player1=player1,
        player2=player2,
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
        "anthropic", player1, player2, usage.input_tokens, usage.output_tokens, text
    )
    return text


def _generate_with_gemini(prompt: MatchupPrompt, player1: str, player2: str) -> str:
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
            "commentary generation failed",
            provider="gemini",
            exc_info=e,
            duration_s=round(time.monotonic() - start, 2),
        )
        raise CommentaryGenerationError(str(e)) from e

    usage = interaction.usage
    input_tokens = usage.total_input_tokens if usage else None
    output_tokens = usage.total_output_tokens if usage else None
    thought_tokens = usage.total_thought_tokens if usage else None
    logger.info(
        "commentary generated",
        provider="gemini",
        player1=player1,
        player2=player2,
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
    _notify_generated("gemini", player1, player2, input_tokens, output_tokens, text)
    return text


def generate_commentary(
    replay_manager: ReplayManager, player1: str, player2: str, round_name: str
) -> str:
    """Fetch both players' data and generate pre-game commentary for
    round_name, using whichever provider COMMENTARY_PROVIDER selects."""
    prompt = build_prompt(replay_manager, player1, player2, round_name)
    if active_provider() == "anthropic":
        return _generate_with_anthropic(prompt, player1, player2)
    return _generate_with_gemini(prompt, player1, player2)
