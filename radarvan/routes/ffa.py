"""Free-for-all (FFA) stats endpoints."""

import structlog

from fastapi import APIRouter, Depends, Query

from .. import ffa_stats
from ..api_types import FFAStats
from ..dependencies import cache_short
from ..queries import AllGames

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/api/ffastats", dependencies=[Depends(cache_short)])
def get_ffa_stats(
    games: AllGames,
    include_cpu: bool = Query(
        False,
        description=(
            "Include free-for-alls containing AI players. The AI slots then "
            "count as full participants: they size the field, hold their own "
            "leaderboard rows, and can win the game."
        ),
    ),
) -> FFAStats:
    """Stats scoped to free-for-all games (player wins, general win rates, ...)."""
    return ffa_stats.get_ffa_stats(games, include_cpu=include_cpu)
