from collections import Counter
from datetime import date
from enum import Enum
from pydantic import BaseModel
import asyncio
import traceback
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import JSONResponse
import logging
import os
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator, Generator
from typing import Any
from fastapi import BackgroundTasks
from . import exception_handling

from . import game_composition
from . import player_ids
from . import middleware
from . import match_details
from . import matches
from . import player_stats
from . import general_stats
from . import map_stats as map_stats_module
from . import team_stats as team_stats_module
from . import replay_files
from . import schedule
from . import tournament
from . import player_rating
from . import superlatives
from . import create_teams
from radarvan.api_types import (
    MatchDetails,
    MapStatsResponse,
    PlayerGameCount,
    TeamStatsResponse,
    ShortPlayerRating,
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
    PlayerRatingData,
)
from cachetools import TTLCache, cached
from .db_utils import DatabaseManager, MatchDebugData, ReplayManager
from .game_composition import GameComposition
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
    """Dependency that provides a ReplayManager instance."""
    return ReplayManager(session, notify=True)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
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
async def my_exception_handler(request: Request, exc: Exception) -> JSONResponse:
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
    match_infos = matches.get_match_infos(replay_manager)
    deduped = {i.id: i for i in match_infos if i}
    logger.info(f"Got {len(deduped)} parsed replays")
    sorted_matches = dict(
        sorted(deduped.items(), key=lambda item: item[1].timestamp, reverse=True)
    )
    return sorted_matches


@cached(cache=TTLCache(5, ttl=30), key=dont_cache_manager)
def competitive_matches(replay_manager: ReplayManager) -> dict[int, MatchInfo]:
    all_matches = sorted_deduped_matches(replay_manager)
    filtered = {
        m.id: m
        for m in all_matches.values()
        if game_composition.competitive_game_filter(comp=m.composition)
    }
    return filtered


@app.get("/api/files/pending_unprocessed")
def list_pending_unprocessed(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> list[ReplayFileSchema]:
    """Return replay files that are pending but have no parsed JSON."""
    files = replay_manager.list_pending_without_parsed()
    return [ReplayFileSchema.model_validate(f) for f in files]


@app.get("/api/files/")
def list_files(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> list[ReplayFileSchema]:
    listed = list(replay_manager.list_files())
    logger.info(f"Found {len(listed)=}")
    return [ReplayFileSchema.model_validate(f) for f in listed]


class ReplayFilters(BaseModel):
    match_id: int | None = None
    game_date: date | None = None


@app.get("/api/replays/")
def list_replays(
    filters: ReplayFilters = Query(
        defulat=ReplayFilters(match_id=None, game_date=date.today())
    ),
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> list[GameRecord]:
    listed = replay_manager.list_jsons()
    if filters.match_id:
        listed = [x for x in listed if x.match_id == filters.match_id]
    if filters.game_date:
        listed = [x for x in listed if x.game_date == filters.game_date]
    logger.info(f"Found {len(listed)=}")
    converted = [GameRecord.model_validate(ls, from_attributes=True) for ls in listed]
    return converted


@app.get("/api/dates/")
def get_dates(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> dict[date, int]:
    replays = sorted_deduped_matches(replay_manager)
    dates = Counter(r.date for r in replays.values())
    return dict(sorted(dates.items(), reverse=True))


@app.post("/api/scrape/{days}")
def scrape(
    background_tasks: BackgroundTasks,
    days: int = 1,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> dict[str, str]:
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


def _row_to_dict(obj: Any) -> dict[str, Any]:
    """Convert a SQLAlchemy mapped row to a plain dict using its table columns."""
    return {col.name: getattr(obj, col.name) for col in obj.__table__.columns}


def _debug_data_to_dict(data: MatchDebugData) -> dict[str, Any]:
    return {
        "matches": _row_to_dict(data.matches) if data.matches else None,
        "match_players": [_row_to_dict(p) for p in data.match_players],
        "match_compostion": _row_to_dict(data.match_compostion)
        if data.match_compostion
        else None,
        "winner_overrides": _row_to_dict(data.winner_overrides)
        if data.winner_overrides
        else None,
        "parsed_replay_json": [_row_to_dict(p) for p in data.parsed_replay_json],
        "replay_files": [_row_to_dict(f) for f in data.replay_files],
    }


@app.get("/api/debug/match/{match_id}")
def debug_match(
    match_id: int,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> dict[str, Any]:
    """Return every row related to a match_id across all tables, keyed by table name."""
    debug_data = _debug_data_to_dict(replay_manager.get_all_data_for_match(match_id))
    rep = replay_manager.get_replay_json_by_match_id(match_id)
    if rep:
        par = replay_files.parse_replay(rep.replay_file_url, replay_manager)
        debug_data["header"] = par.Header.model_dump_json()
    return debug_data


@app.get("/api/debug/json_url/{match_id}")
def get_match_json_url(
    match_id: int,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> dict[str, str]:
    """Return a presigned S3 URL for the parsed JSON of a match."""
    match = replay_manager.get_match(match_id)
    if match is None:
        raise HTTPException(status_code=404, detail=f"Match {match_id} not found")
    return {"url": replay_files.presigned_url(match.json_s3_uri)}


@app.post("/api/matches/{match_id}/composition")
def compute_match_composition(
    match_id: int,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> GameComposition:
    """Compute and persist the composition (teams, humans vs CPUs, category) for a match."""
    result = replay_manager.compute_and_save_composition(match_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Match {match_id} not found")
    return result


@app.post("/api/backfill/composition")
def backfill_match_composition(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> int:
    """Backfill and persist the composition for a match."""
    count = 0
    for match_id in replay_manager.list_matches_without_composition():
        count += 1
        result = replay_manager.compute_and_save_composition(match_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Match {match_id} not found")
    return count


@app.get("/api/matches/by_date/{date}")
def get_matches_by_date(
    date: date,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> Matches:
    """Get all matches for a specific date."""
    replays = sorted_deduped_matches(replay_manager)
    return Matches(matches=[r for r in replays.values() if r.date == date])


@app.get("/api/tournament_results/")
def get_tournament_results(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> list[TournamentResult]:
    """Get results for all tournaments."""
    replays = sorted_deduped_matches(replay_manager)
    tournament_games = tournament.tournament_games(list(replays.values()))
    # logger.info(f"games {tournament_games}")
    results = tournament.create_tournament_results(tournament_games)
    # logger.info(f"results {results}")
    return results


def dont_cache_manager2(match_id: int, replay_manager: ReplayManager) -> str:
    return str(match_id)


@cached(cache=TTLCache(5, ttl=30), key=dont_cache_manager2)
def details_from_id(
    match_id: int, replay_manager: ReplayManager
) -> MatchDetails | None:
    rep = replay_manager.get_replay_json_by_match_id(match_id)
    if rep is None:
        return None
    par = replay_files.parse_replay(rep.replay_file_url, replay_manager)
    return match_details.match_details_from_replay(par)


semaphore = asyncio.Semaphore(value=1)


async def save_report(
    name: str, replay_manager: ReplayManager, save: bool = True
) -> TournamentReport:
    async with semaphore:
        replays = sorted_deduped_matches(replay_manager)
        tournament_games = tournament.tournament_games(list(replays.values())).get(
            name, []
        )
        if save is False:
            tournament_games = tournament_games[:5]
        details = await asyncio.gather(
            *[
                asyncio.to_thread(details_from_id, g.id, replay_manager)
                for g in tournament_games
            ]
        )
        logger.info(f"finished details {len(details)}")
    valid_details = [d for d in details if d is not None]
    results = tournament.tournament_report(name, tournament_games, valid_details)
    if save:
        replay_manager.save_tournament_report(results)
    return results


@app.get("/api/tournament_report/{tournament_name}")
async def get_tournament_report(
    background_tasks: BackgroundTasks,
    tournament_name: str = "2025_2v2_tournament",
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> TournamentReport:
    """Get report for a specific tournament."""
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


@app.get("/api/team_games_without_winner/")
def get_team_games_without_winner(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> list[dict[str, Any]]:
    """Return match IDs and dates for team games with no winner (winning_team=0)."""
    all_matches = sorted_deduped_matches(replay_manager)
    games_with_no_winner = [
        {"match_id": m.id, "date": m.date}
        for m in all_matches.values()
        if m.composition is not None
        and m.composition.is_team_game
        and m.composition.num_teams == 2
        and m.composition.num_humans > 2
        and m.winning_team == Team.NONE
        and (
            m.incomplete == ""
            or m.incomplete is None
            or "no team" in m.incomplete.lower()
        )
    ]
    # if os.getenv("DEV"):
    # for g in games_with_no_winner:
    #     mid = g["match_id"]
    #     _replay = matches.reparse_replay(mid, replay_manager)
    return games_with_no_winner


@app.get("/api/match/{match_id}")
def get_match_by_id(
    match_id: int,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> MatchInfo | None:
    """Get a single match by its ID."""
    return sorted_deduped_matches(replay_manager).get(match_id)


@app.post("/api/reprase/{match_id}")
def reprase(
    match_id: int,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> MatchInfo | None:
    """Rerun the replay parser on this match."""
    replay = matches.reparse_replay(match_id, replay_manager)
    replay_manager.compute_and_save_composition(match_id)
    return replay


@app.post("/api/reparse/{match_id}")
def reparse(
    match_id: int,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> MatchInfo | None:
    """Rerun the replay parser on this match."""
    replay = matches.reparse_replay(match_id, replay_manager)
    replay_manager.compute_and_save_composition(match_id)
    return replay


@app.post("/api/register_replay_url")
def register_replay_url(
    url_of_replay: str,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> MatchInfo | None:
    """Register and parse a new replay from a URL."""
    existing = replay_manager.get_replay_file(url_of_replay)
    if existing:
        if existing.parsed_replay_json:
            logger.info("Already parsed, skipping")
            return None
    replay = replay_files.parse_replay(url_of_replay, replay_manager)
    return matches.reparse_replay(replay.replay_id(), replay_manager)


@app.get("/api/replay")
def get_replay_by_url(
    url_of_replay: str,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> dict[str, str]:
    replay = replay_manager.get_replay_file(url_of_replay)
    if not replay:
        return {}
    return {"original_url": replay.original_url, "status": replay.status.value}


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
        money_collected_values={},
        stats_data={},
        player_summary=[],
    )


@app.get("/api/details/{match_id}")
def get_match_details(
    match_id: int,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> MatchDetails:
    """Get details about a particular match"""
    replay_json = replay_manager.get_replay_json_by_match_id(match_id)
    if not replay_json:
        return empty_match_details(match_id)
    replay = replay_files.parse_replay(replay_json.replay_file_url, replay_manager)
    details = match_details.match_details_from_replay(replay)
    return details or empty_match_details(match_id)


@app.get("/api/playerstats")
def get_player_stats(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> PlayerStats:
    """Get player stats."""
    games = competitive_matches(replay_manager)
    logger.info("getting player stats")
    return player_stats.get_player_stats(list(games.values()))


@app.get("/api/superlatives")
def get_superlatives(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> superlatives.Superlatives:
    """Serve superlatives from the DB if available, otherwise compute on the fly."""
    games = competitive_matches(replay_manager)
    saved_stats = replay_manager.get_computed_stats()
    if saved_stats:
        return superlatives.Superlatives(match_count=len(games), stats=saved_stats)
    logger.info("no saved superlatives")
    return superlatives.Superlatives(match_count=len(games), stats=[])


@app.post("/api/superlatives/recompute")
def recompute_superlatives(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> superlatives.Superlatives:
    """Recompute superlatives, persist to DB, and return the result."""
    games = competitive_matches(replay_manager)
    result = superlatives.get_superlatives(list(games.values()))
    replay_manager.clear_computed_stats()
    replay_manager.save_computed_stats(result.stats)
    logger.info(f"saved {len(result.stats)} computed statistics")
    return result


@app.get("/api/generalstats")
def get_generals_stats(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> GeneralStats:
    """Get generals stats."""
    games = competitive_matches(replay_manager)
    logger.info("getting generals stats")
    return general_stats.get_generals_stats(list(games.values()))


@app.get("/api/team_stats/")
def get_team_stats(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> TeamStatsResponse:
    """Get win/loss records grouped by team composition, for teams with >5 games."""
    games = competitive_matches(replay_manager)
    return team_stats_module.get_team_stats(list(games.values()))


@app.get("/api/map_stats/")
def get_map_stats(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> MapStatsResponse:
    """Get player and general win rates grouped by map."""
    games = competitive_matches(replay_manager)
    return map_stats_module.get_map_stats(list(games.values()))


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
) -> dict[str, list[ReplayFileSchema] | list[ParsedReplayJsonSchema]]:
    """Get all replay and parsed files for a match."""
    files = replay_manager.all_files_for_id(match_id)
    return {
        "replay_files": [
            ReplayFileSchema.model_validate(r) for r in files.replay_files
        ],
        "parsed_files": [
            ParsedReplayJsonSchema.model_validate(p) for p in files.parsed_files
        ],
    }


@app.post("/api/set_override/")
def set_override(
    match_id: int,
    winner: Team,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> WinnerOverride:
    """Set a winner override for a match."""
    saved = replay_manager.set_override(
        match_id, winner=winner.value if winner else None
    )
    return WinnerOverride(
        match_id=saved.match_id, winning_team_id=saved.winning_team_id or Team.NONE
    )


@app.delete("/api/match/{match_id}")
def reset_match(
    match_id: int,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> dict[str, int]:
    """Delete all parsed data for a match and reset its ReplayFile(s) to pending."""
    counts = replay_manager.reset_match(match_id)
    if not any(counts.values()):
        raise HTTPException(
            status_code=404, detail=f"No data found for match {match_id}"
        )
    return counts


@app.delete("/api/override/{match_id}")
def delete_override(
    match_id: int,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> dict[str, str]:
    """Delete a winner override for a match."""
    deleted = replay_manager.delete_override(match_id)
    if not deleted:
        raise HTTPException(
            status_code=404, detail=f"No override found for match {match_id}"
        )
    return {"status": "deleted", "match_id": str(match_id)}


@app.post("/api/update_num_timestamps/")
def update_num_timestamps(
    max_to_update: int = 1000,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> dict[str, int]:
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


@app.post("/api/update_matches_missing_data/")
def update_matches_missing_data(
    max_to_update: int = 1,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> dict[str, int]:
    missing_game_version = replay_manager.list_matches_without_game_version(
        max_to_update
    )
    logger.info(f"{len(missing_game_version)=}")
    updated_count = 0
    for missing in missing_game_version:
        replay = replay_files.parse_json(missing.json_s3_uri)
        game_version = replay.Header.Version.lower().replace("version", "").strip()
        existing = replay_manager.get_match(missing.match_id)
        if existing is None:
            continue
        existing.game_version = game_version
        result = replay_manager.update_match(existing)
        logger.info(f"Updated {missing.match_id} success={result}")
        if result:
            updated_count += 1
        if updated_count >= max_to_update:
            break
    return {"updated": updated_count}


@app.post("/api/fix_incomplete/")
def fix_incomplete(
    max_to_update: int = 1,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> dict[str, int]:
    winner_but_incomplete = replay_manager.list_matches_with_winner_but_incomplete(
        max_to_update
    )
    logger.info(f"{len(winner_but_incomplete)=} ")
    updated_count = 0
    for need_fix, has_stats in winner_but_incomplete:
        logger.info(need_fix.incomplete)
        logger.info(f"{need_fix.winning_team_id=}  {has_stats}")
        matches.reparse_replay(need_fix.match_id, replay_manager)
        logger.info(f"Updated {need_fix}")
        updated_count += 1
        if updated_count >= max_to_update:
            break
    return {"updated": updated_count}


@app.post("/api/fix_unk_player/")
def fix_unk_players(
    max_to_update: int = 1,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> dict[str, int]:
    match_ids = replay_manager.list_matches_with_player_unk(max_to_update * 10)
    logger.info(f"{len(match_ids)=} ")
    updated_count = 0
    for match_id in match_ids:
        updated = matches.reparse_replay(match_id, replay_manager)
        logger.info(f"Updated {updated}")
        if updated:
            updated_count += 1
        if updated_count >= max_to_update:
            break
    return {"updated": updated_count}


@app.get("/api/replays_without_playerstats/")
def replays_without_playerstats(
    max_to_return: int = 10,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> Generator[dict[str, Any]]:  # Generator return type - FastAPI streams this
    missing_player_stats = replay_manager.list_jsons_without_player_stats(max_to_return)
    for row in missing_player_stats:
        yield {
            "match_id": row.match_id,
            "url": row.url,
            "s3_path": row.s3_path,
            "version": row.version,
            "presigned_url": replay_files.presigned_url(row.s3_path),
        }


@app.get("/api/player_game_counts/")
def get_player_game_counts(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> list[PlayerGameCount]:
    """Get all player names with their total game count, sorted by count descending."""
    all_matches = sorted_deduped_matches(replay_manager)
    counts: dict[str, int] = {}
    for game in all_matches.values():
        for player in game.players:
            name = player_ids.resolve_player_name(player.name, player.color)
            counts[name] = counts.get(name, 0) + 1
    return [
        PlayerGameCount(name=name, count=count)
        for name, count in sorted(counts.items(), key=lambda x: x[1], reverse=True)
    ]


@app.get("/api/player_ratings/")
def get_player_ratings(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> PlayerRatingData:
    games = competitive_matches(replay_manager)

    ratings_and_counts = player_rating.compute_player_ratings(list(games.values()))
    counts = ratings_and_counts.game_counts

    def convert(rating: player_rating.NamedRating) -> PlayerRatings:
        return PlayerRatings(
            name=rating.name,
            ordinal=rating.ordinal(),
            mu=rating.mu,
            sigma=rating.sigma,
            atdate=rating.at_date,
            game_count=counts.get(rating.name),
        )

    def convert_short(rating: player_rating.NamedRating) -> ShortPlayerRating:
        return ShortPlayerRating(
            mu=rating.mu,
            sigma=rating.sigma,
            atdate=rating.at_date,
        )

    converted = [convert(r) for r in ratings_and_counts.ratings]
    over_time = {
        name: [convert_short(r) for r in ratings]
        for name, ratings in ratings_and_counts.over_time.items()
    }
    logger.info(f"over time data {over_time}")
    return PlayerRatingData(
        player_rating=converted,
        player_rating_overtime=over_time,
    )


PlayerEnum = Enum(  # type: ignore[misc]
    "PlayerEnum", {v.upper(): v for v in player_ids.PLAYER_NAMES}, type=str
)


class SelectedPLayers(BaseModel):
    players: list[PlayerEnum] = []


@app.get("/api/balance_teams/")
def balance_teams(
    players: SelectedPLayers = Query(default=SelectedPLayers(players=[])),
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> dict[str, float]:
    if len(players.players) < 4:
        return {}

    games = competitive_matches(replay_manager)

    team_scores = create_teams.balance_teams(
        list(games.values()), player_list={str(p.value) for p in players.players}
    )
    logger.info(f"Team Scores {team_scores}")
    return {",".join(i): v for i, v in team_scores.items()}


@app.get("/api/partition_teams/{team_size}")
def partition_teams(
    team_size: int = 2,
    players: SelectedPLayers = Query(default=SelectedPLayers(players=[])),
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> list[list[str]]:
    games = list(competitive_matches(replay_manager).values())
    teams = create_teams.create_balanced_teams(
        games, player_list={str(p.value) for p in players.players}, team_size=team_size
    )

    return teams


app.mount("/", StaticFiles(directory="build", html=True), name="build")


exception_handling.setup_error_handling(app)
