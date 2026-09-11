"""Generals (faction) stats endpoints."""

import structlog

from fastapi import APIRouter, Depends

from .. import general_stats
from ..api_types import GeneralMatchups, GeneralStats
from ..db_utils import ReplayManager
from ..dependencies import cache_short, get_replay_manager
from ..queries import CompetitiveGames

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["generals"])


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


@router.get("/api/generalstats/matchups", dependencies=[Depends(cache_short)])
def get_general_matchups(game_list: CompetitiveGames) -> GeneralMatchups:
    """Actual win/loss for every pair of generals that has faced off.

    Same `gameFormat`-filtered corpus as `/api/generalstats`, so picking 1v1
    up there narrows this to genuine one-on-one results; "All" pools every
    team size together (see `general_stats.get_general_matchups` for how a
    team game turns into pairwise samples).
    """
    logger.info("getting general matchups")
    return general_stats.get_general_matchups(game_list)
