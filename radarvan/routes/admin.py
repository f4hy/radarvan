"""Admin / operational / debug endpoints.

These are mostly write or backfill operations; many are excluded from the
OpenAPI schema in production. Authentication is enforced via the global
verify_api_key dependency on the FastAPI app.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, date, datetime, timedelta
import asyncio
import structlog
from typing import Any, NamedTuple

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from .. import matches, replay_files, schedule
from ..api_types import MatchInfo, Team, WinnerOverride
from ..cache import details_from_id, invalidate_match_caches
from ..db import Match, ParsedReplayJson
from ..db_utils import MatchDebugData, ReplayManager
from ..dependencies import IS_DEV, db_manager, get_replay_manager
from ..game_composition import GameComposition

logger = structlog.get_logger(__name__)

router = APIRouter()


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


@router.post("/api/scrape/{days}")
def scrape(
    background_tasks: BackgroundTasks,
    days: int = 1,
) -> dict[str, str]:
    # The background task runs after this request's session is torn down, so it
    # gets the db_manager and opens its own session.
    invalidate_match_caches()
    background_tasks.add_task(schedule.update_games, db_manager, days)
    return {"scheduled": "ok"}


@router.get("/api/debug/match/{match_id}")
def debug_match(
    match_id: int,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> dict[str, Any]:
    """Return every row related to a match_id across all tables, keyed by table name."""
    debug_data = _debug_data_to_dict(replay_manager.get_all_data_for_match(match_id))
    rep = replay_manager.get_replay_json_by_match_id(match_id)
    if rep:
        par = replay_files.parse_replay(rep.replay_file_url, replay_manager)
        debug_data["header"] = par.header.model_dump_json()
    return debug_data


@router.get("/api/debug/json_url/{match_id}")
def get_match_json_url(
    match_id: int,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> dict[str, str]:
    """Return a presigned S3 URL for the parsed JSON of a match."""
    match = replay_manager.get_match(match_id)
    if match is None:
        raise HTTPException(status_code=404, detail=f"Match {match_id} not found")
    return {"url": replay_files.presigned_url(match.json_s3_uri)}


@router.post("/api/matches/{match_id}/composition")
def compute_match_composition(
    match_id: int,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> GameComposition:
    """Compute and persist the composition (teams, humans vs CPUs, category) for a match."""
    result = replay_manager.compute_and_save_composition(match_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Match {match_id} not found")
    return result


@router.post("/api/backfill/composition")
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


@router.post("/api/reparse/{match_id}")
def reparse(
    match_id: int,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> MatchInfo | None:
    """Rerun the replay parser on this match."""
    replay = matches.reparse_replay(match_id, replay_manager)
    replay_manager.compute_and_save_composition(match_id)
    invalidate_match_caches()
    details_from_id.cache_clear()
    return replay


@router.post("/api/clear_details_cache/", include_in_schema=IS_DEV)
def clear_details_cache(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> dict[str, int]:
    """Drop every row of the durable MatchDetails cache and the in-process LRU
    fronting it. Normal invalidation is per-match (reparse) or implicit via
    DETAILS_VERSION; this is for a full manual bust - e.g. debugging a stale
    row that shouldn't exist, or a derivation change that should have bumped
    the version but didn't.
    """
    deleted = replay_manager.delete_all_cached_details()
    details_from_id.cache_clear()
    logger.info("cleared details cache", deleted=deleted)
    return {"deleted": deleted}


@router.post("/api/reparse_recent/", include_in_schema=IS_DEV)
def reparse_recent(
    days: int = 3,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> dict[str, int | list[int]]:
    """Re-run cncstats on all matches whose game_date is within the last `days` days."""
    since = datetime.now(UTC).date() - timedelta(days=days)
    candidates = replay_manager.list_jsons_since_date(since)
    logger.info("reparse_recent", candidates=len(candidates), since=since)
    updated_ids: set[int] = set()
    for record in candidates:
        updated = matches.reparse_replay(record.match_id, replay_manager)
        if updated:
            replay_manager.compute_and_save_composition(record.match_id)
            updated_ids.add(updated.id)
    if updated_ids:
        invalidate_match_caches()
    return {
        "updated": len(updated_ids),
        "checked": len(candidates),
        "updated_ids": list(updated_ids),
    }


@router.post("/api/reparse_before_date/", include_in_schema=IS_DEV)
def reparse_before_date(
    before: date,
    max_to_update: int = 10,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> dict[str, int | list[int]]:
    """Re-run cncstats on matches whose parsed JSON was last updated before `before`.

    Calls cncstats for each match - slower than refresh_matches_from_json but picks
    up new fields added to the parser output.
    """
    candidates = replay_manager.list_jsons_parsed_before(before, limit=max_to_update)
    logger.info("reparse_before_date", candidates=len(candidates), before=before)
    updated_ids: set[int] = set()
    for record in candidates:
        try:
            updated = matches.reparse_replay(record.match_id, replay_manager)
            if updated:
                replay_manager.compute_and_save_composition(record.match_id)
                updated_ids.add(updated.id)
        except ValueError:
            logger.info("unable to reparse", match_id=record.match_id)
    if updated_ids:
        invalidate_match_caches()
    return {
        "updated": len(updated_ids),
        "checked": len(candidates),
        "updated_ids": list(updated_ids),
    }


@router.post("/api/reparse_non_v2/", include_in_schema=IS_DEV)
async def reparse_non_v2(
    max_to_update: int = 10,
    max_concurrent: int = 8,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> dict[str, int | list[int]]:
    """Re-run cncstats on matches whose parsed JSON was last updated before `before`.

    Calls cncstats for each match - slower than refresh_matches_from_json but picks
    up new fields added to the parser output.
    """
    candidates = replay_manager.list_jsons_non_v2(limit=max_to_update)
    logger.info("reparse_non_v2", candidates=len(candidates))
    # Extract plain values here, on the request's session: ORM objects must not
    # cross into the worker threads (sessions aren't thread-safe, and attribute
    # access can lazy-load through the session they're bound to).
    work_items = [matches.ReparseInputs.from_row(p) for p in candidates]

    semaphore = asyncio.Semaphore(max_concurrent)

    async def _reparse_one(item: matches.ReparseInputs) -> int | None:
        async with semaphore:

            def _work() -> int | None:
                with db_manager.get_replay_manager() as rm:
                    try:
                        updated = matches.reparse_existing(item, rm)
                    except Exception as e:
                        logger.exception(
                            "error reparsing match", match_id=item.match_id
                        )
                        raise RuntimeError(
                            f"Error reparseing match {item.match_id}"
                        ) from e
                    if updated:
                        rm.compute_and_save_composition(updated.id)
                        return updated.id
                    return None

            return await asyncio.to_thread(_work)

    results = await asyncio.gather(*[_reparse_one(w) for w in work_items])
    updated_ids = [r for r in results if r is not None]
    if updated_ids:
        invalidate_match_caches()
    return {
        "updated": len(updated_ids),
        "checked": len(candidates),
        "updated_ids": updated_ids,
    }


@router.get("/api/overrides")
def get_overrides(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> list[WinnerOverride]:
    """Get winner overrides."""
    overrides = replay_manager.get_overrides()
    return [
        WinnerOverride(
            match_id=o.match_id,
            winning_team_id=o.winning_team_id or Team.NONE,
            incomplete=o.incomplete,
        )
        for o in overrides.values()
    ]


@router.post("/api/set_override/")
def set_override(
    match_id: int,
    winner: Team | None = None,
    incomplete: str | None = None,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> WinnerOverride:
    """Set a winner and/or incomplete override for a match. Persists through re-parses."""
    saved = replay_manager.set_override(
        match_id, winner=winner.value if winner else None, incomplete=incomplete
    )
    invalidate_match_caches()
    return WinnerOverride(
        match_id=saved.match_id,
        winning_team_id=saved.winning_team_id or Team.NONE,
        incomplete=saved.incomplete,
    )


@router.delete("/api/match/{match_id}")
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
    invalidate_match_caches()
    return counts


@router.delete("/api/override/{match_id}")
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
    invalidate_match_caches()
    return {"status": "deleted", "match_id": str(match_id)}


class MatchPair(NamedTuple):
    db_match: Match
    new_match: Match


def _fetch_and_parse(match_id: int, json_record: ParsedReplayJson) -> Match:
    """Fetch JSON from S3 and convert to a Match - no DB access, safe to run in threads."""
    replay = replay_files.with_filename(
        replay_files.parse_json(json_record.json_s3_uri),
        json_record.replay_file_url,
    )
    return matches.replay_to_db_match(replay, json_record.json_s3_uri)


@router.post("/api/refresh_matches_from_json/", include_in_schema=IS_DEV)
def refresh_matches_from_json(
    max_to_update: int = 10,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> dict[str, int]:
    """Re-parse existing JSON files from S3 and update DB matches if they differ.

    Does NOT re-run cncstats - only reloads the already-parsed JSON from S3.
    Phase 1 (S3 fetches) runs in parallel; Phase 2 (DB writes) runs serially.
    Fetches up to max_to_update * 4 candidates to account for non-differing matches.
    """
    all_matches = replay_manager.list_matches(0.0)
    candidates = [
        (db_match, db_match.replay_json)
        for db_match in all_matches
        if db_match.replay_json is not None
    ][: max_to_update * 4]

    # Phase 1: fetch and parse candidates from S3 in parallel
    parsed: list[MatchPair] = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_match = {
            executor.submit(_fetch_and_parse, db_match.match_id, json_record): db_match
            for db_match, json_record in candidates
        }
        for future in as_completed(future_to_match):
            db_match = future_to_match[future]
            try:
                new_match = future.result()
                parsed.append(MatchPair(db_match=db_match, new_match=new_match))
            except Exception:
                logger.exception(
                    "failed to load JSON for match", match_id=db_match.match_id
                )

    # Phase 2: compare and write in a single transaction
    updated_count = 0
    replay_manager.auto_commit = False
    for db_match, new_match in parsed:
        if updated_count >= max_to_update:
            break
        if matches.matches_differ(db_match, new_match):
            replay_manager.update_match(new_match)
            updated_count += 1
    if updated_count:
        replay_manager.session.commit()
    replay_manager.auto_commit = True
    return {"updated": updated_count, "checked": len(parsed)}


@router.post("/api/register_matches/", include_in_schema=IS_DEV)
def register_matches(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> dict[str, str]:
    """Register Match rows for any ParsedReplayJson that has no corresponding Match."""
    matches.register_matches(replay_manager)
    return {"status": "ok"}


@router.post("/api/fix_incomplete/", include_in_schema=IS_DEV)
def fix_incomplete(
    max_to_update: int = 1,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> dict[str, int]:
    winner_but_incomplete = replay_manager.list_matches_with_winner_but_incomplete(
        max_to_update
    )
    logger.info("winner but incomplete", count=len(winner_but_incomplete))
    updated_count = 0
    for need_fix, has_stats in winner_but_incomplete:
        logger.info(
            "fixing match",
            incomplete=need_fix.incomplete,
            winning_team_id=need_fix.winning_team_id,
            has_stats=has_stats,
        )
        matches.reparse_replay(need_fix.match_id, replay_manager)
        logger.info("updated", match=need_fix)
        updated_count += 1
        if updated_count >= max_to_update:
            break
    if updated_count:
        invalidate_match_caches()
    return {"updated": updated_count}


@router.post("/api/fix_unk_player/", include_in_schema=IS_DEV)
def fix_unk_players(
    max_to_update: int = 1,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> dict[str, int]:
    match_ids = replay_manager.list_matches_with_player_unk(max_to_update * 10)
    logger.info("matches with unknown player", count=len(match_ids))
    updated_count = 0
    for match_id in match_ids:
        updated = matches.reparse_replay(match_id, replay_manager)
        logger.info("updated", match=updated)
        if updated:
            updated_count += 1
        if updated_count >= max_to_update:
            break
    if updated_count:
        invalidate_match_caches()
    return {"updated": updated_count}
