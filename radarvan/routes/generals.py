"""Generals (faction) stats endpoints."""

import structlog

from fastapi import APIRouter, Depends

from .. import general_stats
from ..api_types import GeneralStats
from ..db_utils import ReplayManager
from ..dependencies import cache_short, get_replay_manager
from ..queries import CompetitiveGames

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/api/generalstats", dependencies=[Depends(cache_short)])
def get_generals_stats(
    game_list: CompetitiveGames,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> GeneralStats:
    """Get generals stats.

    Still takes a `ReplayManager` alongside the corpus: the value-destroyed
    totals are read from the `Statistic` rows the nightly superlatives recompute
    persists, which is a stored projection rather than something derived from
    the match list.
    """
    logger.info("getting generals stats")
    value_stats = general_stats.value_stats_from_computed(
        replay_manager.get_computed_stats()
    )
    return general_stats.get_generals_stats(game_list, value_stats)
