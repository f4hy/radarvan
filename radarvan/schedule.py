from db_utils import ReplayManager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import scrape_games
import logging

logger = logging.getLogger(__name__)


async def update_games(replay_manager: ReplayManager) -> None:
    """Get latest updates."""
    logger.info("Updating games.")
    base = scrape_games.BASE
    await scrape_games.get_replay_urls(0, base, replay_manager)
    logger.info("Done updating.")


def get_scheduler(replay_manager: ReplayManager) -> AsyncIOScheduler:
    """Get the scheduler with the tasks on it."""

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        update_games,
        "interval",
        minutes=60,
        args=[replay_manager],
        id="update_games",
    )
    logger.info("Setup scheduler.")
    return scheduler
