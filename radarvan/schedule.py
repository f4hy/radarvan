"""APScheduler-backed scheduled tasks - periodically scrapes new games, registers
matches, and recomputes superlatives/ratings (``get_scheduler``).

Every job run opens its own DB session via the DatabaseManager: sessions are
not safe to share between overlapping jobs, and a failed transaction on a
process-lifetime session would poison every later run.
"""

from .db_utils import DatabaseManager
from .cache import invalidate_match_caches
from .matches import register_matches
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import UTC, datetime
import asyncio
from . import scrape_games
from . import game_composition
from . import superlatives as superlatives_module
from . import matches as matches_module
from . import player_rating as player_rating_module
import structlog
from .notify import notify

logger = structlog.get_logger(__name__)


async def update_games(
    db_manager: DatabaseManager,
    days: int = 0,
    do_notify: bool = False,
) -> None:
    """Get latest updates."""
    logger.info("Updating games.")
    base = scrape_games.BASE
    with db_manager.get_replay_manager() as replay_manager:
        paths = await scrape_games.get_replay_urls(days, base, replay_manager)
        # register_matches is blocking (cncstats HTTP + S3 I/O); keep it off
        # the event loop so the API stays responsive during a scrape.
        await asyncio.to_thread(register_matches, replay_manager)
    invalidate_match_caches()
    logger.info("done updating", found=len(paths))
    if do_notify:
        notify(f"DEBUG:Done updating, found {len(paths)}.")


async def compute_and_save_superlatives(db_manager: DatabaseManager) -> None:
    """Recompute all superlatives and persist them, replacing any previous results."""
    start = datetime.now(UTC)
    logger.info(
        "computing superlatives", started_at=start.strftime("%Y-%m-%d %H:%M:%S")
    )
    with db_manager.get_replay_manager() as replay_manager:
        stale = replay_manager.computed_stats_are_stale(days=3)
        if stale:
            notify(message=f"Computing records (started at {start:%Y-%m-%d %H:%M:%S})")
        all_matches = await asyncio.to_thread(
            matches_module.get_match_infos, replay_manager
        )
        competitive = [
            m
            for m in all_matches
            if m
            and game_composition.competitive_game_filter(comp=m.composition)
            and m.winning_team > 0
            and "mismatch" not in m.incomplete.lower()
        ]
        match_ids = [m.id for m in competitive]
        details = await superlatives_module.load_many_superlative_data(
            match_ids, db_manager
        )
        logger.info("loaded match details for superlatives", count=len(details))
        # Pure computation, but heavy - run off the event loop.
        ratings_and_counts = await asyncio.to_thread(
            player_rating_module.compute_player_ratings, competitive
        )
        result = await asyncio.to_thread(
            superlatives_module.get_superlatives,
            competitive,
            details,
            ratings_and_counts.daily_changes,
        )
        replay_manager.clear_computed_stats()
        replay_manager.save_computed_stats(result.stats)
    duration = datetime.now(UTC) - start
    logger.info(
        "saved computed statistics",
        count=len(result.stats),
        started_at=start.strftime("%Y-%m-%d %H:%M:%S"),
        took=str(duration),
    )
    if stale:
        msg = f"Saved {len(result.stats)} computed statistics for Records page. Started at {start:%Y-%m-%d %H:%M:%S}, took {duration}."
        notify(message=msg)


def get_scheduler(db_manager: DatabaseManager) -> AsyncIOScheduler:
    """Get the scheduler with the tasks on it."""

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        update_games,
        "date",
        run_date=datetime.now(UTC),
        args=[db_manager, 1],
        id="update_games_init",
    )
    scheduler.add_job(
        update_games,
        "interval",
        minutes=60 * 6,
        args=[db_manager, 1, False],
        id="update_games",
    )
    scheduler.add_job(
        compute_and_save_superlatives,
        "cron",
        hour=4,
        minute=0,
        args=[db_manager],
        id="compute_superlatives",
    )
    logger.info("Setup scheduler.")
    return scheduler
