import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from functools import cache
from typing import Union
from cachetools import TTLCache, cached
from cachetools.keys import hashkey
import match_details
import matches
import player_stats
from api_types import (
    General,
    MatchDetails,
    Matches,
    MatchInfo,
    Player,
    PlayerStats,
    SpentOverTime,
    Team,
)
import schedule
from cncstats_types import EnhancedReplay
from db_utils import DatabaseManager, MatchRepository, ReplayManager, StatsRepository
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import replay_files
import os

logger = logging.getLogger(__name__)

conn_str = os.environ["DATABASE_URL"]
db_manager = DatabaseManager(conn_str)


def get_db_session() -> Session:
    """
    Dependency that provides a database session.
    Automatically handles commit/rollback and cleanup.
    """
    session = db_manager.SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_replay_manager(session: Session = Depends(get_db_session)) -> ReplayManager:
    """Dependency that provides a MatchRepository instance."""
    return ReplayManager(session)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("hello")
    logging.basicConfig(level=logging.INFO)
    replay_files.test_connection()
    logger.info("connection tested")
    # sorted_deduped_matches()
    # logger.info("primed replays")
    replay_manager = get_replay_manager(get_db_session())
    scheduler = schedule.get_scheduler(replay_manager)
    scheduler.start()
    yield
    scheduler.shutdown()
    logger.info("goodbye!")


app = FastAPI(
    title="radarvan",
    description="Stats for generals",
    version="0.1.0",
    lifespan=lifespan,
)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)


# @app.get("/api/reparse")
# def reparse() -> None:
#     """Reparse the replays."""
#     manual.parse_replay.cache_clear()
#     for replay in manual.REPLAYS:
#         logger.info(f"Reparsing {replay=}")
#         manual.parse_replay(replay, reparse=True)
def dont_cache_manager(replay_manager: ReplayManager) -> str:
    return "single_key"


@cached(cache=TTLCache(5, ttl=1_200), key=dont_cache_manager)
def sorted_deduped_matches(replay_manager: ReplayManager) -> dict[int, MatchInfo]:
    replays = replay_files.get_all_replays(replay_manager)
    match_infos = (matches.match_from_replay(replay) for replay in replays)
    deduped = {i.id: i for i in match_infos if i}
    logger.info(f"Got {len(deduped)} parsed replays")
    sorted_matches = dict(
        sorted(deduped.items(), key=lambda item: item[1].timestamp, reverse=True)
    )
    return sorted_matches


@app.get("/api/replays/")
def list_replays(
    replay_manager: ReplayManager = Depends(get_replay_manager),
):
    listed = replay_manager.list_jsons()
    logger.info(f"Found {len(listed)=}")
    return listed


@app.get("/api/dates/")
def get_dates(
    replay_manager: ReplayManager = Depends(get_replay_manager),
):
    listed = replay_manager.list_dates_with_games()
    logger.info(f"Found {len(listed)=}")
    return listed


@app.get("/api/matches/{match_count}")
def get_matches(
    match_count: int,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> Matches:
    """Get listing of matches, up to a return count limit for paging."""
    replays = sorted_deduped_matches(replay_manager)
    return Matches(matches=replays.values())


def empty_match_details(match_id: int) -> MatchDetails:
    return MatchDetails(
        match_id=match_id,
        costs=[],
        apms=[],
        upgrade_events={},
        spent=SpentOverTime(
            buildings=[],
            units=[],
            upgrades=[],
            total=[],
        ),
        money_values={},
        player_summary=[],
    )


@app.get("/api/details/{match_id}")
def get_match_details(
    match_id: int,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> MatchDetails:
    """Get details about a particular match"""
    replays = sorted_deduped_matches(replay_manager)
    replay = replays.get(match_id)
    if not replay:
        return empty_match_details(match_id)
    replay = replay_files.parse_replay(replay.filename, replay_manager)
    details = match_details.match_details_from_replay(replay)
    return details


@app.get("/api/playerstats")
def get_player_stats(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> PlayerStats:
    """Get player stats."""
    games = sorted_deduped_matches(replay_manager)
    return player_stats.get_player_stats(games.values())


app.mount("/", StaticFiles(directory="build", html=True), name="build")
