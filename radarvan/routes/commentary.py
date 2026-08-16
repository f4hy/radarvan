"""The two LLM-generated blurbs about a bracket set: the pre-game hype and,
once it's been played, the post-game recap.

Both are persisted (``repositories.commentary``): a cache hit returns the
stored text with no LLM call; a miss generates and writes the result before
returning it. The generator modules themselves stay unaware caching exists -
they always regenerate when called. Keys differ because the two are about
different things: hype is keyed on (player1, player2, round_name), which is
all a matchup is before it's played, while the recap is keyed on the durable
tournament plus bracket stage, which is what identifies the games it
describes.

``bypass_cache``/``force_refresh`` skip the cache read and force a fresh LLM
call; ``force_refresh`` then overwrites the cached row, ``bypass_cache``
leaves it untouched. Both are admin-tier-only - see the route docstrings.
"""

from typing import NamedTuple

import structlog
from fastapi import APIRouter, Depends, HTTPException

from .. import bracket
from ..api_types import (
    BracketMatchOutput,
    BracketSummaryResponse,
    MatchInfo,
    MatchupCommentaryPromptPreview,
    MatchupCommentaryResponse,
    PlayerName,
)
from ..commentary import matchup_commentary, postgame_summary
from ..db_utils import ReplayManager
from ..dependencies import (
    IS_DEV,
    get_bracket_repo,
    get_bracket_summary_repo,
    get_replay_manager,
    get_tournament_repo,
    has_admin_access,
)
from ..repositories import BracketRepo, BracketSummaryRepo, TournamentRepo
from . import bracket as bracket_routes

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["commentary"])


@router.get("/api/matchup_commentary/")
def get_matchup_commentary(
    player1: PlayerName,
    player2: PlayerName,
    round_name: str,
    bypass_cache: bool = False,
    force_refresh: bool = False,
    admin_access: bool = Depends(has_admin_access),
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> MatchupCommentaryResponse:
    """Generate (or return the cached) pre-game hype commentary for a 1v1
    matchup.

    A GET so the normal-tier API key the browser ships with can reach it - the
    bracket UI needs to show this to everyone, and a cache hit is free and
    instant. A cache *miss* still triggers a real, billed LLM call, so the
    two things that would make that spend unbounded are fenced off:

    - ``round_name`` must be one a bracket actually produces
      (``bracket.known_round_names()``); the cache key is
      (player1, player2, round_name) and all three must be enumerable, or a
      caller could mint fresh keys forever. Player names are already bounded
      by ``PlayerName``'s alias resolution.
    - ``bypass_cache``/``force_refresh`` both skip the cache read and always
      call the LLM, so they require the admin-tier key. They differ in
      whether the result is then persisted: ``force_refresh`` overwrites the
      cached row, ``bypass_cache`` does not touch it. If both are set,
      ``bypass_cache`` wins (no write).
    """
    skip_cache_read = bypass_cache or force_refresh
    if skip_cache_read and not admin_access:
        raise HTTPException(
            status_code=403,
            detail="bypass_cache/force_refresh require an admin-tier API key",
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


class RecappableSet(NamedTuple):
    """A completed bracket set whose games are all on record, plus the key
    its recap is cached under."""

    match: BracketMatchOutput
    tournament_id: int
    games: list[MatchInfo]


def _recappable_set(
    match_id: str,
    repo: BracketRepo,
    tournament_repo: TournamentRepo,
    replay_manager: ReplayManager,
) -> RecappableSet | None:
    """The set behind ``match_id`` if it can be recapped, else None.

    Recappable means: the bracket is revealed, the set is completed with both
    players known, its games are linked to a durable tournament, and there
    are at least as many linked games as the score says were played. That
    last check is the point of the whole gate - a recap written off three of
    a five-game set would describe a sweep that never happened.

    Both reads go through the bracket route handlers rather than the repos
    directly, for the reason ``matchup_commentary._tournament_inputs``
    documents: ``get_bracket`` owns the pre-reveal redaction, and
    ``get_bracket_games`` owns which games count. ``user=None`` (never an
    admin preview) is deliberate - one cached recap is served to everyone, so
    it must only ever be built from what everyone can already see.
    """
    tournament_row, _raw_states, _result, _resolved = bracket_routes.load_match(
        repo, match_id
    )
    parent = bracket_routes.tournament_for_bracket(tournament_row, tournament_repo)
    if parent is None:
        return None
    output = bracket_routes.get_bracket(preview=False, user=None, repo=repo)
    if output is None:
        return None
    match = next((m for m in output.matches if m.match_id == match_id), None)
    if match is None or match.status != "completed":
        return None
    if match.winner is None or match.player_a is None or match.player_b is None:
        return None
    if match.score_a is None or match.score_b is None:
        return None

    games = bracket_routes.get_bracket_games(
        match_id,
        user=None,
        repo=repo,
        tournament_repo=tournament_repo,
        replay_manager=replay_manager,
    ).linked
    if len(games) < match.score_a + match.score_b:
        return None
    return RecappableSet(match=match, tournament_id=parent.id, games=games)


@router.get("/api/bracket_summary/{match_id}")
def get_bracket_summary(
    match_id: str,
    bypass_cache: bool = False,
    force_refresh: bool = False,
    admin_access: bool = Depends(has_admin_access),
    repo: BracketRepo = Depends(get_bracket_repo),
    tournament_repo: TournamentRepo = Depends(get_tournament_repo),
    summary_repo: BracketSummaryRepo = Depends(get_bracket_summary_repo),
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> BracketSummaryResponse:
    """Generate (or return the cached) post-game recap of one bracket set.

    A GET, for the same reason the pre-game commentary route is one: the
    bracket UI shows this to everyone and a cache hit is free. A cache *miss*
    still triggers a real, billed LLM call, so the same two fences apply:

    - The key is (tournament, bracket stage), both of which the server
      resolves itself from ``match_id`` - a caller can't mint fresh keys, and
      ``_recappable_set`` refuses everything that isn't a finished set with
      all of its games on record. ``ready=false`` is the "nothing to say yet"
      answer, and costs nothing.
    - ``bypass_cache``/``force_refresh`` always call the LLM, so they need
      the admin-tier key. They differ in whether the result is then
      persisted: ``force_refresh`` overwrites the cached row, ``bypass_cache``
      does not touch it. If both are set, ``bypass_cache`` wins (no write).
      ``force_refresh`` is the answer to a recap whose games an admin
      relinked afterwards.
    """
    skip_cache_read = bypass_cache or force_refresh
    if skip_cache_read and not admin_access:
        raise HTTPException(
            status_code=403,
            detail="bypass_cache/force_refresh require an admin-tier API key",
        )
    recappable = _recappable_set(match_id, repo, tournament_repo, replay_manager)
    if recappable is None:
        return BracketSummaryResponse(match_id=match_id, ready=False)

    cached = (
        None
        if skip_cache_read
        else summary_repo.get_cached_summary(recappable.tournament_id, match_id)
    )
    if cached is not None:
        return BracketSummaryResponse(match_id=match_id, ready=True, summary=cached)

    if not matchup_commentary.commentary_available():
        raise HTTPException(
            status_code=503,
            detail="commentary generation is not available on this server",
        )
    try:
        text = postgame_summary.generate_summary(
            replay_manager, recappable.match, recappable.games
        )
    except matchup_commentary.CommentaryGenerationError as e:
        logger.error("bracket summary generation failed", exc_info=e, stage=match_id)
        raise HTTPException(status_code=502, detail="summary generation failed") from e
    if not bypass_cache:
        summary_repo.save_summary(
            recappable.tournament_id,
            match_id,
            text,
            matchup_commentary.active_provider(),
        )
    return BracketSummaryResponse(match_id=match_id, ready=True, summary=text)


@router.get("/api/bracket_summary_preview/{match_id}", include_in_schema=IS_DEV)
def get_bracket_summary_prompt_preview(
    match_id: str,
    repo: BracketRepo = Depends(get_bracket_repo),
    tournament_repo: TournamentRepo = Depends(get_tournament_repo),
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> MatchupCommentaryPromptPreview:
    """Dev-only: assemble the exact system + user content that would be sent
    to the active LLM provider for this set's recap, without calling the API.

    A distinct top-level path rather than a sibling of
    ``/api/bracket_summary/{match_id}`` - the OpenAPI generator merges a
    static route with a parameterized sibling sharing its prefix (see
    CLAUDE.md).
    """
    recappable = _recappable_set(match_id, repo, tournament_repo, replay_manager)
    if recappable is None:
        raise HTTPException(
            status_code=404, detail=f"{match_id} has no complete set to recap"
        )
    prompt = postgame_summary.build_prompt(
        replay_manager, recappable.match, recappable.games
    )
    return MatchupCommentaryPromptPreview(
        system=prompt.system,
        user_message=prompt.user_message,
        system_chars=len(prompt.system),
        user_message_chars=len(prompt.user_message),
    )
