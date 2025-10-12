from datetime import datetime, UTC
from api_types import Matches, MatchInfo, Player, General, Team
from typing import Union
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import manual
import matches
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


app = FastAPI(title="radarvan", description="Stats for generals", version="0.1.0", lifespan=lifespan)

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
    replays = manual.get_parsed_replays(manual.REPLAYS)
    # logger.info(f"{replays=}")
    match_infos = [matches.match_from_replay(replay) for replay in replays]
    logger.info(f"{match_infos=}")
    return Matches(matches=match_infos)


app.mount("/", StaticFiles(directory="build", html=True), name="build")
