from db_utils import ReplayManager
from matches import register_matches
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import scrape_games
import logging
from notify import notify

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
    logger.info("Setup scheduler.")
    return scheduler
