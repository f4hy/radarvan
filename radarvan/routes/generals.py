"""Generals (faction) stats endpoints."""

import logging

from fastapi import APIRouter, Depends, Query

from .. import general_stats, matches
from ..api_types import GeneralStats
from ..cache import competitive_matches
from ..db_utils import ReplayManager
from ..dependencies import get_replay_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/generalstats")
def get_generals_stats(
    game_format: str | None = Query(
        None, description="Filter by game format: 1v1, 2v2, 3v3, 4v4"
    ),
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> GeneralStats:
    """Get generals stats."""
    games = competitive_matches(replay_manager)
    game_list = matches.filter_by_format(list(games.values()), game_format)
    logger.info("getting generals stats")
    return general_stats.get_generals_stats(game_list)
