"""Free-for-all (FFA) stats endpoints."""

import structlog

from fastapi import APIRouter, Depends

from .. import ffa_stats
from ..api_types import FFAStats
from ..dependencies import cache_short
from ..queries import AllGames

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/api/ffastats", dependencies=[Depends(cache_short)])
def get_ffa_stats(games: AllGames) -> FFAStats:
    """Stats scoped to human free-for-all games (player wins, general win rates, ...)."""
    return ffa_stats.get_ffa_stats(games)
