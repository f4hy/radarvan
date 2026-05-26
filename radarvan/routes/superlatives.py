"""Superlatives (leaderboard records) endpoints."""

import asyncio
from datetime import date
import structlog

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from .. import match_details, player_rating, superlatives
from ..cache import competitive_matches
from ..db_utils import ReplayManager
from ..dependencies import db_manager, get_replay_manager
from ..notify import notify

logger = structlog.get_logger(__name__)

router = APIRouter()


_recompute_lock = asyncio.Lock()


@router.get("/api/superlatives")
def get_superlatives(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> superlatives.Superlatives:
    """Serve superlatives from the DB if available, otherwise compute on the fly."""
    saved_stats = replay_manager.get_computed_stats()
    if saved_stats:
        return superlatives.Superlatives(
            stats=saved_stats,
            computed_at=saved_stats[0].date_computed,
        )
    logger.info("no saved superlatives")
    return superlatives.Superlatives(stats=[], computed_at=date.today())


async def _do_recompute(
    replay_manager: ReplayManager,
) -> superlatives.Superlatives:
    games = competitive_matches(replay_manager)
    game_list = [
        g
        for g in games.values()
        if g.winning_team > 0 and "mismatch" not in g.incomplete.lower()
    ]
    stale = replay_manager.computed_stats_are_stale(days=3)
    details = await match_details.load_many_superlative_data(
        [g.id for g in game_list], db_manager
    )
    if stale:
        notify(f"Loaded {len(details)} match details for superlatives recompute")
    ratings_and_counts = player_rating.compute_player_ratings(game_list)
    result = superlatives.get_superlatives(
        game_list, details, ratings_and_counts.daily_changes
    )
    replay_manager.clear_computed_stats()
    replay_manager.save_computed_stats(result.stats)
    logger.info("saved computed statistics", count=len(result.stats))
    if stale:
        notify("Recomputed superlatives")

    return result


async def _do_recompute_bg() -> None:
    async with _recompute_lock:
        with db_manager.SessionLocal() as session:
            rm = ReplayManager(session)
            await _do_recompute(rm)
            session.commit()


@router.post("/api/superlatives/recompute")
async def recompute_superlatives(
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    """Trigger superlatives recompute in the background and return immediately."""
    if _recompute_lock.locked():
        raise HTTPException(status_code=409, detail="Recompute already in progress")
    background_tasks.add_task(_do_recompute_bg)
    return {"status": "started"}
