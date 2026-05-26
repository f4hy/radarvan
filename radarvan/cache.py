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
from . import replay_files
from .dependencies import db_manager

logger = structlog.get_logger(__name__)


_latest_ts_cache: TTLCache[str, str] = TTLCache(maxsize=1, ttl=60)

# cachetools caches are not thread-safe; sync endpoints run in uvicorn's
# threadpool, so concurrent access can corrupt LRU bookkeeping. Each @cached
# below gets its own lock. cachetools holds the lock only around the cache
# get/set (and cache_clear), never around the wrapped call, so there is no
# deadlock even when one cached function calls another.
_sorted_lock = threading.Lock()
_competitive_lock = threading.Lock()
_details_lock = threading.Lock()


def latest_match_ts(replay_manager: ReplayManager) -> str:
    if "v" not in _latest_ts_cache:
        ts = replay_manager.latest_match_created_at()
        _latest_ts_cache["v"] = ts.isoformat() if ts else ""
    return _latest_ts_cache["v"]


def details_key(match_id: int, replay_manager: ReplayManager) -> str:
    return str(match_id)


@cached(cache=LRUCache(maxsize=2), key=latest_match_ts, lock=_sorted_lock)
def sorted_deduped_matches(replay_manager: ReplayManager) -> dict[int, MatchInfo]:
    match_infos = matches.get_match_infos(replay_manager)
    deduped = {i.id: i for i in match_infos if i}
    logger.info("got parsed replays", count=len(deduped))
    sorted_matches = dict(
        sorted(deduped.items(), key=lambda item: item[1].timestamp, reverse=True)
    )
    return sorted_matches


@cached(cache=LRUCache(maxsize=2), key=latest_match_ts, lock=_competitive_lock)
def competitive_matches(replay_manager: ReplayManager) -> dict[int, MatchInfo]:
    all_matches = sorted_deduped_matches(replay_manager)
    filtered = {
        m.id: m
        for m in all_matches.values()
        if game_composition.competitive_game_filter(comp=m.composition)
        and player_ids.all_teams_have_group_player(m.players)
    }
    return filtered


@cached(cache=LRUCache(maxsize=100), key=details_key, lock=_details_lock)
def details_from_id(
    match_id: int, replay_manager: ReplayManager
) -> MatchDetails | None:
    rep = replay_manager.get_replay_json_by_match_id(match_id)
    if rep is None:
        return None
    par = replay_files.parse_replay(rep.replay_file_url, replay_manager)
    return match_details.match_details_from_replay(par)


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
    _latest_ts_cache.clear()
    sorted_deduped_matches.cache_clear()
    competitive_matches.cache_clear()
    details_from_id.cache_clear()
    _ensure_warm_thread()
    _warm_event.set()
