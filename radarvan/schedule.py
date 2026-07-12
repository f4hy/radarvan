"""APScheduler-backed scheduled tasks - periodically scrapes new games, registers
matches, and recomputes superlatives/ratings (``get_scheduler``).

Every job run opens its own DB session via the DatabaseManager: sessions are
not safe to share between overlapping jobs, and a failed transaction on a
process-lifetime session would poison every later run.
"""

from .db_utils import DatabaseManager
from .cache import competitive_matches, invalidate_match_caches
from .matches import register_matches
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import UTC, datetime
import asyncio
from . import missing_maps as missing_maps_module
from . import scrape_games
from . import player_profile as player_profile_module
from . import superlatives as superlatives_module
from . import player_rating as player_rating_module
import structlog
from .notify import notify_async

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
        await notify_async(f"DEBUG:Done updating, found {len(paths)}.")


async def compute_and_save_superlatives(db_manager: DatabaseManager) -> None:
    """Recompute all superlatives and persist them, replacing any previous results."""
    start = datetime.now(UTC)
    logger.info(
        "computing superlatives", started_at=start.strftime("%Y-%m-%d %H:%M:%S")
    )
    with db_manager.get_replay_manager() as replay_manager:
        stale = replay_manager.computed_stats_are_stale(days=3)
        if stale:
            await notify_async(
                f"Computing records (started at {start:%Y-%m-%d %H:%M:%S})"
            )
        # Same game set as POST /api/superlatives/recompute (routes/superlatives):
        # competitive_matches already excludes incomplete/mismatch games, so the
        # nightly run and a manual trigger always agree on which matches count.
        # Blocking DB work on a cache miss - keep it off the event loop.
        games = await asyncio.to_thread(competitive_matches, replay_manager)
        competitive = [m for m in games.values() if m.winning_team > 0]
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
        await notify_async(msg)


async def compute_and_save_player_profiles(db_manager: DatabaseManager) -> None:
    """Recompute all player profile deep stats and persist them as a batch.

    Uses the same ``cache.competitive_matches`` set as the on-demand
    ``POST /api/player_profile/recompute`` route (routes/profile.py), so the
    nightly run and a manual trigger always agree on which matches count.
    """
    start = datetime.now(UTC)
    logger.info(
        "computing player profiles", started_at=start.strftime("%Y-%m-%d %H:%M:%S")
    )
    with db_manager.get_replay_manager() as replay_manager:
        stale = replay_manager.player_profiles_are_stale(days=3)
        games = list(competitive_matches(replay_manager).values())
        data = await player_profile_module.load_many_profile_data(games, db_manager)
        logger.info("loaded profile data", count=len(data))
        # Pure computation, but heavy - run off the event loop.
        profiles = await asyncio.to_thread(
            player_profile_module.compute_all_profiles, data
        )
        replay_manager.save_player_profiles(
            profiles, player_profile_module.PROFILE_VERSION
        )
    duration = datetime.now(UTC) - start
    logger.info(
        "saved player profiles",
        count=len(profiles),
        started_at=start.strftime("%Y-%m-%d %H:%M:%S"),
        took=str(duration),
    )
    if stale:
        await notify_async(f"Saved {len(profiles)} player profiles, took {duration}.")


async def sync_maps_to_cncstats(
    db_manager: DatabaseManager, max_to_update: int = 25
) -> None:
    """Push maps we host to the cncstats CDN so game clients can fetch them.

    The lobby's "Radarvan Pick" hands the client a map CRC and expects the CDN
    to serve the bytes for it. Without this pass the CDN only ever gets maps
    that some player's client happened to upload, so a map we picked can be one
    nobody can download. Skips maps already marked synced, and checks
    /map_exists before pushing, so a steady state costs one HEAD-ish call per
    new map and nothing at all afterwards.
    """
    if not missing_maps_module.cncstats_push_enabled():
        logger.info("cncstats push not configured; skipping map sync")
        return
    with db_manager.get_replay_manager() as replay_manager:
        results = await missing_maps_module.push_unsynced_maps(
            replay_manager, limit=max_to_update
        )
    pushed = sum(1 for r in results if r.pushed)
    errors = [r.map_name for r in results if r.error is not None]
    logger.info(
        "synced maps to cncstats",
        considered=len(results),
        pushed=pushed,
        already_present=sum(1 for r in results if r.already_present),
        errors=errors,
    )
    if pushed:
        await notify_async(f"Pushed {pushed} map(s) to the cncstats CDN.")


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
    # After superlatives: that run leaves match_details_cache warm, so this
    # second full pass over the same matches is DB-read-only.
    scheduler.add_job(
        compute_and_save_player_profiles,
        "cron",
        hour=4,
        minute=30,
        args=[db_manager],
        id="compute_player_profiles",
    )
    # Keep the map CDN in step with the maps we host: the lobby map pick sends
    # clients to cncstats by CRC, so a map that never got pushed is a pick
    # nobody can download.
    scheduler.add_job(
        sync_maps_to_cncstats,
        "interval",
        minutes=60 * 6,
        args=[db_manager],
        id="sync_maps_to_cncstats",
    )
    logger.info("Setup scheduler.")
    return scheduler
