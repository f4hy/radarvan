"""Draft randomization endpoint."""

from cachetools import TTLCache

from fastapi import APIRouter, Depends, HTTPException

from .. import draft as draft_module
from ..api_types import DraftPlayerRequest, DraftRequest, DraftResult
from ..db_utils import ReplayManager
from ..dependencies import get_replay_manager

router = APIRouter()


# Manual dict-style TTLCache (not @cached) because replay_manager is a FastAPI
# Depends parameter that can't pass through a decorator.
_draft_cache: TTLCache[str, DraftResult] = TTLCache(maxsize=100, ttl=1800)


def _draft_cache_key(map_name: str, players: list[DraftPlayerRequest]) -> str:
    return f"{map_name}:{tuple(sorted((p.name, p.team) for p in players))}"


@router.post("/api/draft/randomize")
def randomize_draft(
    request: DraftRequest,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> DraftResult:
    key = _draft_cache_key(request.map_name, request.players)
    if key in _draft_cache:
        return _draft_cache[key]
    map_data = replay_manager.get_map_data(request.map_name)
    if map_data is None:
        raise HTTPException(
            status_code=404, detail=f"No map data for '{request.map_name}'"
        )
    assignments, randomized_at = draft_module.compute_draft(
        request.players, map_data.player_starts
    )
    result = DraftResult(assignments=assignments, randomized_at=randomized_at)
    _draft_cache[key] = result
    return result
