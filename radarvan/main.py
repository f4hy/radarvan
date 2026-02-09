from enum import Enum
from pydantic import BaseModel
import asyncio
import traceback
from fastapi import FastAPI, Request, Query
from fastapi.responses import JSONResponse
import logging
import os
from contextlib import asynccontextmanager
from collections.abc import Generator
from fastapi import BackgroundTasks
from . import exception_handling

from . import player_ids
from . import middleware
from . import match_details
from . import matches
from . import player_stats
from . import general_stats
from . import replay_files
from . import schedule
from . import tournament
from . import player_rating
from . import create_teams
from radarvan.api_types import (
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
    ReplayFileSchema,
    ParsedReplayJsonSchema,
    TournamentReport,
    PlayerRatings,
)
from cachetools import TTLCache, cached
from .db_utils import DatabaseManager, ReplayManager
from fastapi import Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

conn_str = os.environ["DATABASE_URL"]
db_manager = DatabaseManager(conn_str)


def get_db_session() -> Generator[Session]:
    """Dependency that provides a database session.

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
    """Setup and shutdown of the webserver."""
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


@app.exception_handler(Exception)
async def my_exception_handler(request: Request, exc: Exception):
    tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__, limit=5)

    logger.info("".join(tb_lines))

    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error {type(exc)}"},
    )


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
    converted = [GameRecord.model_validate(ls, from_attributes=True) for ls in listed]
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
    sorted_deduped_matches.cache_clear()
    details_from_id.cache_clear()
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


def dont_cache_manager2(match_id: int, replay_manager: ReplayManager) -> str:
    return str(match_id)


@cached(cache=TTLCache(5, ttl=30), key=dont_cache_manager2)
def details_from_id(match_id: int, replay_manager: ReplayManager) -> MatchDetails:
    rep = replay_manager.get_replay_json_by_match_id(match_id)
    par = replay_files.parse_replay(rep.replay_file_url, replay_manager)
    return match_details.match_details_from_replay(par)


semaphore = asyncio.Semaphore(value=1)


async def save_report(
    name: str, replay_manager: ReplayManager, save: bool = True
) -> TournamentReport:
    async with semaphore:
        replays = sorted_deduped_matches(replay_manager)
        tournament_games = tournament.tournament_games(replays.values()).get(name, [])
        if save is False:
            tournament_games = tournament_games[:5]
        details = await asyncio.gather(
            *[
                asyncio.to_thread(details_from_id, g.id, replay_manager)
                for g in tournament_games
            ]
        )
        logger.info(f"finished details {len(details)}")
    results = tournament.tournament_report(name, tournament_games, details)
    if save:
        replay_manager.save_tournament_report(results)
    return results


@app.get("/api/tournament_report/{tournament_name}")
async def get_tournament_report(
    background_tasks: BackgroundTasks,
    tournament_name: str = "2025_2v2_tournament",
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> TournamentReport:
    """Get listing of matches, up to a return count limit for paging."""
    existing = replay_manager.get_tournament_report_by_name(tournament_name)
    if not existing:
        background_tasks.add_task(save_report, tournament_name, replay_manager)
        return TournamentReport(name="", stats=[])

    return existing


@app.post("/api/generate_tournament_report/{tournament_name}")
async def generate_tournament_report(
    background_tasks: BackgroundTasks,
    tournament_name: str = "2025_2v2_tournament",
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> str:
    background_tasks.add_task(save_report, tournament_name, replay_manager)
    return "OK"


@app.post("/api/test_tournament_report/{tournament_name}")
async def test_tournament_report(
    background_tasks: BackgroundTasks,
    tournament_name: str = "2025_2v2_tournament",
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> TournamentReport:
    report = await save_report(tournament_name, replay_manager, save=False)
    return report


@app.get("/api/match/{match_id}")
def get_match_by_id(
    match_id: int,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> MatchInfo:
    """Get listing of matches, up to a return count limit for paging."""
    m = sorted_deduped_matches(replay_manager).get(match_id)
    return m


@app.post("/api/reprase/{match_id}")
def reprase(
    match_id: int,
    replay_manager: ReplayManager = Depends(get_replay_manager),
):
    """Rerun the replay parser on this match."""
    return matches.reparse_replay(match_id, replay_manager)


@app.post("/api/reparse/{match_id}")
def reparse(
    match_id: int,
    replay_manager: ReplayManager = Depends(get_replay_manager),
):
    """Rerun the replay parser on this match."""
    return matches.reparse_replay(match_id, replay_manager)


@app.post("/api/register_replay_url")
def register_replay_url(
    url_of_replay: str,
    replay_manager: ReplayManager = Depends(get_replay_manager),
):
    """Rerun the replay parser on this match."""
    replay = replay_files.parse_replay(url_of_replay, replay_manager)
    matches.register_matches(replay_manager)
    return matches.reparse_replay(replay.replay_id(), replay_manager)


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


@app.get("/api/files_for_match", response_model_exclude_none=True)
def get_files_for_match_id(
    match_id: int,
    replay_manager: ReplayManager = Depends(get_replay_manager),
):
    """Get winner overrides."""
    files = replay_manager.all_files_for_id(match_id)
    resp = {
        "replay_files": [
            ReplayFileSchema.model_validate(r) for r in files.replay_files
        ],
        "parsed_files": [
            ParsedReplayJsonSchema.model_validate(p) for p in files.parsed_files
        ],
    }
    return resp


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


@app.post("/api/update_num_timestamps/")
def update_num_timestamps(
    max_to_update: int = 1000,
    replay_manager: ReplayManager = Depends(get_replay_manager),
):
    missing_timestamp_count = replay_manager.list_jsons_without_num_timestamps()
    updated = 0
    for missing in missing_timestamp_count:
        replay = replay_files.parse_replay(missing.replay_file_url, replay_manager)
        num_time_stamps = replay.Header.NumTimeStamps
        has_enhanced_stats = any(chunk.PlayerStats is not None for chunk in replay.Body)
        result = replay_manager.update_parsed_json(
            missing.json_s3_uri,
            num_time_stamps,
            has_player_stats=has_enhanced_stats,
        )
        logger.info(f"Updated {missing.match_id} success={result}")
        if result:
            updated += 1
        if updated >= max_to_update:
            break
    return {"updated": updated}


@app.get("/api/replays_without_playerstats/")
def replays_without_playerstats(
    max_to_return: int = 10,
    replay_manager: ReplayManager = Depends(get_replay_manager),
):
    missing_player_stats = replay_manager.list_jsons_without_player_stats(max_to_return)
    for row in missing_player_stats:
        row["presigned_url"] = replay_files.presigned_url(row["s3_path"])
        yield row


@app.get("/api/player_ratings/")
def get_player_ratings(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> list[PlayerRatings]:
    games = sorted_deduped_matches(replay_manager)

    ratings = player_rating.compute_player_ratings(list(games.values()))
    converted = [
        PlayerRatings(name=r.name, ordinal=r.ordinal(), mu=r.mu, sigma=r.sigma)
        for r in ratings
    ]
    return converted


PlayerEnum = Enum(
    "PlayerEnum", {v.upper(): v for v in player_ids.PLAYER_NAMES}, type=str
)


class SelectedPLayers(BaseModel):
    players: list[PlayerEnum] = []


@app.get("/api/balance_teams/")
def balance_teams(
    players: SelectedPLayers = Query(default=SelectedPLayers(players=[])),
    replay_manager: ReplayManager = Depends(get_replay_manager),
):
    if players is None:
        return {}
    if len(players.players) < 4:
        return {}

    games = sorted_deduped_matches(replay_manager)

    team_scores = create_teams.balance_teams(
        list(games.values()), player_list=players.players
    )
    logger.info(f"Team Scores {team_scores}")
    return {",".join(i): v for i, v in team_scores.items()}


@app.get("/api/partition_teams/{team_size}")
def partition_teams(
    team_size: int = 2,
    players: SelectedPLayers = Query(default=SelectedPLayers(players=[])),
    replay_manager: ReplayManager = Depends(get_replay_manager),
):
    games = list(sorted_deduped_matches(replay_manager).values())
    teams = create_teams.create_balanced_teams(
        games, player_list=players.players, team_size=team_size
    )

    return teams


app.mount("/", StaticFiles(directory="build", html=True), name="build")


exception_handling.setup_error_handling(app)
