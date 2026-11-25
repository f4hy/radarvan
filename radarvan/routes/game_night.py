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
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from .. import queries
from ..api_types import (
    GameNightBackfill,
    GameNightBackfillNight,
    GameNightBackfillOutcome,
    GameNightRecap,
    GameNightSummaryStatus,
    MatchBlurbBackfill,
    MatchBlurbBackfillNight,
    MatchBlurbRun,
    NightNetstats,
)
from ..commentary import llm, match_blurb, night_summary
from ..dependencies import (
    OPS_ADMIN,
    cache_short,
    db_manager,
    get_game_night_summary_repo,
    get_match_blurb_repo,
    get_netstats_repo,
)
from ..notify import notify_async
from ..queries import AllGames, NightGames, UnfilteredCompetitiveGames
from ..repositories import GameNightSummaryRepo, MatchBlurbRepo, NetstatsRepo
from ..run_slot import RunSlot

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["game night"])

# Operational routes the admin control panel drives. Cookie-authenticated, so
# included in main.py without the API-key dependency; every route here carries
# `dependencies=OPS_ADMIN`.
session_router = APIRouter(tags=["game night"])


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
    blurbs: MatchBlurbRepo = Depends(get_match_blurb_repo),
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
    recap = night_games.recap
    # Never mutate in place - see the "no mutating inputs" rule in CLAUDE.md.
    update: dict[str, object] = {
        "highlights": queries.with_blurbs(recap.highlights, blurbs)
    }
    stored = summaries.get_night_summary(night)
    if stored is not None:
        update |= {
            "ai_summary": stored.summary,
            "ai_summary_provider": stored.provider,
            "ai_summary_computed_at": stored.computed_at,
        }
    return recap.model_copy(update=update)


@router.get("/api/game_night_netstats/{night}", dependencies=[Depends(cache_short)])
def get_game_night_netstats(
    night: date,
    all_games: AllGames,
    netstats: NetstatsRepo = Depends(get_netstats_repo),
) -> NightNetstats:
    """Who the night spent its freezes and stutter waiting on, over the games with client logs."""
    return queries.night_netstats(night, all_games, netstats)


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


# The four billed routes below answer with a plan and run the calls as a
# background task: a call can outlast Heroku's 30s router timeout, and the
# router 503s the caller while the dyno keeps paying for the work anyway.
# Each claims its feature's `manual_run` before answering and the background
# task releases it, so a second request 409s until the run is done.

_BUSY_SUMMARY = "a game night summary is already being generated"
_BUSY_BLURBS = "match blurbs are already being generated"


def _require_provider() -> None:
    if not llm.commentary_available():
        raise HTTPException(
            status_code=503, detail="LLM generation is not available on this server"
        )


def _reserve(slot: RunSlot, busy: bool, detail: str) -> None:
    if busy or not slot.try_reserve():
        raise HTTPException(status_code=409, detail=detail)


async def _summarize_nights(nights: list[NightGames]) -> None:
    try:
        with db_manager.get_replay_manager() as replay_manager:
            summaries = GameNightSummaryRepo(replay_manager.session)
            for night_games in nights:
                night = night_games.recap.date
                try:
                    await night_summary.generate_and_store(
                        night_games.recap,
                        queries.night_narratives(night_games),
                        summaries,
                    )
                except llm.CommentaryGenerationError as e:
                    # A provider error will hit every remaining night the same way.
                    logger.error(
                        "game night summary generation failed",
                        night=str(night),
                        exc_info=e,
                    )
                    await notify_async(f"Game night recap for {night} failed: {e}")
                    return
    finally:
        night_summary.manual_run.release()


async def _caption_nights(plan: list[tuple[NightGames, int]], force: bool) -> None:
    try:
        with db_manager.get_replay_manager() as replay_manager:
            blurbs = MatchBlurbRepo(replay_manager.session)
            for night_games, calls in plan:
                night = night_games.recap.date
                try:
                    await match_blurb.generate_night_blurbs(
                        night_games, blurbs, force=force, max_calls=calls
                    )
                except llm.CommentaryGenerationError as e:
                    logger.error(
                        "match blurb generation failed", night=str(night), exc_info=e
                    )
                    await notify_async(f"Match blurbs for {night} failed: {e}")
                    return
    finally:
        match_blurb.manual_run.release()


@session_router.post(
    "/api/generate_game_night_summary/{night}",
    dependencies=OPS_ADMIN,
    status_code=202,
)
async def generate_game_night_summary(
    night: date,
    all_games: AllGames,
    competitive: UnfilteredCompetitiveGames,
    background_tasks: BackgroundTasks,
    force: bool = False,
    summaries: GameNightSummaryRepo = Depends(get_game_night_summary_repo),
) -> GameNightSummaryStatus:
    """Queue (or, with ``force``, re-queue) one game night's billed LLM recap.

    Answers 202 with the night's current status; poll
    ``GET /api/game_night_status/{night}`` for the result. Unlike the backfill
    this does not require the night to be closed.
    """
    if night_summary.busy():
        raise HTTPException(status_code=409, detail=_BUSY_SUMMARY)
    if not force and summaries.has_night_summary(night):
        raise HTTPException(
            status_code=409,
            detail=f"{night} already has a summary; pass force=true to overwrite",
        )
    _require_provider()
    night_games = await queries.build_night_recap(
        night, all_games, competitive, db_manager
    )
    if night_games.recap.match_count == 0:
        raise HTTPException(status_code=400, detail=f"no matches on game night {night}")
    _reserve(night_summary.manual_run, night_summary.busy(), _BUSY_SUMMARY)
    background_tasks.add_task(_summarize_nights, [night_games])
    return summary_status(night, summaries)


@session_router.post(
    "/api/generate_match_blurbs/{night}", dependencies=OPS_ADMIN, status_code=202
)
async def generate_match_blurbs(
    night: date,
    all_games: AllGames,
    competitive: UnfilteredCompetitiveGames,
    background_tasks: BackgroundTasks,
    force: bool = False,
    blurbs: MatchBlurbRepo = Depends(get_match_blurb_repo),
) -> MatchBlurbRun:
    """Queue billed captions for one night's top matches (at most ``MAX_BLURBS_PER_NIGHT``).

    Picks that already have a blurb are skipped unless ``force=true``. Does
    not require the night to be closed. Answers 202 with what was queued.
    """
    if match_blurb.busy():
        raise HTTPException(status_code=409, detail=_BUSY_BLURBS)
    _require_provider()
    night_games = await queries.build_night_recap(
        night, all_games, competitive, db_manager
    )
    queued = [
        p.match.id for p in match_blurb.uncaptioned(night_games, blurbs, force=force)
    ]
    picked = [p.match.id for p in match_blurb.pick_candidates(night_games)]
    if queued:
        _reserve(match_blurb.manual_run, match_blurb.busy(), _BUSY_BLURBS)
        background_tasks.add_task(_caption_nights, [(night_games, len(queued))], force)
    return MatchBlurbRun(date=night, picked=picked, queued=queued)


@session_router.post(
    "/api/backfill_match_blurbs", dependencies=OPS_ADMIN, status_code=202
)
async def backfill_match_blurbs(
    all_games: AllGames,
    competitive: UnfilteredCompetitiveGames,
    background_tasks: BackgroundTasks,
    days: int = 7,
    max_to_update: int = 3,
    blurbs: MatchBlurbRepo = Depends(get_match_blurb_repo),
) -> MatchBlurbBackfill:
    """Queue captions for the top matches of the last ``days`` closed nights, newest first.

    **Every blurb queued is a billed LLM call**, and ``max_to_update`` caps
    them across the whole run (each night is capped separately at
    ``MAX_BLURBS_PER_NIGHT``). ``max_to_update=0`` is a dry run: it queues
    nothing and reports what each night would spend. Never overwrites, and
    never touches the night still being played.
    """
    if days < 1:
        raise HTTPException(status_code=400, detail="days must be at least 1")
    if max_to_update < 0:
        raise HTTPException(
            status_code=400, detail="max_to_update must not be negative"
        )
    if match_blurb.busy():
        raise HTTPException(status_code=409, detail=_BUSY_BLURBS)
    if max_to_update > 0:
        _require_provider()
    budget = max_to_update
    nights: list[MatchBlurbBackfillNight] = []
    plan: list[tuple[NightGames, int]] = []
    for night in queries.closed_nights_within(all_games, days):
        night_games = await queries.build_night_recap(
            night, all_games, competitive, db_manager
        )
        report = match_blurb.plan_night(night_games, blurbs, budget)
        budget -= report.queued
        nights.append(report)
        if report.queued:
            plan.append((night_games, report.queued))
    if plan:
        _reserve(match_blurb.manual_run, match_blurb.busy(), _BUSY_BLURBS)
        background_tasks.add_task(_caption_nights, plan, False)
    return MatchBlurbBackfill(
        days=days,
        queued=sum(n.queued for n in nights),
        pending=sum(n.pending for n in nights),
        nights=nights,
    )


@session_router.post(
    "/api/backfill_game_night_summaries", dependencies=OPS_ADMIN, status_code=202
)
async def backfill_game_night_summaries(
    all_games: AllGames,
    competitive: UnfilteredCompetitiveGames,
    background_tasks: BackgroundTasks,
    days: int = 7,
    max_to_update: int = 1,
    summaries: GameNightSummaryRepo = Depends(get_game_night_summary_repo),
) -> GameNightBackfill:
    """Queue missing LLM recaps for the last ``days`` game nights, newest first.

    **Every night queued is a real, billed LLM call.** ``days`` says how far
    back to *look*; ``max_to_update`` says how many calls this run may
    *spend* (default 1, run it again to continue).

    Never overwrites: a night with a stored row is ``already_summarized``,
    because the stored text is the delivery mechanism rather than a cache - use
    ``POST /api/generate_game_night_summary/{night}?force=true`` to rewrite
    one. Nights below ``night_summary.MIN_MATCHES_FOR_SUMMARY`` are skipped,
    and the night in progress is never in the window
    (``queries.closed_nights_within``). The report lists every night
    considered, so it doubles as a preview of the next run.
    """
    if days < 1:
        raise HTTPException(status_code=400, detail="days must be at least 1")
    if max_to_update < 1:
        raise HTTPException(status_code=400, detail="max_to_update must be at least 1")
    if night_summary.busy():
        raise HTTPException(status_code=409, detail=_BUSY_SUMMARY)
    _require_provider()

    nights: list[GameNightBackfillNight] = []
    queued: list[NightGames] = []
    outcome: GameNightBackfillOutcome
    for night in queries.closed_nights_within(all_games, days):
        played = queries.on_night(all_games, night)
        if summaries.has_night_summary(night):
            outcome = "already_summarized"
        elif len(played) < night_summary.MIN_MATCHES_FOR_SUMMARY:
            outcome = "too_few_games"
        elif len(queued) >= max_to_update:
            outcome = "not_attempted"
        else:
            queued.append(
                await queries.build_night_recap(
                    night, all_games, competitive, db_manager
                )
            )
            outcome = "queued"
        nights.append(
            GameNightBackfillNight(date=night, matches=len(played), outcome=outcome)
        )
    if queued:
        _reserve(night_summary.manual_run, night_summary.busy(), _BUSY_SUMMARY)
        logger.info(
            "queued game night summaries", nights=[str(n.recap.date) for n in queued]
        )
        background_tasks.add_task(_summarize_nights, queued)
    remaining = sum(1 for n in nights if n.outcome == "not_attempted")
    return GameNightBackfill(
        days=days, queued=len(queued), remaining=remaining, nights=nights
    )
