"""Draft randomization endpoint."""

import threading

from cachetools import TTLCache

from fastapi import APIRouter, Depends, HTTPException

from .. import draft as draft_module
from ..api_types import DraftPlayerRequest, DraftRequest, DraftResult
from ..db_utils import ReplayManager
from ..dependencies import get_replay_manager

router = APIRouter(tags=["draft"])


# Deliberately NOT a @derived derivation, and the reason is not the mechanism -
# the registry could bind `replay_manager` by name perfectly well. A draft is a
# *random* result held steady for a while, not a value derived from the corpus:
# keying it on a version token would re-randomize everyone's teams the moment a
# game landed, mid-game-night. A wall-clock TTL is the honest expression of
# "keep this stable for 30 minutes", so this stays a manual TTLCache and is
# allow-listed in tests/test_derived_registry.py. Dropping @cached does not drop
# the lock: this is a sync endpoint, so it runs in uvicorn's threadpool and
# concurrent access would corrupt the cache's LRU/TTL bookkeeping.
_draft_cache: TTLCache[str, DraftResult] = TTLCache(maxsize=100, ttl=1800)
_draft_cache_lock = threading.Lock()


def _draft_cache_key(map_name: str, players: list[DraftPlayerRequest]) -> str:
    return f"{map_name}:{tuple(sorted((p.name, p.team) for p in players))}"


@router.post("/api/draft/randomize")
def randomize_draft(
    request: DraftRequest,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> DraftResult:
    key = _draft_cache_key(request.map_name, request.players)
    # One lookup, not `in` + `[]`: an entry can expire between the two, which
    # would raise KeyError on a cache that just reported a hit.
    with _draft_cache_lock:
        cached = _draft_cache.get(key)
    if cached is not None:
        return cached
    map_data = replay_manager.get_map_data(request.map_name)
    if map_data is None:
        raise HTTPException(
            status_code=404, detail=f"No map data for '{request.map_name}'"
        )
    assignments, randomized_at = draft_module.compute_draft(
        request.players, map_data.player_starts
    )
    result = DraftResult(assignments=assignments, randomized_at=randomized_at)
    with _draft_cache_lock:
        _draft_cache[key] = result
    return result
