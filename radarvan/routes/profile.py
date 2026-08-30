"""Per-player profile endpoints.

GET assembles the cheap live parts (W/L, generals, maps, people, tempo) from
the in-process competitive-match cache on every request, and attaches the
persisted deep stats (favorites, aversions, percentiles) computed by the
batch job in radarvan.player_profile. The deep stats are never computed
in-request - a full pass loads thousands of MatchDetails.
"""

import asyncio

import structlog

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from .. import player_profile, player_stats, player_synergy
from ..api_types import PlayerName, PlayerProfile
from ..cache import competitive_matches, sorted_deduped_matches
from ..db_utils import ReplayManager
from ..dependencies import OPS_ADMIN, cache_short, db_manager, get_replay_manager
from ..notify import notify_async

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["profile"])

# Operational routes the admin control panel drives. Cookie-authenticated, so
# included in main.py without the API-key dependency; every route here carries
# `dependencies=OPS_ADMIN`.
session_router = APIRouter(tags=["profile"])


_recompute_lock = asyncio.Lock()


@router.get("/api/player_profile/eligible_players", dependencies=[Depends(cache_short)])
def get_eligible_players(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> list[str]:
    """Players with a full profile: enough games for favorites/badges to mean
    anything. Populates the profile page's player picker."""
    return replay_manager.list_profiled_players(player_profile.PROFILE_VERSION)


@router.get("/api/player_profile/", dependencies=[Depends(cache_short)])
def get_player_profile(
    player: PlayerName,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> PlayerProfile:
    """Full profile for one player.

    ``computed`` is None until the batch recompute has run at the current
    PROFILE_VERSION (nightly, or via POST /api/player_profile/recompute).
    """
    # Same game set as the Player Stats page so the record and per-general
    # numbers on both pages agree. Synergy keeps the competitive set - that's
    # the population its (cached) model is fit on for every other endpoint.
    games = [
        g
        for g in sorted_deduped_matches(replay_manager).values()
        if player_stats.stats_game_filter(g)
    ]
    synergy_pairs = player_synergy.compute_player_synergy(
        list(competitive_matches(replay_manager).values())
    )
    profile = player_profile.compute_live_profile(games, player, synergy_pairs)
    computed = replay_manager.get_player_profile(player, player_profile.PROFILE_VERSION)
    return profile.model_copy(update={"computed": computed})


async def _do_recompute(replay_manager: ReplayManager) -> int:
    games = list(competitive_matches(replay_manager).values())
    data = await player_profile.load_many_profile_data(games, db_manager)
    logger.info("loaded profile data", count=len(data))
    profiles = await asyncio.to_thread(player_profile.compute_all_profiles, data)
    replay_manager.save_player_profiles(profiles, player_profile.PROFILE_VERSION)
    logger.info("saved player profiles", count=len(profiles))
    return len(profiles)


async def _do_recompute_bg() -> None:
    async with _recompute_lock:
        with db_manager.SessionLocal() as session:
            rm = ReplayManager(session)
            count = await _do_recompute(rm)
            session.commit()
    await notify_async(f"Recomputed {count} player profiles")


@session_router.post("/api/player_profile/recompute", dependencies=OPS_ADMIN)
async def recompute_player_profiles(
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    """Trigger a profile batch recompute in the background and return immediately."""
    if _recompute_lock.locked():
        raise HTTPException(status_code=409, detail="Recompute already in progress")
    background_tasks.add_task(_do_recompute_bg)
    return {"status": "started"}
