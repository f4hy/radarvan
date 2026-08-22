"""The game-night recap: one evening of games as a page.

Two halves with very different costs, which is why the read path is shaped the
way it is. The deterministic recap (``queries.build_night_recap``) is
recomputed per request and available for every night in the corpus. The
LLM-written paragraph is *only* ever attached from storage - a night without a
stored row returns ``ai_summary: null`` and the page omits that section.

**No read path here generates.** Generation happens once a night in the
scheduler (``schedule.compute_game_night_summary``), and by hand through the
two ops endpoints below (one night by hand, or a bounded backfill of the
last N). A date is an unbounded key, so a route that filled the
cache on a miss would bill an LLM call for every night anybody scrolled back
to - the opposite of the bracket blurbs, whose keys are enumerable and so can
safely generate on demand (see routes/commentary.py).
"""

from datetime import date

import structlog
from fastapi import APIRouter, Depends, HTTPException

from .. import queries
from ..api_types import (
    GameNightBackfill,
    GameNightBackfillNight,
    GameNightBackfillOutcome,
    GameNightRecap,
    GameNightSummaryStatus,
)
from ..commentary import llm, night_summary
from ..dependencies import (
    OPS_ADMIN,
    cache_short,
    db_manager,
    get_game_night_summary_repo,
)
from ..queries import AllGames, UnfilteredCompetitiveGames
from ..repositories import GameNightSummaryRepo

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["game night"])

# Operational routes the admin control panel drives. Cookie-authenticated, so
# included in main.py without the API-key dependency; every route here carries
# `dependencies=OPS_ADMIN`.
session_router = APIRouter()


def summary_status(
    night: date, summaries: GameNightSummaryRepo
) -> GameNightSummaryStatus:
    stored = summaries.get_night_summary(night)
    return GameNightSummaryStatus(
        date=night,
        has_summary=stored is not None,
        provider=stored.provider if stored else None,
        computed_at=stored.computed_at if stored else None,
    )


@router.get("/api/game_night/{night}", dependencies=[Depends(cache_short)])
async def get_game_night_recap(
    night: date,
    all_games: AllGames,
    competitive: UnfilteredCompetitiveGames,
    summaries: GameNightSummaryRepo = Depends(get_game_night_summary_repo),
) -> GameNightRecap:
    """The recap for one game night.

    ``night`` is the game-night date key (``utils.game_night_date``), the same
    one ``/api/dates/`` returns - not a calendar UTC date. A night with no
    games returns a zeroed recap rather than a 404, so the page can render
    "nothing was played" for a date somebody typed in.
    """
    night_games = await queries.build_night_recap(
        night, all_games, competitive, db_manager
    )
    stored = summaries.get_night_summary(night)
    if stored is None:
        return night_games.recap
    # Never mutate in place - see the "no mutating inputs" rule in CLAUDE.md.
    return night_games.recap.model_copy(
        update={
            "ai_summary": stored.summary,
            "ai_summary_provider": stored.provider,
            "ai_summary_computed_at": stored.computed_at,
        }
    )


@router.get("/api/game_night_summaries", dependencies=[Depends(cache_short)])
def list_game_night_summaries(
    limit: int = 60,
    summaries: GameNightSummaryRepo = Depends(get_game_night_summary_repo),
) -> list[date]:
    """Game nights that have a stored LLM recap, newest first.

    Lets a listing badge the nights that have one without fetching each night's
    recap. A distinct top-level path rather than a static sibling of
    ``/api/game_night/{night}`` - the OpenAPI generator silently merges those
    (see the maps note in CLAUDE.md).
    """
    return summaries.list_summarized_nights(limit)


@router.get("/api/game_night_status/{night}", dependencies=[Depends(cache_short)])
def get_game_night_summary_status(
    night: date,
    summaries: GameNightSummaryRepo = Depends(get_game_night_summary_repo),
) -> GameNightSummaryStatus:
    """Whether a night has a stored LLM recap, without shipping its text."""
    return summary_status(night, summaries)


@session_router.post("/api/generate_game_night_summary/{night}", dependencies=OPS_ADMIN)
async def generate_game_night_summary(
    night: date,
    all_games: AllGames,
    competitive: UnfilteredCompetitiveGames,
    force: bool = False,
    summaries: GameNightSummaryRepo = Depends(get_game_night_summary_repo),
) -> GameNightSummaryStatus:
    """Write (or rewrite) one game night's LLM recap by hand.

    A real, billed LLM call - which is why this is the only way to reach the
    generator outside the nightly job, why it is ops-admin gated, and why it
    refuses by default when a row already exists. ``force=true`` overwrites.

    Unlike the nightly job this does not require the night to be closed, so it
    can be used to see what tonight would read like; the row it writes is then
    the one the page serves, so re-run it with ``force`` once the night ends.
    """
    if night_summary.generation_lock.locked():
        raise HTTPException(
            status_code=409, detail="a game night summary is already being generated"
        )
    if not force and summaries.has_night_summary(night):
        raise HTTPException(
            status_code=409,
            detail=f"{night} already has a summary; pass force=true to overwrite",
        )
    if not llm.commentary_available():
        raise HTTPException(
            status_code=503,
            detail="LLM generation is not available on this server",
        )
    night_games = await queries.build_night_recap(
        night, all_games, competitive, db_manager
    )
    if night_games.recap.match_count == 0:
        raise HTTPException(status_code=400, detail=f"no matches on game night {night}")
    try:
        await night_summary.generate_and_store(
            night_games.recap, queries.night_narratives(night_games), summaries
        )
    except llm.CommentaryGenerationError as e:
        logger.error("game night summary generation failed", exc_info=e)
        raise HTTPException(status_code=502, detail="summary generation failed") from e
    return summary_status(night, summaries)


@session_router.post("/api/backfill_game_night_summaries", dependencies=OPS_ADMIN)
async def backfill_game_night_summaries(
    all_games: AllGames,
    competitive: UnfilteredCompetitiveGames,
    days: int = 7,
    max_to_update: int = 1,
    summaries: GameNightSummaryRepo = Depends(get_game_night_summary_repo),
) -> GameNightBackfill:
    """Fill in missing LLM recaps for the last ``days`` game nights.

    **Every night this writes is a real, billed LLM call**, which is what
    shapes the two knobs. ``days`` says how far back to *look*;
    ``max_to_update`` says how many calls this run may *spend* (the backfill
    endpoint pattern - default 1, run it again to continue). Nights are taken
    newest first, so a small budget buys the recaps people are most likely to
    read.

    Never overwrites: a night with a stored row is reported
    ``already_summarized`` and skipped, because the stored text is the
    delivery mechanism rather than a cache. Use
    ``POST /api/generate_game_night_summary/{night}?force=true`` to rewrite
    one deliberately. Nights below the floor the nightly job uses
    (``night_summary.MIN_MATCHES_FOR_SUMMARY``) are skipped too, and the night
    currently in progress is never in the window - see
    ``queries.closed_nights_within``.

    The report lists every night considered, so a run with the default budget
    doubles as a dry run of the next one.
    """
    if days < 1:
        raise HTTPException(status_code=400, detail="days must be at least 1")
    if max_to_update < 1:
        raise HTTPException(status_code=400, detail="max_to_update must be at least 1")
    if night_summary.generation_lock.locked():
        raise HTTPException(
            status_code=409, detail="a game night summary is already being generated"
        )
    if not llm.commentary_available():
        raise HTTPException(
            status_code=503,
            detail="LLM generation is not available on this server",
        )

    nights: list[GameNightBackfillNight] = []
    generated = 0
    # A provider error is not per-night bad luck - it will hit every remaining
    # night the same way, so the first one stops the run rather than burning
    # the budget on repeats. Already-written rows are kept and reported.
    stopped = False
    outcome: GameNightBackfillOutcome
    for night in queries.closed_nights_within(all_games, days):
        played = queries.on_night(all_games, night)
        if summaries.has_night_summary(night):
            outcome = "already_summarized"
        elif len(played) < night_summary.MIN_MATCHES_FOR_SUMMARY:
            outcome = "too_few_games"
        elif stopped or generated >= max_to_update:
            outcome = "not_attempted"
        else:
            logger.info(
                "backfilling game night summary", night=str(night), games=len(played)
            )
            night_games = await queries.build_night_recap(
                night, all_games, competitive, db_manager
            )
            try:
                await night_summary.generate_and_store(
                    night_games.recap, queries.night_narratives(night_games), summaries
                )
            except llm.CommentaryGenerationError as e:
                logger.error(
                    "game night summary generation failed",
                    night=str(night),
                    exc_info=e,
                )
                outcome = "failed"
                stopped = True
            else:
                generated += 1
                outcome = "generated"
        nights.append(
            GameNightBackfillNight(date=night, matches=len(played), outcome=outcome)
        )
    remaining = sum(1 for n in nights if n.outcome in {"not_attempted", "failed"})
    return GameNightBackfill(
        days=days, generated=generated, remaining=remaining, nights=nights
    )
