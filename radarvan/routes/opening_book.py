"""Opening book endpoint: early build-order archetypes per general."""

import structlog

from fastapi import APIRouter, Depends

from .. import opening_book
from ..api_types import OpeningBook
from ..db_utils import ReplayManager
from ..dependencies import cache_short, get_replay_manager

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["opening_book"])


@router.get("/api/opening_book/", dependencies=[Depends(cache_short)])
def get_opening_book(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> OpeningBook:
    """Serve the opening book from the DB, computed by the nightly/manual
    superlatives recompute (see routes/superlatives._do_recompute)."""
    return opening_book.opening_book_from_computed(replay_manager.get_computed_stats())
