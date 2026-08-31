"""Match-derived values, cache warming, and invalidation.

The derivations here are declared with `radarvan.derived.derived`, which supplies
the bound and the lock and folds the dependency's version token into every key -
so there's no lock or `LRUCache` in this file, and `invalidate_match_caches()`
names no single cache: it bumps two version tokens, and every derivation over
them (here and in seven other modules) stops being addressable. See
`radarvan/derived/__init__.py`.

Cache-warming runs on a single long-lived background thread driven by a
threading.Event - a fresh worker per invalidation would waste the dyno's one
core recomputing the same thing on a burst. (Not for thread safety: the
decorator already locks every cache and single-flights concurrent misses.)
"""

import structlog
import threading

from . import game_composition, matches, player_rating
from .api_types import MatchInfo, MatchDetails
from .db_utils import ReplayManager
from . import match_details
from .dependencies import db_manager
from .derived import CORPUS, MAPS, derived, invalidate
from .repositories.maps import normalize_map_name

logger = structlog.get_logger(__name__)


@derived(on=MAPS, maxsize=1)
def maps_by_player_count(replay_manager: ReplayManager) -> dict[int, list[str]]:
    """Maps grouped by start-position count.

    Map geometry changes rarely, but the underlying query loads every MapData row
    plus its JSON blob, so caching keeps the voting endpoints from re-scanning the
    table on every request. Keyed on MAPS, whose probe is a single aggregate over
    `map_data.updated_at` - so a re-parsed or newly fetched map surfaces without
    the 10-minute TTL this used to carry.
    """
    return replay_manager.list_maps_by_player_count()


@derived(on=MAPS, maxsize=1)
def map_name_index(replay_manager: ReplayManager) -> dict[str, str]:
    """{normalized map name -> canonical MapData.map_name}, loaded once and cached.

    Every played map has (at most) one MapData row, and `map_name` is stored with
    the exact case/punctuation of the S3-hosted asset - resolving through this
    index is how map-image serving (routes/maps.py) finds the right S3 object
    without guessing at case variants. Loading the full (small) table once beats a
    per-request query.
    """
    return {normalize_map_name(name): name for name in replay_manager.list_map_names()}


def resolve_map_name_cached(replay_manager: ReplayManager, map_name: str) -> str | None:
    """Like `ReplayManager.resolve_map_name`, but served from `map_name_index`."""
    return map_name_index(replay_manager).get(normalize_map_name(map_name))


@derived(on=CORPUS, maxsize=1)
def sorted_deduped_matches(replay_manager: ReplayManager) -> dict[int, MatchInfo]:
    match_infos = matches.get_match_infos(replay_manager)
    deduped = {i.id: i for i in match_infos if i}
    logger.info("got parsed replays", count=len(deduped))
    return dict(
        sorted(deduped.items(), key=lambda item: item[1].timestamp, reverse=True)
    )


@derived(on=CORPUS, maxsize=1)
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
        and m.roster().all_teams_have_group_player()
    }


@derived(on=CORPUS, maxsize=30)
def details_from_id(
    match_id: int, replay_manager: ReplayManager
) -> MatchDetails | None:
    """Resolve MatchDetails through a two-tier cache.

    This in-process LRU fronts the durable, versioned DB cache implemented in
    `match_details.load_match_details` (`MatchDetailsCache`): a DB hit at the
    current DETAILS_VERSION skips re-reading + re-validating the multi-MB raw
    replay from S3; a miss recomputes and writes the small derived projection
    back. The same loader backs the superlatives / bulk paths, so every caller
    shares one warm cache.

    The two tiers invalidate on different things and both are needed. This tier is
    keyed on CORPUS, so a reparse or override makes the old entry unreachable
    without anyone clearing it. The durable tier is keyed on DETAILS_VERSION,
    which survives restarts and covers a derivation-logic change; a reparse
    additionally deletes its row explicitly, because the raw replay changed while
    the version did not.
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
    """Mark the match corpus and map registry as changed; request a re-warm.

    No cache is named. Bumping the two version tokens moves the key of every
    derivation over them - including the ones in player_rating, player_synergy,
    player_skill, create_teams, missing_maps and routes/votes, none of which the
    old hand-maintained clear list reached. (`routes/predict._faction_grid` is on
    MODEL and is deliberately *not* reached: new games must not evict it.) The
    registry additionally empties what it just superseded, so a stale generation
    does not sit in memory waiting to be evicted.

    Both tokens are bumped together because the operations that call this - a
    scrape, a register, a reparse, an override - land matches and fetch the maps
    they were played on in the same pass.
    """
    invalidate(CORPUS, MAPS)
    _ensure_warm_thread()
    _warm_event.set()
