"""Tournament endpoints."""

import asyncio
import structlog

from fastapi import APIRouter, BackgroundTasks, Depends, Response

from .. import tournament
from ..api_types import TournamentReport, TournamentResult
from ..cache import details_from_id, sorted_deduped_matches
from ..db_utils import ReplayManager
from ..dependencies import cache_short, get_replay_manager

logger = structlog.get_logger(__name__)

router = APIRouter()


_report_semaphore = asyncio.Semaphore(value=1)


@router.get("/api/is_tournament_game/{match_id}", dependencies=[Depends(cache_short)])
def is_tournament_game(
    match_id: int,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> str | None:
    """test if a match is a tournament game."""
    match_info = sorted_deduped_matches(replay_manager).get(match_id)
    if match_info is None:
        return None
    return tournament.is_tournament_game(match_info)


@router.get("/api/tournament_results/", dependencies=[Depends(cache_short)])
def get_tournament_results(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> list[TournamentResult]:
    """Get results for all tournaments."""
    replays = sorted_deduped_matches(replay_manager)
    tournament_games = tournament.tournament_games(list(replays.values()))
    results = tournament.create_tournament_results(tournament_games)
    return results


async def save_report(
    name: str, replay_manager: ReplayManager, save: bool = True
) -> TournamentReport:
    async with _report_semaphore:
        replays = sorted_deduped_matches(replay_manager)
        tournament_games = tournament.tournament_games(list(replays.values())).get(
            name, []
        )
        if save is False:
            tournament_games = tournament_games[:5]
        details = await asyncio.gather(
            *[
                asyncio.to_thread(details_from_id, g.id, replay_manager)
                for g in tournament_games
            ]
        )
        logger.info("finished details", count=len(details))
    valid_details = [d for d in details if d is not None]
    results = tournament.tournament_report(name, tournament_games, valid_details)
    if save:
        replay_manager.save_tournament_report(results)
    return results


@router.get("/api/tournament_report/{tournament_name}")
async def get_tournament_report(
    background_tasks: BackgroundTasks,
    response: Response,
    tournament_name: str = "2025_2v2_tournament",
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> TournamentReport:
    """Get report for a specific tournament."""
    existing = replay_manager.get_tournament_report_by_name(tournament_name)
    if not existing:
        # Don't cache the empty placeholder — the background task fills it in
        # seconds and a cached empty report would look perpetually empty.
        background_tasks.add_task(save_report, tournament_name, replay_manager)
        response.headers["Cache-Control"] = "no-cache"
        return TournamentReport(name="", stats=[])

    response.headers["Cache-Control"] = "private, max-age=60"
    return existing


@router.post("/api/generate_tournament_report/{tournament_name}")
async def generate_tournament_report(
    background_tasks: BackgroundTasks,
    tournament_name: str = "2025_2v2_tournament",
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> str:
    background_tasks.add_task(save_report, tournament_name, replay_manager)
    return "OK"


@router.post("/api/test_tournament_report/{tournament_name}")
async def test_tournament_report(
    background_tasks: BackgroundTasks,
    tournament_name: str = "2025_2v2_tournament",
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> TournamentReport:
    report = await save_report(tournament_name, replay_manager, save=False)
    return report
