"""Reparse every match through cncstats.

Run this after a cncstats bugfix/update that requires refreshing already-parsed
data. Reparses one canonical replay per match (see ``_pick_canonical``) and
writes the resulting JSON + DB rows in place.

Reparsing is one cncstats HTTP round-trip per replay, so this runs them
concurrently - bounded by ``--max-concurrent`` (default 30, and capped there)
so we don't hammer the cncstats service. Concurrency is only across distinct
matches: ``MatchRepo.update_match`` clears a match's players and re-inserts
them, so two overlapping reparses of the *same* match_id (e.g. a game with
several independently-uploaded replay files) can race - each transaction
deletes-then-reinserts, and interleaved commits leave duplicate MatchPlayer
rows behind. Deduping to one replay per match_id sidesteps that; re-running
this script also self-heals any match already left with duplicates, since the
single reparse clears the whole (bloated) player collection before rebuilding
it clean.

Usage:
    uv run python reparse_all_replays.py [--max-concurrent N] [--limit N]

Note: this talks directly to the database, not the running API server, so it
won't clear that process's in-memory caches. If radarvan is running against
the same database, hit ``POST /api/clear_details_cache/`` afterwards.
"""

import argparse
import asyncio
import logging
import os

from tqdm import tqdm

from radarvan import matches
from radarvan.db import ParsedReplayJson
from radarvan.db_utils import DatabaseManager
from radarvan.logging_config import configure_logging

MAX_CONCURRENT = 30


def _pick_canonical(rows: list[ParsedReplayJson]) -> list[ParsedReplayJson]:
    """One row per match_id, preferring the same row `get_replay_json_by_match_id` would.

    Multiple ParsedReplayJson rows can share a match_id (e.g. the same game
    captured independently by several players' clients). Only one may ever be
    reparsed per match_id - see the module docstring for why.
    """
    best: dict[int, ParsedReplayJson] = {}
    best_key: dict[int, tuple[bool, int]] = {}
    for row in rows:
        key = ("upload" in row.json_s3_uri, row.num_time_stamps or 0)
        if row.match_id not in best_key or key > best_key[row.match_id]:
            best[row.match_id] = row
            best_key[row.match_id] = key
    return list(best.values())


async def reparse_all(
    db_manager: DatabaseManager, max_concurrent: int, limit: int | None
) -> None:
    with db_manager.get_replay_manager() as replay_manager:
        candidates = _pick_canonical(replay_manager.list_jsons())
        if limit is not None:
            candidates = candidates[:limit]
        # Extract plain values while the session is still open - rows become
        # detached (and lazy attribute access raises) once the `with` exits.
        work_items = [matches.ReparseInputs.from_row(row) for row in candidates]
    tqdm.write(f"Reparsing {len(work_items)} matches (max_concurrent={max_concurrent})")

    semaphore = asyncio.Semaphore(max_concurrent)
    failed_match_ids: list[int] = []

    async def reparse_one(item: matches.ReparseInputs) -> None:
        async with semaphore:

            def work() -> None:
                with db_manager.get_replay_manager() as rm:
                    try:
                        updated = matches.reparse_existing(item, rm)
                        if updated:
                            rm.compute_and_save_composition(updated.id)
                    except Exception:
                        failed_match_ids.append(item.match_id)

            await asyncio.to_thread(work)

    tasks = [asyncio.ensure_future(reparse_one(item)) for item in work_items]
    for task in tqdm(
        asyncio.as_completed(tasks),
        total=len(tasks),
        desc="Reparsing replays",
        unit="replay",
        smoothing=0.1,
    ):
        await task

    tqdm.write(f"Reparse complete: {len(work_items)} total, {len(failed_match_ids)} failed")
    if failed_match_ids:
        tqdm.write(f"Failed match_ids: {failed_match_ids}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=MAX_CONCURRENT,
        help=f"Max concurrent cncstats reparses (default/cap {MAX_CONCURRENT})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only reparse the first N replays (for testing a subset first)",
    )
    args = parser.parse_args()
    if args.max_concurrent > MAX_CONCURRENT:
        raise SystemExit(
            f"--max-concurrent must be <= {MAX_CONCURRENT} to avoid overwhelming cncstats"
        )

    constring = os.getenv("DATABASE_URL")
    if constring is None:
        raise RuntimeError("DATABASE_URL environment variable is not set")

    configure_logging(dev=True)
    # Bulk-reparse generates a log line (or several) per replay across radarvan's
    # own logging and its dependencies; disable it all so tqdm's progress bar is
    # the only thing on the terminal. Failures are still tracked and summarized
    # after the bar completes.
    logging.disable(logging.CRITICAL)
    db_manager = DatabaseManager(constring)
    asyncio.run(reparse_all(db_manager, args.max_concurrent, args.limit))


if __name__ == "__main__":
    main()
