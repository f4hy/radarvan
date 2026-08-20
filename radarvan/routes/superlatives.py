"""Superlatives (leaderboard records) endpoints."""

import asyncio
from datetime import UTC, datetime
import structlog

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from .. import general_stats, player_rating, superlatives
from ..api_types import Statistic
from ..cache import competitive_matches
from ..db_utils import ReplayManager
from ..dependencies import OPS_ADMIN, cache_short, db_manager, get_replay_manager
from ..notify import notify_async

logger = structlog.get_logger(__name__)

router = APIRouter()

# Operational routes the admin control panel drives. Cookie-authenticated, so
# included in main.py without the API-key dependency; every route here carries
# `dependencies=OPS_ADMIN`.
session_router = APIRouter()


_recompute_lock = asyncio.Lock()


@router.get("/api/superlatives", dependencies=[Depends(cache_short)])
def get_superlatives(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> superlatives.Superlatives:
    """Serve superlatives from the DB if available, otherwise compute on the fly."""
    saved_stats = [
        s
        for s in replay_manager.get_computed_stats()
        if not s.stat_name.startswith(general_stats.GENERAL_VALUE_STAT_PREFIX)
    ]
    if saved_stats:
        return superlatives.Superlatives(
            stats=saved_stats,
            computed_at=saved_stats[0].date_computed,
        )
    logger.info("no saved superlatives")
    return superlatives.Superlatives(stats=[], computed_at=datetime.now(UTC).date())


async def _do_recompute(
    replay_manager: ReplayManager,
) -> superlatives.Superlatives:
    # competitive_matches already excludes incomplete/mismatch games.
    game_list = [
        g for g in competitive_matches(replay_manager).values() if g.winning_team > 0
    ]
    stale = replay_manager.computed_stats_are_stale(days=3)
    details = await superlatives.load_many_superlative_data(
        [g.id for g in game_list], db_manager
    )
    if stale:
        await notify_async(
            f"Loaded {len(details)} match details for superlatives recompute"
        )
    # Pure computation, but heavy - run off the event loop (mirrors
    # schedule.compute_and_save_superlatives).
    ratings_and_counts = await asyncio.to_thread(
        player_rating.compute_player_ratings, game_list
    )
    result = await asyncio.to_thread(
        superlatives.get_superlatives,
        game_list,
        details,
        ratings_and_counts.daily_changes,
    )
    value_stats = await asyncio.to_thread(
        general_stats.general_value_stats, game_list, details
    )
    computed_at = datetime.now(UTC).date()
    value_stat_rows = [
        Statistic(
            stat_name=f"{general_stats.GENERAL_VALUE_STAT_PREFIX}{kind}",
            date_computed=computed_at,
            value=float(total),
            player=str(int(general)),
        )
        for general, (destroyed, lost) in value_stats.items()
        for kind, total in (("destroyed", destroyed), ("lost", lost))
    ]
    result.stats = result.stats + value_stat_rows
    replay_manager.clear_computed_stats()
    replay_manager.save_computed_stats(result.stats)
    logger.info(
        "saved computed statistics",
        count=len(result.stats),
        general_value_rows=len(value_stat_rows),
    )
    if stale:
        await notify_async("Recomputed superlatives")

    return result


async def _do_recompute_bg() -> None:
    async with _recompute_lock:
        with db_manager.SessionLocal() as session:
            rm = ReplayManager(session)
            await _do_recompute(rm)
            session.commit()


@session_router.post("/api/superlatives/recompute", dependencies=OPS_ADMIN)
async def recompute_superlatives(
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    """Trigger superlatives recompute in the background and return immediately."""
    if _recompute_lock.locked():
        raise HTTPException(status_code=409, detail="Recompute already in progress")
    background_tasks.add_task(_do_recompute_bg)
    return {"status": "started"}
