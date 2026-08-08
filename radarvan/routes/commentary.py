"""Pre-game matchup commentary endpoint.

Persisted via ``repositories.commentary.MatchupCommentaryRepo``, keyed on
(player1, player2, round_name): a cache hit returns the stored text with no
LLM call; a miss calls ``matchup_commentary.generate_commentary`` and writes
the result before returning it. ``matchup_commentary`` itself stays unaware
caching exists - it always regenerates when called.

``bypass_cache``/``force_refresh`` skip the cache read and force a fresh LLM
call; ``force_refresh`` then overwrites the cached row, ``bypass_cache``
leaves it untouched. Both are write-tier-only - see the route docstring.
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException

from .. import bracket
from ..api_types import (
    MatchupCommentaryPromptPreview,
    MatchupCommentaryResponse,
    PlayerName,
)
from ..commentary import matchup_commentary
from ..db_utils import ReplayManager
from ..dependencies import IS_DEV, get_replay_manager, has_write_access

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["commentary"])


@router.get("/api/matchup_commentary/")
def get_matchup_commentary(
    player1: PlayerName,
    player2: PlayerName,
    round_name: str,
    bypass_cache: bool = False,
    force_refresh: bool = False,
    write_access: bool = Depends(has_write_access),
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> MatchupCommentaryResponse:
    """Generate (or return the cached) pre-game hype commentary for a 1v1
    matchup.

    A GET so the read-tier API key the browser ships with can reach it - the
    bracket UI needs to show this to everyone, and a cache hit is free and
    instant. A cache *miss* still triggers a real, billed LLM call, so the
    two things that would make that spend unbounded are fenced off:

    - ``round_name`` must be one a bracket actually produces
      (``bracket.known_round_names()``); the cache key is
      (player1, player2, round_name) and all three must be enumerable, or a
      caller could mint fresh keys forever. Player names are already bounded
      by ``PlayerName``'s alias resolution.
    - ``bypass_cache``/``force_refresh`` both skip the cache read and always
      call the LLM, so they require the write-tier key. They differ in
      whether the result is then persisted: ``force_refresh`` overwrites the
      cached row, ``bypass_cache`` does not touch it. If both are set,
      ``bypass_cache`` wins (no write).
    """
    skip_cache_read = bypass_cache or force_refresh
    if skip_cache_read and not write_access:
        raise HTTPException(
            status_code=403,
            detail="bypass_cache/force_refresh require a write-tier API key",
        )
    if round_name not in bracket.known_round_names():
        raise HTTPException(status_code=400, detail=f"unknown round: {round_name}")
    cached = (
        None
        if skip_cache_read
        else replay_manager.get_cached_commentary(player1, player2, round_name)
    )
    if cached is not None:
        return MatchupCommentaryResponse(commentary=cached)

    if not matchup_commentary.commentary_available():
        raise HTTPException(
            status_code=503,
            detail="commentary generation is not available on this server",
        )
    try:
        text = matchup_commentary.generate_commentary(
            replay_manager, player1, player2, round_name
        )
    except matchup_commentary.CommentaryGenerationError as e:
        logger.error("matchup commentary generation failed", exc_info=e)
        raise HTTPException(
            status_code=502, detail="commentary generation failed"
        ) from e
    if not bypass_cache:
        replay_manager.save_commentary(
            player1,
            player2,
            round_name,
            text,
            matchup_commentary.active_provider(),
        )
    return MatchupCommentaryResponse(commentary=text)


@router.get("/api/matchup_commentary/prompt_preview", include_in_schema=IS_DEV)
def get_matchup_commentary_prompt_preview(
    player1: PlayerName,
    player2: PlayerName,
    round_name: str,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> MatchupCommentaryPromptPreview:
    """Dev-only: assemble the exact system + user content that would be sent
    to the active LLM provider for this matchup, without calling the API -
    for inspecting and trimming payload size/cost. E.g.:

        curl -s "http://localhost:8000/api/matchup_commentary/prompt_preview?player1=X&player2=Y&round_name=Test" \\
          | jq -r .userMessage > /tmp/prompt.json
    """
    prompt = matchup_commentary.build_prompt(
        replay_manager, player1, player2, round_name
    )
    return MatchupCommentaryPromptPreview(
        system=prompt.system,
        user_message=prompt.user_message,
        system_chars=len(prompt.system),
        user_message_chars=len(prompt.user_message),
    )
