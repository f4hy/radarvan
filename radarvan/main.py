from datetime import datetime, UTC
from api_types import (
    Matches,
    MatchInfo,
    Player,
    General,
    Team,
    MatchDetails,
    SpentOverTime,
)
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


@app.get("/api/matches/{match_count}")
def get_matches(match_count: int) -> Matches:
    """Get listing of matches, up to a return count limit for paging."""
    replays = manual.get_parsed_replays(manual.REPLAYS)
    # logger.info(f"{replays=}")
    match_infos = [matches.match_from_replay(replay) for replay in replays]
    not_nulls = [i for i in match_infos if i]
    logger.info(f"{match_infos=}")
    return Matches(matches=not_nulls)


@app.get("/api/details/{match_id}")
def get_match_details(match_id: int) -> MatchDetails:
    """Get details about a particular match"""
    replays = manual.get_parsed_replays(manual.REPLAYS)
    for replay in replays:
        if replay.Header.TimeStampBegin == match_id:
            details = match_details.match_details_from_replay(replay)
            return details
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
        money_values=[],
    )


app.mount("/", StaticFiles(directory="build", html=True), name="build")
