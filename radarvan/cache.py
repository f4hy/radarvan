"""In-process match caches, cache warming, and invalidation.

The cachetools LRUCaches here are process-global singletons; they MUST be
defined once (here) so that `cache_clear()` from one router invalidates the
same cache that another router reads.

Cache-warming runs on a single long-lived background thread driven by
threading.Event. We must not spawn a fresh worker per invalidation:
cachetools caches are not thread-safe, and concurrent writes corrupt them.
"""

import structlog
import threading

from cachetools import LRUCache, TTLCache, cached

from . import game_composition, matches, player_ids, player_rating
from .api_types import MatchInfo, MatchDetails
from .db_utils import ReplayManager
from . import match_details
from .dependencies import db_manager

logger = structlog.get_logger(__name__)


# cachetools caches are not thread-safe; sync endpoints run in uvicorn's
# threadpool, so concurrent access can corrupt LRU bookkeeping. Each @cached
# below gets its own lock. cachetools holds the lock only around the cache
# get/set (and cache_clear), never around the wrapped call, so there is no
# deadlock even when one cached function calls another.
_latest_ts_lock = threading.Lock()
_sorted_lock = threading.Lock()
_competitive_lock = threading.Lock()
_details_lock = threading.Lock()
_maps_by_count_lock = threading.Lock()


@cached(
    cache=TTLCache(maxsize=1, ttl=60),
    key=lambda replay_manager: "v",
    lock=_latest_ts_lock,
)
def latest_match_ts(replay_manager: ReplayManager) -> str:
    ts = replay_manager.latest_match_created_at()
    return ts.isoformat() if ts else ""


def details_key(match_id: int, replay_manager: ReplayManager) -> str:
    return str(match_id)


@cached(
    cache=TTLCache(maxsize=1, ttl=600),
    key=lambda replay_manager: "maps",
    lock=_maps_by_count_lock,
)
def maps_by_player_count(replay_manager: ReplayManager) -> dict[int, list[str]]:
    """Maps grouped by start-position count.

    Map geometry changes rarely (only when maps are added), but the underlying
    query loads every MapData row + its JSON blob, so this short-TTL cache keeps
    the voting endpoints from re-scanning the table on every request. Cleared by
    invalidate_match_caches() as well, so a re-scrape surfaces new maps promptly.
    """
    return replay_manager.list_maps_by_player_count()


@cached(cache=LRUCache(maxsize=2), key=latest_match_ts, lock=_sorted_lock)
def sorted_deduped_matches(replay_manager: ReplayManager) -> dict[int, MatchInfo]:
    match_infos = matches.get_match_infos(replay_manager)
    deduped = {i.id: i for i in match_infos if i}
    logger.info("got parsed replays", count=len(deduped))
    return dict(
        sorted(deduped.items(), key=lambda item: item[1].timestamp, reverse=True)
    )


@cached(cache=LRUCache(maxsize=2), key=latest_match_ts, lock=_competitive_lock)
def competitive_matches(replay_manager: ReplayManager) -> dict[int, MatchInfo]:
    all_matches = sorted_deduped_matches(replay_manager)
    return {
        m.id: m
        for m in all_matches.values()
        # Disconnects/desyncs/quit-early/too-short games aren't real competitive
        # results (a balanced 2v2 that ends in a 3-min disconnect would otherwise
        # pass the composition filter and pollute stats/ratings/upsets).
        if not m.incomplete
        and game_composition.competitive_game_filter(comp=m.composition)
        and player_ids.all_teams_have_group_player(m.players)
    }


@cached(cache=LRUCache(maxsize=100), key=details_key, lock=_details_lock)
def details_from_id(
    match_id: int, replay_manager: ReplayManager
) -> MatchDetails | None:
    """Resolve MatchDetails through a two-tier cache.

    This in-process LRU (the decorator) fronts the durable, versioned DB cache
    implemented in `match_details.load_match_details` (`MatchDetailsCache`): a
    DB hit at the current DETAILS_VERSION skips re-reading + re-validating the
    multi-MB raw replay from S3; a miss recomputes and writes the small derived
    projection back. The same loader backs the superlatives / bulk paths, so
    every caller shares one warm cache. Reparse explicitly deletes the row (raw
    replay changed but version did not); a DETAILS_VERSION bump invalidates all
    rows implicitly.
    """
    return match_details.load_match_details(match_id, replay_manager)


def _warm_caches() -> None:
    with db_manager.get_replay_manager() as rm:
        sorted_deduped_matches(rm)
        comp = competitive_matches(rm)
        player_rating.compute_player_ratings(list(comp.values()))


# Cache warming runs on a single long-lived background thread driven by an
# Event. Event.set() / clear() are thread-safe; multiple sets coalesce so a
# burst of invalidations produces at most one extra warm.
_warm_event = threading.Event()
_warm_thread_started = False
_warm_thread_lock = threading.Lock()


def _warm_loop() -> None:
    while True:
        _warm_event.wait()
        _warm_event.clear()
        try:
            _warm_caches()
        except Exception:
            logger.exception("warm_caches failed")


def _ensure_warm_thread() -> None:
    global _warm_thread_started
    with _warm_thread_lock:
        if _warm_thread_started:
            return
        threading.Thread(target=_warm_loop, daemon=True, name="cache-warm").start()
        _warm_thread_started = True


def warm_caches() -> None:
    """Synchronously warm the match caches. Called during app startup."""
    _ensure_warm_thread()
    _warm_caches()


def invalidate_match_caches() -> None:
    """Drop all match-related caches and request a background re-warm."""
    latest_match_ts.cache_clear()
    sorted_deduped_matches.cache_clear()
    competitive_matches.cache_clear()
    details_from_id.cache_clear()
    maps_by_player_count.cache_clear()
    _ensure_warm_thread()
    _warm_event.set()
