"""Generals-power picks and usage endpoints."""

import structlog

from fastapi import APIRouter, Depends

from ..api_types import PlayerName, PowerStats
from ..db_utils import ReplayManager
from ..dependencies import cache_short, get_replay_manager
from ..queries import power_stats

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["powers"])


@router.get("/api/power_stats/", dependencies=[Depends(cache_short)])
def get_power_stats(
    player: PlayerName | None = None,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> PowerStats:
    """One player's generals-power habits, against the rest of the group.

    Takes a `ReplayManager` rather than a corpus dependency: the whole answer
    comes from `queries.power_stats`, which folds the corpus once per corpus
    version and keeps only counters. Declaring `CompetitiveGames` here would
    build the match list on every request for a handler that never looks at it,
    and would key the fold by game format - four full passes over
    `match_details_cache` instead of one.

    `player` is an `api_types.PlayerName`, so an in-game alias ("skp") is
    resolved to the canonical name at validation, matching the names the
    projection stores.
    """
    logger.info("getting power stats", player=player)
    return power_stats(replay_manager, player)
