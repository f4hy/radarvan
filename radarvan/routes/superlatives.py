"""Superlatives (leaderboard records) endpoints."""

from datetime import UTC, datetime
import structlog

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from .. import computed_stats, general_stats, opening_book, superlatives
from ..db_utils import ReplayManager
from ..dependencies import OPS_ADMIN, cache_short, db_manager, get_replay_manager

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["superlatives"])

# Operational routes the admin control panel drives. Cookie-authenticated, so
# included in main.py without the API-key dependency; every route here carries
# `dependencies=OPS_ADMIN`.
session_router = APIRouter(tags=["superlatives"])


@router.get("/api/superlatives", dependencies=[Depends(cache_short)])
def get_superlatives(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> superlatives.Superlatives:
    """Serve superlatives from the DB if available, otherwise compute on the fly."""
    saved_stats = [
        s
        for s in replay_manager.get_computed_stats()
        if not s.stat_name.startswith(general_stats.GENERAL_VALUE_STAT_PREFIX)
        and not s.stat_name.startswith(opening_book.OPENING_STAT_PREFIX)
    ]
    if saved_stats:
        return superlatives.Superlatives(
            stats=saved_stats,
            computed_at=saved_stats[0].date_computed,
        )
    logger.info("no saved superlatives")
    return superlatives.Superlatives(stats=[], computed_at=datetime.now(UTC).date())


@session_router.post("/api/superlatives/recompute", dependencies=OPS_ADMIN)
async def recompute_superlatives(
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    """Trigger superlatives recompute in the background and return immediately."""
    if not computed_stats.try_reserve_recompute():
        raise HTTPException(status_code=409, detail="Recompute already in progress")
    background_tasks.add_task(computed_stats.reserved_recompute, db_manager)
    return {"status": "started"}
