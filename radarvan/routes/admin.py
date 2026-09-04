"""Admin / operational / debug endpoints.

Two routers, because there are two kinds of caller:

- ``router`` - the read-only debug/override *listings*, at the normal tier so
  the DebugData page can reach them with the key the browser ships.
- ``session_router`` - every mutating operation, included in main.py *without*
  the API-key dependency because the credential is a signed session cookie.
  The reparse button on the DebugData page carries ``ADMIN_LOGIN``; everything
  else - scrape, backfill, bulk reparse, override, delete - carries
  ``OPS_ADMIN``, which is what the
  admin control panel drives.

These used to sit on ``router`` behind an admin-tier ``X-API-Key``, which no
browser can hold: the frontend ships one normal-tier key to every visitor. The
gates still accept an admin key, so curl and ops scripts are unaffected.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, date, datetime, timedelta
import asyncio
import structlog
from typing import Any, NamedTuple

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from .. import matches, replay_files, schedule, tournament_membership, utils
from ..api_types import (
    AdminUser,
    MatchInfo,
    Team,
    WinnerOverride,
)
from ..cache import invalidate_match_caches, sorted_deduped_matches
from ..db import Match, PlayerKey
from ..db_utils import MatchDebugData, ReplayManager
from ..dependencies import (
    ADMIN_LOGIN,
    OPS_ADMIN,
    db_manager,
    get_bracket_repo,
    get_replay_manager,
    get_user_repo,
)
from ..repositories import BracketRepo, UserRepo
from ..game_composition import GameComposition

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["admin"])

# Admin actions driven from the UI. Included in main.py *without* the API-key
# dependency: the browser sends a session cookie, not an admin key. Every route
# here must carry `dependencies=OPS_ADMIN` (or `ADMIN_LOGIN` for the DebugData
# reparse button) - the router itself has no gate of its own.
session_router = APIRouter(tags=["admin"])


@session_router.get("/api/admin/users", dependencies=OPS_ADMIN)
def list_users(repo: UserRepo = Depends(get_user_repo)) -> list[AdminUser]:
    """Current Discord/player associations for the operations admin panel."""
    return [AdminUser.model_validate(user) for user in repo.list_users()]


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


@session_router.post("/api/scrape/{days}", dependencies=OPS_ADMIN)
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


@session_router.post("/api/matches/{match_id}/composition", dependencies=OPS_ADMIN)
def compute_match_composition(
    match_id: int,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> GameComposition:
    """Compute and persist the composition (teams, humans vs CPUs, category) for a match."""
    result = replay_manager.compute_and_save_composition(match_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Match {match_id} not found")
    return result


@session_router.post("/api/backfill/composition", dependencies=OPS_ADMIN)
def backfill_match_composition(
    max_to_update: int = 100,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> dict[str, int]:
    """Backfill and persist the composition for matches missing it."""
    updated = 0
    missing = 0
    for match_id in replay_manager.list_matches_without_composition():
        if updated >= max_to_update:
            break
        result = replay_manager.compute_and_save_composition(match_id)
        if result is None:
            # Match vanished between the listing and the recompute; skip it
            # rather than aborting the whole backfill.
            missing += 1
            continue
        updated += 1
    return {"updated": updated, "missing": missing}


@session_router.post("/api/reparse/{match_id}", dependencies=ADMIN_LOGIN)
def reparse(
    match_id: int,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> MatchInfo | None:
    """Rerun the replay parser on this match.

    On the cookie-session router, not the API-key one: the DebugData page's
    reparse button drives this, and the key the browser ships is normal-tier
    by design. Authorization is the logged-in user being an admin.
    """
    replay = matches.reparse_replay(match_id, replay_manager)
    replay_manager.compute_and_save_composition(match_id)
    # No details_from_id.cache_clear() needed: details_from_id is keyed on CORPUS,
    # which this bumps, so the pre-reparse entry is unreachable. The durable row is
    # deleted inside reparse_replay - that tier is keyed on DETAILS_VERSION, which
    # a reparse does not move.
    invalidate_match_caches()
    return replay


@session_router.post("/api/clear_details_cache/", dependencies=OPS_ADMIN)
def clear_details_cache(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> dict[str, int]:
    """Drop every row of the durable MatchDetails cache and the in-process
    derivation fronting it. A debugging hatch - normal invalidation is per-match
    (reparse) or implicit via DETAILS_VERSION, and derivation changes should
    bump the version rather than lean on this.

    Invalidating the corpus is a wider hammer than `details_from_id` alone, and
    deliberately so: reaching for a single cache by name is the vocabulary the
    registry exists to remove, and this also kicks the re-warm that emptying the
    durable tier makes worth doing.
    """
    deleted = replay_manager.delete_all_cached_details()
    invalidate_match_caches()
    logger.info("cleared details cache", deleted=deleted)
    return {"deleted": deleted}


@session_router.post("/api/reparse_recent/", dependencies=OPS_ADMIN)
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


@session_router.post("/api/reparse_before_date/", dependencies=OPS_ADMIN)
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


@session_router.post("/api/reparse_non_v2/", dependencies=OPS_ADMIN)
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


@session_router.post("/api/set_override/", dependencies=OPS_ADMIN)
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


@session_router.delete("/api/match/{match_id}", dependencies=OPS_ADMIN)
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


@session_router.delete("/api/override/{match_id}", dependencies=OPS_ADMIN)
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


@session_router.post("/api/backfill/tournament_games", dependencies=OPS_ADMIN)
def backfill_tournament_games(
    replay_manager: ReplayManager = Depends(get_replay_manager),
    bracket_repo: BracketRepo = Depends(get_bracket_repo),
) -> dict[str, int]:
    """Register the known tournaments and persist their game links.

    Idempotent - re-running picks up games played since the last run and
    leaves admin-set (``manual``) links untouched, so this is safe to call
    repeatedly and is what the scrape job calls after registering matches.
    Unlike the other backfills there's no ``max_to_update``: detection is one
    in-memory pass over the already-cached match list, not per-match S3 work.
    """
    all_matches = list(sorted_deduped_matches(replay_manager).values())
    counts = tournament_membership.sync_links(replay_manager, bracket_repo, all_matches)
    invalidate_match_caches()
    return counts


def _roles_from_json(json_s3_uri: str) -> list[tuple[PlayerKey, int]]:
    """A match's players in header order, as (identity tuple, role) pairs.

    Order is what `set_player_roles` pairs on; the identity tuple is its
    fallback. Built the same way `replay_to_db_match` writes the rows, so the
    caller can stamp roles onto existing match_players without rebuilding the
    match.
    """
    replay = replay_files.parse_json(json_s3_uri)
    return [
        ((p.name, p.color, int(p.team), int(p.general)), int(p.role_or_guess()))
        for p in utils.players_from_replay(replay)
    ]


@session_router.post("/api/backfill_player_roles/", dependencies=OPS_ADMIN)
def backfill_player_roles(
    max_to_update: int = 100,
    max_concurrent: int = 16,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> dict[str, int]:
    """Stamp match_players.role from each match's already-parsed replay JSON.

    Reads the stored S3 JSON - does NOT call cncstats - so this is free to run
    in bulk. Idempotent and incremental: it only looks at matches that still
    have a role-less player row, so it can be called repeatedly until
    `remaining` is 0.
    """
    candidates = replay_manager.list_matches_with_unset_roles(limit=max_to_update)
    logger.info("backfill_player_roles", candidates=len(candidates))

    # Phase 1: S3 fetches in parallel. Plain strings only - no ORM objects
    # cross into the worker threads.
    fetched: dict[int, list[tuple[PlayerKey, int]]] = {}
    failed = 0
    with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        future_to_match = {
            executor.submit(_roles_from_json, uri): match_id
            for match_id, uri in candidates
        }
        for future in as_completed(future_to_match):
            match_id = future_to_match[future]
            try:
                fetched[match_id] = future.result()
            except Exception:
                logger.exception("failed to load JSON for match", match_id=match_id)
                failed += 1

    # Phase 2: DB writes serially on the request's session.
    rows_updated = 0
    matches_updated = 0
    for match_id, roles in fetched.items():
        updated = replay_manager.set_player_roles(match_id, roles)
        if updated:
            matches_updated += 1
            rows_updated += updated

    if matches_updated:
        invalidate_match_caches()
    return {
        "matches_updated": matches_updated,
        "rows_updated": rows_updated,
        "checked": len(candidates),
        "failed": failed,
    }


class MatchPair(NamedTuple):
    db_match: Match
    new_match: Match


def _fetch_and_parse(json_s3_uri: str, replay_file_url: str) -> Match:
    """Fetch JSON from S3 and convert to a Match - takes plain strings (no ORM
    objects), so it's safe to run in worker threads."""
    replay = replay_files.with_filename(
        replay_files.parse_json(json_s3_uri),
        replay_file_url,
    )
    return matches.replay_to_db_match(replay, json_s3_uri)


@session_router.post("/api/refresh_matches_from_json/", dependencies=OPS_ADMIN)
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
    # Extract plain strings here, on the request's session: ORM objects must not
    # cross into the worker threads (sessions aren't thread-safe, and attribute
    # access can lazy-load through the session they're bound to).
    candidates = [
        (
            db_match,
            db_match.replay_json.json_s3_uri,
            db_match.replay_json.replay_file_url,
        )
        for db_match in all_matches
        if db_match.replay_json is not None
    ][: max_to_update * 4]

    # Phase 1: fetch and parse candidates from S3 in parallel
    parsed: list[MatchPair] = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_match = {
            executor.submit(_fetch_and_parse, json_uri, file_url): db_match
            for db_match, json_uri, file_url in candidates
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
    try:
        for db_match, new_match in parsed:
            if updated_count >= max_to_update:
                break
            if matches.matches_differ(db_match, new_match):
                replay_manager.update_match(new_match)
                updated_count += 1
        if updated_count:
            replay_manager.session.commit()
    finally:
        replay_manager.auto_commit = True
    if updated_count:
        invalidate_match_caches()
    return {"updated": updated_count, "checked": len(parsed)}


@session_router.post("/api/register_matches/", dependencies=OPS_ADMIN)
def register_matches(
    max_to_update: int = 100,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> dict[str, int]:
    """Register Match rows for any ParsedReplayJson that has no corresponding Match.

    `checked` counts replays read from S3, including ones declined as too
    short - so `updated: 0` with a non-zero `checked` means "run me again",
    not "queue drained".
    """
    outcome = matches.register_matches(replay_manager, max_to_update=max_to_update)
    if outcome.registered:
        invalidate_match_caches()
    return {"updated": outcome.registered, "checked": outcome.examined}


@session_router.post("/api/fix_incomplete/", dependencies=OPS_ADMIN)
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
        replay_manager.compute_and_save_composition(need_fix.match_id)
        logger.info("updated", match=need_fix)
        updated_count += 1
        if updated_count >= max_to_update:
            break
    if updated_count:
        invalidate_match_caches()
    return {"updated": updated_count}


@session_router.post("/api/fix_unk_player/", dependencies=OPS_ADMIN)
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
            replay_manager.compute_and_save_composition(match_id)
            updated_count += 1
        if updated_count >= max_to_update:
            break
    if updated_count:
        invalidate_match_caches()
    return {"updated": updated_count}
