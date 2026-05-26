"""Team stats endpoints."""

from fastapi import APIRouter, Depends

from .. import team_stats as team_stats_module
from ..api_types import TeamStatsResponse
from ..cache import competitive_matches
from ..db_utils import ReplayManager
from ..dependencies import cache_short, get_replay_manager

router = APIRouter()


@router.get("/api/team_stats/", dependencies=[Depends(cache_short)])
def get_team_stats(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> TeamStatsResponse:
    """Get win/loss records grouped by team composition, for teams with >5 games."""
    games = competitive_matches(replay_manager)
    return team_stats_module.get_team_stats(list(games.values()))
