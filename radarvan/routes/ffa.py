"""Free-for-all (FFA) stats endpoints."""

import structlog

from fastapi import APIRouter, Depends

from .. import ffa_stats
from ..api_types import FFAStats
from ..cache import sorted_deduped_matches
from ..db_utils import ReplayManager
from ..dependencies import cache_short, get_replay_manager

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/api/ffastats", dependencies=[Depends(cache_short)])
def get_ffa_stats(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> FFAStats:
    """Stats scoped to human free-for-all games (player wins, general win rates, …)."""
    all_games = sorted_deduped_matches(replay_manager)
    return ffa_stats.get_ffa_stats(list(all_games.values()))
