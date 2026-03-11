from .db_utils import ReplayManager, DatabaseManager
from .matches import register_matches
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from . import scrape_games
from . import game_composition
from . import match_details as match_details_module
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


async def compute_and_save_superlatives(
    replay_manager: ReplayManager, db_manager: DatabaseManager
) -> None:
    """Recompute all superlatives and persist them, replacing any previous results."""
    start = datetime.now()
    logger.info(f"Computing superlatives (started at {start:%Y-%m-%d %H:%M:%S}).")
    notify(message=f"Computing records (started at {start:%Y-%m-%d %H:%M:%S})")
    competitive = [
        m
        for m in matches_module.get_match_infos(replay_manager)
        if m
        and game_composition.competitive_game_filter(comp=m.composition)
        and m.winning_team > 0
        and "mismatch" not in m.incomplete.lower()
    ]
    match_ids = [m.id for m in competitive]
    details = await match_details_module.load_many_superlative_data(
        match_ids, db_manager
    )
    logger.info(f"Loaded {len(details)} match details for superlatives.")
    result = superlatives_module.get_superlatives(competitive, details)
    replay_manager.clear_computed_stats()
    replay_manager.save_computed_stats(result.stats)
    duration = datetime.now() - start
    msg = f"Saved {len(result.stats)} computed statistics for Records page. Started at {start:%Y-%m-%d %H:%M:%S}, took {duration}."
    logger.info(msg)
    notify(message=msg)


def get_scheduler(
    replay_manager: ReplayManager, db_manager: DatabaseManager
) -> AsyncIOScheduler:
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
        args=[replay_manager, db_manager],
        id="compute_superlatives",
    )
    logger.info("Setup scheduler.")
    return scheduler
