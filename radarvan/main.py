from datetime import datetime, UTC
from cncstats_types import EnhancedReplay
from api_types import (
    Matches,
    MatchInfo,
    Player,
    General,
    Team,
    MatchDetails,
    SpentOverTime,
)
from functools import cache
from typing import Union
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import manual
import matches
import match_details
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("hello")
    logging.basicConfig(level=logging.INFO)
    manual.test_connection()
    logger.info("connection tested")
    manual.get_parsed_replays(manual.REPLAYS)
    logger.info("primed replays")
    yield
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


@app.get("/api/reparse")
def reparse() -> None:
    """Reparse the replays."""
    manual.parse_replay.cache_clear()
    for replay in manual.REPLAYS:
        logger.info(f"Reparsing {replay=}")
        manual.parse_replay(replay, reparse=True)


@cache
def sorted_deduped_matches() -> dict[int, EnhancedReplay]:
    replays = manual.get_parsed_replays(manual.REPLAYS)
    logger.info(f"Got {len(replays)} parsed replays")
    match_infos = [matches.match_from_replay(replay) for replay in replays]
    deduped = {i.id: i for i in match_infos if i}
    sorted_matches = dict(
        sorted(deduped.items(), key=lambda item: item[1].timestamp, reverse=True)
    )
    return sorted_matches


@app.get("/api/matches/{match_count}")
def get_matches(match_count: int) -> Matches:
    """Get listing of matches, up to a return count limit for paging."""
    replays = sorted_deduped_matches()
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


@cache
def replay_map() -> dict[int, EnhancedReplay]:
    replays = manual.get_parsed_replays(manual.REPLAYS)
    logger.info(f"Got {len(replays)} parsed replays")
    return {r.Header.Metadata.Seed: r for r in replays}


@app.get("/api/details/{match_id}")
def get_match_details(match_id: int) -> MatchDetails:
    """Get details about a particular match"""
    replays = replay_map()
    replay = replays.get(match_id)
    if not replay:
        return empty_match_details(match_id)
    details = match_details.match_details_from_replay(replay)
    return details


app.mount("/", StaticFiles(directory="build", html=True), name="build")
