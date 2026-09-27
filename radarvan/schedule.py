"""Scheduled tasks - scrape and register new games, recompute superlatives,
profiles and the game-night LLM recaps. Run on one-off dynos via ``radarvan.jobs``.

Every job run opens its own DB session via the DatabaseManager: sessions are
not safe to share between overlapping jobs, and a failed transaction on a
process-lifetime session would poison every later run.
"""

from .db_utils import DatabaseManager, ReplayManager
from .cache import competitive_matches
from .matches import get_match_infos, register_matches
from .repositories import BracketRepo, GameNightSummaryRepo, MatchBlurbRepo
from . import computed_stats, queries
from . import tournament_membership
from datetime import UTC, datetime
import asyncio
from . import scrape_games
from . import player_profile as player_profile_module
import structlog
from .notify import notify_async

logger = structlog.get_logger(__name__)


def _sync_tournament_links(replay_manager: ReplayManager) -> dict[str, int]:
    """Persist tournament membership for the games registered just now.

    Builds its own match list via ``get_match_infos`` rather than reading the
    cache: it needs the games registered moments ago, which the cached list
    predates. Admin-set links are untouched.
    """
    games = get_match_infos(replay_manager)
    return tournament_membership.sync_links(
        replay_manager, BracketRepo(replay_manager.session), games
    )


async def update_games(db_manager: DatabaseManager, days: int = 1) -> None:
    """Scrape the last ``days`` of replays, register them and link tournaments."""
    # Doesn't invalidate: a job process is about to exit, and the web dyno sees
    # new matches through the CORPUS probe. In-process callers invalidate after.
    logger.info("Updating games.")
    base = scrape_games.BASE
    with db_manager.get_replay_manager() as replay_manager:
        paths = await scrape_games.get_replay_urls(days, base, replay_manager)
        # register_matches is blocking (cncstats HTTP + S3 I/O); keep it off
        # the event loop so the API stays responsive during a scrape.
        await asyncio.to_thread(register_matches, replay_manager)
        # Sequential to_thread calls may share this session; concurrent ones
        # may not.
        await asyncio.to_thread(_sync_tournament_links, replay_manager)
    logger.info("done updating", found=len(paths))


async def compute_and_save_superlatives(db_manager: DatabaseManager) -> None:
    """Nightly records/generals/opening-book refresh.

    Skips rather than queues behind a manual run: waiting would only redo the
    identical full-corpus pass.
    """
    try:
        await computed_stats.recompute(db_manager)
    except computed_stats.RecomputeBusy:
        logger.info("skipping scheduled recompute; another process is running one")


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


async def compute_game_night_summary(db_manager: DatabaseManager) -> None:
    """Write the LLM game-night recap for the most recent *closed* night.

    **The only scheduled job in this app that spends money**, so what it will
    and won't do is deliberately narrow:

    - It looks at one night: the latest whose game-night key is behind the one
      currently in progress (``latest_closed_night``). Nothing older is ever
      revisited, so deploying this does not backfill years of history - it
      writes at most one row per run, and none at all once that night has one.
    - A night still being played is never summarized. The row is permanent
      (nothing regenerates), so summarizing at 1am would freeze a half-finished
      evening as *the* recap of it.
    - A missed run costs the skipped night its recap rather than queueing up
      several calls; the deterministic recap still renders for every night.

    Scheduled well after the 5am US Eastern game-night rollover for that
    reason - see ``radarvan.jobs``.
    """
    # Imported here, not at module scope: the LLM SDKs cost ~1s and ~54 MB,
    # which the non-LLM jobs' 512 MB one-off dynos shouldn't pay.
    from .commentary import llm, night_summary

    if not llm.commentary_available():
        logger.info("skipping game night summary: no LLM provider configured")
        return
    with db_manager.get_replay_manager() as replay_manager:
        all_games = await asyncio.to_thread(queries.all_games, replay_manager)
        night = queries.latest_closed_night(all_games)
        if night is None:
            logger.info("no closed game night to summarize")
            return
        summaries = GameNightSummaryRepo(replay_manager.session)
        if summaries.has_night_summary(night):
            logger.info("game night already summarized", night=str(night))
            return
        played = [game for game in all_games if game.date == night]
        if len(played) < night_summary.MIN_MATCHES_FOR_SUMMARY:
            logger.info(
                "skipping game night summary: too few games",
                night=str(night),
                games=len(played),
            )
            return
        competitive = await asyncio.to_thread(queries.competitive_games, replay_manager)
        logger.info(
            "generating game night summary", night=str(night), games=len(played)
        )
        night_games = await queries.build_night_recap(
            night, all_games, competitive, db_manager
        )
        await night_summary.generate_and_store(
            night_games.recap, queries.night_narratives(night_games), summaries
        )
    await notify_async(f"Wrote the game night recap for {night} ({len(played)} games).")


async def compute_match_blurbs(db_manager: DatabaseManager) -> None:
    """Caption the top matches of the latest *closed* night. Billed; capped per night."""
    from .commentary import llm, match_blurb

    if not llm.commentary_available():
        logger.info("skipping match blurbs: no LLM provider configured")
        return
    with db_manager.get_replay_manager() as replay_manager:
        all_games = await asyncio.to_thread(queries.all_games, replay_manager)
        night = queries.latest_closed_night(all_games)
        if night is None:
            logger.info("no closed game night to caption")
            return
        competitive = await asyncio.to_thread(queries.competitive_games, replay_manager)
        night_games = await queries.build_night_recap(
            night, all_games, competitive, db_manager
        )
        # Each blurb commits as it is written, so a failure keeps the paid ones.
        await match_blurb.generate_night_blurbs(
            night_games, MatchBlurbRepo(replay_manager.session)
        )
