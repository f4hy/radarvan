"""Team stats endpoints."""

from fastapi import APIRouter, Depends

from .. import team_stats as team_stats_module
from ..api_types import TeamStatsResponse
from ..dependencies import cache_short
from ..queries import UnfilteredCompetitiveGames

router = APIRouter(tags=["teams"])


@router.get("/api/team_stats/", dependencies=[Depends(cache_short)])
def get_team_stats(games: UnfilteredCompetitiveGames) -> TeamStatsResponse:
    """Get win/loss records grouped by team composition, for teams with >5 games."""
    return team_stats_module.get_team_stats(games)
