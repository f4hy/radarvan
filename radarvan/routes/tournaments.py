"""Tournament endpoints."""

import asyncio
import structlog

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response

from .. import match_details, tournament
from ..api_types import Matches, TournamentInfo, TournamentReport, TournamentResult
from ..cache import sorted_deduped_matches
from ..db_utils import ReplayManager
from ..dependencies import (
    ADMIN_ONLY,
    cache_short,
    db_manager,
    get_replay_manager,
    get_tournament_repo,
)
from ..repositories import TournamentRepo

logger = structlog.get_logger(__name__)

router = APIRouter()


_report_semaphore = asyncio.Semaphore(value=1)


def _require_round_robin(name: str) -> None:
    """404 unless this slug is a configured round-robin tournament.

    ``tournament_games`` now yields bracket slugs too (it reads the persisted
    links), and ``/api/tournaments`` advertises them - but the report builder
    derives team records from ``tournament.TOURNAMENT_MAP`` and raises a
    KeyError for anything else. Every report route checks, not just the read
    one: `generate_tournament_report` fails inside a BackgroundTask, so
    without this the caller gets "OK" and never learns it broke.
    """
    if name not in tournament.TOURNAMENT_MAP:
        raise HTTPException(status_code=404, detail=f"No round-robin report for {name}")


@router.get("/api/is_tournament_game/{match_id}", dependencies=[Depends(cache_short)])
def is_tournament_game(
    match_id: int,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> str | None:
    """The slug of the tournament this match counted toward, or None.

    Reads the persisted link rather than re-deriving membership, so an
    admin's manual link (or exclusion) is reflected here too.
    """
    match_info = sorted_deduped_matches(replay_manager).get(match_id)
    if match_info is None or match_info.tournament is None:
        return None
    return match_info.tournament.slug


@router.get("/api/tournaments", dependencies=[Depends(cache_short)])
def list_tournaments(
    tournament_repo: TournamentRepo = Depends(get_tournament_repo),
) -> list[TournamentInfo]:
    """Every tournament ever run, newest first, with its linked game count.

    Counts come from an aggregate over the link table, so this page doesn't
    depend on the match cache being warm.
    """
    counts = tournament_repo.link_counts_by_slug()
    return [
        TournamentInfo(
            slug=t.slug,
            name=t.name,
            format=t.format,
            status=t.status,
            start_date=t.start_date,
            end_date=t.end_date,
            game_count=counts.get(t.slug, 0),
        )
        for t in tournament_repo.list_tournaments()
    ]


@router.get("/api/tournaments/{slug}/games", dependencies=[Depends(cache_short)])
def tournament_games_for(
    slug: str,
    replay_manager: ReplayManager = Depends(get_replay_manager),
    tournament_repo: TournamentRepo = Depends(get_tournament_repo),
) -> Matches:
    """The matches linked to one tournament, newest first.

    Driven off the persisted links, so this answers "every game of this
    tournament" for a finished bracket whose live state has since been reset.
    Links whose match is missing from the listing are skipped - the link table
    has no FK to matches on purpose (see db.TournamentGame).
    """
    row = tournament_repo.get_tournament_by_slug(slug)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Unknown tournament {slug}")
    known = sorted_deduped_matches(replay_manager)
    linked = [
        known[link.match_id]
        for link in tournament_repo.list_links(row.id)
        if link.match_id in known
    ]
    linked.sort(key=lambda m: m.timestamp, reverse=True)
    return Matches(matches=linked)


@router.get("/api/tournament_results/", dependencies=[Depends(cache_short)])
def get_tournament_results(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> list[TournamentResult]:
    """Get results for all tournaments."""
    replays = sorted_deduped_matches(replay_manager)
    tournament_games = tournament.tournament_games(list(replays.values()))
    return tournament.create_tournament_results(tournament_games)


async def save_report(name: str, save: bool = True) -> TournamentReport:
    """Build (and optionally persist) a tournament report.

    Opens its own DB sessions: this runs as a background task (after the
    request-scoped session is torn down), and the per-match detail loads run
    in worker threads that must not share one session -
    ``load_many_match_details`` gives each thread its own.
    """
    async with _report_semaphore:
        with db_manager.get_replay_manager() as rm:
            replays = sorted_deduped_matches(rm)
        tournament_games = tournament.tournament_games(list(replays.values())).get(
            name, []
        )
        if save is False:
            tournament_games = tournament_games[:5]
        details = await match_details.load_many_match_details(
            [g.id for g in tournament_games], db_manager
        )
        logger.info("finished details", count=len(details))
    results = tournament.tournament_report(name, tournament_games, details)
    if save:
        with db_manager.get_replay_manager() as rm:
            rm.save_tournament_report(results)
    return results


@router.get("/api/tournament_report/{tournament_name}")
async def get_tournament_report(
    background_tasks: BackgroundTasks,
    response: Response,
    tournament_name: str = "2025_2v2_tournament",
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> TournamentReport:
    """Get report for a specific tournament (round-robin only)."""
    _require_round_robin(tournament_name)
    existing = replay_manager.get_tournament_report_by_name(tournament_name)
    if not existing:
        # Don't cache the empty placeholder - the background task fills it in
        # seconds and a cached empty report would look perpetually empty.
        background_tasks.add_task(save_report, tournament_name)
        response.headers["Cache-Control"] = "no-cache"
        return TournamentReport(name="", stats=[])

    response.headers["Cache-Control"] = "private, max-age=60"
    return existing


@router.post(
    "/api/generate_tournament_report/{tournament_name}", dependencies=ADMIN_ONLY
)
async def generate_tournament_report(
    background_tasks: BackgroundTasks,
    tournament_name: str = "2025_2v2_tournament",
) -> str:
    _require_round_robin(tournament_name)
    background_tasks.add_task(save_report, tournament_name)
    return "OK"


@router.post("/api/test_tournament_report/{tournament_name}", dependencies=ADMIN_ONLY)
async def test_tournament_report(
    tournament_name: str = "2025_2v2_tournament",
) -> TournamentReport:
    _require_round_robin(tournament_name)
    return await save_report(tournament_name, save=False)
