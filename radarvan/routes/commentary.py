"""Pre-game matchup commentary endpoint.

Persisted via ``repositories.commentary.MatchupCommentaryRepo``, keyed on
(player1, player2, round_name): a cache hit returns the stored text with no
LLM call; a miss calls ``matchup_commentary.generate_commentary`` and writes
the result before returning it. ``matchup_commentary`` itself stays unaware
caching exists - it always regenerates when called.
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException

from ..api_types import (
    MatchupCommentaryPromptPreview,
    MatchupCommentaryRequest,
    MatchupCommentaryResponse,
    PlayerName,
)
from ..commentary import matchup_commentary
from ..db_utils import ReplayManager
from ..dependencies import IS_DEV, get_replay_manager

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["commentary"])


@router.post("/api/matchup_commentary/")
def get_matchup_commentary(
    req: MatchupCommentaryRequest,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> MatchupCommentaryResponse:
    """Generate (or return the cached) pre-game hype commentary for a 1v1
    matchup.

    POST (not GET) and gated behind the write-tier API key deliberately -
    a cache miss triggers a real LLM call, not just a read. A cache hit is
    free and instant; see the module docstring for the caching scheme.
    """
    cached = replay_manager.get_cached_commentary(
        req.player1, req.player2, req.round_name
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
            replay_manager, req.player1, req.player2, req.round_name
        )
    except matchup_commentary.CommentaryGenerationError as e:
        logger.error("matchup commentary generation failed", exc_info=e)
        raise HTTPException(
            status_code=502, detail="commentary generation failed"
        ) from e
    replay_manager.save_commentary(
        req.player1,
        req.player2,
        req.round_name,
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
