from .db_utils import ReplayManager
from .matches import register_matches
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from . import scrape_games
from . import game_composition
from . import superlatives as superlatives_module
from . import matches as matches_module
import logging
from .notify import notify

logger = logging.getLogger(__name__)


async def update_games(
    replay_manager: ReplayManager,
    days: int = 0,
    do_notify: bool = False,
) -> None:
    """Get latest updates."""
    logger.info("Updating games.")
    base = scrape_games.BASE
    paths = await scrape_games.get_replay_urls(days, base, replay_manager)
    register_matches(replay_manager)
    msg = f"Done updating, found {len(paths)}."
    logger.info(msg)
    if do_notify:
        notify("DEBUG:" + msg)


async def compute_and_save_superlatives(replay_manager: ReplayManager) -> None:
    """Recompute all superlatives and persist them, replacing any previous results."""
    logger.info("Computing superlatives.")
    match_infos = matches_module.get_match_infos(replay_manager)
    competitive = [
        m
        for m in match_infos
        if m and game_composition.competitive_game_filter(comp=m.composition)
    ]
    result = superlatives_module.get_superlatives(competitive)
    replay_manager.clear_computed_stats()
    replay_manager.save_computed_stats(result.stats)
    logger.info(f"Saved {len(result.stats)} computed statistics.")


def get_scheduler(replay_manager: ReplayManager) -> AsyncIOScheduler:
    """Get the scheduler with the tasks on it."""

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        update_games,
        "date",
        run_date=datetime.now(),
        args=[replay_manager, 1],
        id="update_games_init",
    )
    scheduler.add_job(
        update_games,
        "interval",
        minutes=60,
        args=[replay_manager, 1, False],
        id="update_games",
    )
    scheduler.add_job(
        compute_and_save_superlatives,
        "cron",
        hour=4,
        minute=0,
        args=[replay_manager],
        id="compute_superlatives",
    )
    logger.info("Setup scheduler.")
    return scheduler
