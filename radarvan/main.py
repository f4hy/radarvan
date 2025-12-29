import logging
import os
from contextlib import asynccontextmanager
from collections.abc import Generator
from fastapi import FastAPI, BackgroundTasks
import exception_handling

import middleware
import match_details
import matches
import player_stats
import general_stats
import replay_files
import schedule
import tournament
from api_types import (
    MatchDetails,
    Team,
    Matches,
    MatchInfo,
    PlayerStats,
    GeneralStats,
    SpentOverTime,
    WinnerOverride,
    GameRecord,
    TournamentResult,
)
from cachetools import TTLCache, cached
from db_utils import DatabaseManager, ReplayManager
from fastapi import Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

conn_str = os.environ["DATABASE_URL"]
db_manager = DatabaseManager(conn_str)


def get_db_session() -> Generator[Session]:
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
    return ReplayManager(session, notify=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("hello")
    logging.basicConfig(level=logging.INFO)
    replay_files.test_connection()
    logger.info("connection tested")
    # sorted_deduped_matches()
    # logger.info("primed replays")
    with db_manager.SessionLocal() as session:
        replay_manager = get_replay_manager(session)
        scheduler = schedule.get_scheduler(replay_manager)
        if os.getenv("DEV") is None:
            scheduler.start()
        yield
        if os.getenv("DEV") is None:
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
app.add_middleware(middleware.RequestTimingMiddleware)


# @app.get("/api/reparse")
# def reparse() -> None:
#     """Reparse the replays."""
#     manual.parse_replay.cache_clear()
#     for replay in manual.REPLAYS:
#         logger.info(f"Reparsing {replay=}")
#         manual.parse_replay(replay, reparse=True)
def dont_cache_manager(replay_manager: ReplayManager) -> str:
    return "single_key"


@cached(cache=TTLCache(5, ttl=30), key=dont_cache_manager)
def sorted_deduped_matches(replay_manager: ReplayManager) -> dict[int, MatchInfo]:
    # replays = replay_files.get_all_replays(replay_manager)
    # match_infos = (matches.match_from_replay(replay) for replay in replays)
    match_infos = matches.get_all_matches2(replay_manager)
    deduped = {i.id: i for i in match_infos if i}
    logger.info(f"Got {len(deduped)} parsed replays")
    sorted_matches = dict(
        sorted(deduped.items(), key=lambda item: item[1].timestamp, reverse=True)
    )
    return sorted_matches


@app.get("/api/files/")
def list_files(
    replay_manager: ReplayManager = Depends(get_replay_manager),
):
    listed = list(replay_manager.list_files())
    logger.info(f"Found {len(listed)=}")
    return listed


@app.get("/api/replays/")
def list_replays(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> list[GameRecord]:
    listed = replay_manager.list_jsons()
    logger.info(f"Found {len(listed)=}")
    converted = [GameRecord.model_validate(l, from_attributes=True) for l in listed]
    return converted


@app.get("/api/dates/")
def get_dates(
    replay_manager: ReplayManager = Depends(get_replay_manager),
):
    listed = replay_manager.list_dates_with_games()
    logger.info(f"Found {len(listed)=}")
    return listed


@app.post("/api/scrape/{days}")
def scrape(
    background_tasks: BackgroundTasks,
    days: int = 1,
    replay_manager: ReplayManager = Depends(get_replay_manager),
):
    background_tasks.add_task(schedule.update_games, replay_manager, days=days)
    return {"scheduled": "ok"}


@app.get("/api/matches/{match_count}")
def get_matches(
    match_count: int,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> Matches:
    """Get listing of matches, up to a return count limit for paging."""
    replays = sorted_deduped_matches(replay_manager)
    return Matches(matches=replays.values())


@app.get("/api/tournament_results/")
def get_tournament_results(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> list[TournamentResult]:
    """Get listing of matches, up to a return count limit for paging."""
    replays = sorted_deduped_matches(replay_manager)
    tournament_games = tournament.tournament_games(replays.values())
    # logger.info(f"games {tournament_games}")
    results = tournament.create_tournament_results(tournament_games)
    # logger.info(f"results {results}")
    return results


@app.get("/api/match/{match_id}")
def get_matches(
    match_id: int,
    replay_manager: ReplayManager = Depends(get_replay_manager),
):
    """Get listing of matches, up to a return count limit for paging."""
    m = sorted_deduped_matches(replay_manager).get(match_id)
    return m


@app.post("/api/reprase/{match_id}")
def reparse(
    match_id: int,
    replay_manager: ReplayManager = Depends(get_replay_manager),
):
    """Rerun the replay parser on this match."""
    return matches.reparse_replay(match_id, replay_manager)


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
    replay = replay_manager.get_replay_json_by_match_id(match_id)
    if not replay:
        return empty_match_details(match_id)
    replay = replay_files.parse_replay(replay.replay_file_url, replay_manager)
    details = match_details.match_details_from_replay(replay)
    return details


@app.get("/api/playerstats")
def get_player_stats(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> PlayerStats:
    """Get player stats."""
    games = sorted_deduped_matches(replay_manager)
    logger.info("getting player stats")
    return player_stats.get_player_stats(games.values())


@app.get("/api/generalstats")
def get_generals_stats(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> GeneralStats:
    """Get generals stats."""
    games = sorted_deduped_matches(replay_manager)
    logger.info("getting player stats")
    return general_stats.get_player_stats(games.values())


@app.get("/api/overrides")
def get_overrides(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> list[WinnerOverride]:
    """Get winner overrides."""
    overrides = replay_manager.get_overrides()
    return [
        WinnerOverride(
            match_id=o.match_id, winning_team_id=o.winning_team_id or Team.NONE
        )
        for o in overrides.values()
    ]


@app.post("/api/set_override/")
def set_overrides(
    match_id: int,
    winner: Team,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> WinnerOverride:
    """Set winner overrides."""
    saved = replay_manager.set_override(match_id, winner=winner or None)
    return WinnerOverride(
        match_id=saved.match_id, winning_team_id=saved.winning_team_id or Team.NONE
    )


app.mount("/", StaticFiles(directory="build", html=True), name="build")


exception_handling.setup_error_handling(app)
