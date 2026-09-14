"""Shared recomputation and publication of the computed-statistics snapshot."""

import asyncio
from collections import Counter
from datetime import UTC, datetime
from typing import NamedTuple

import structlog

from . import general_stats, opening_book, player_rating, superlatives
from .api_types import General, MatchInfo, Statistic, SuperlativeData
from .cache import competitive_matches
from .db_utils import DatabaseManager
from .notify import notify_async
from .repositories.stats import StatsRepo

logger = structlog.get_logger(__name__)

# Manual and scheduled runs must not interleave whole-table replacements.
recompute_lock = asyncio.Lock()
# BackgroundTasks only start after the response is sent, so the lock alone
# leaves a window in which two quick POSTs both see it free and both queue.
_queued = False


class IncompleteSnapshot(Exception):
    """A run finished but produced a snapshot unsafe to publish over the previous one."""


class _Inputs(NamedTuple):
    games: list[MatchInfo]
    stale: bool


class _Projections(NamedTuple):
    details: list[SuperlativeData]
    tallies: dict[tuple[General, tuple[str, ...]], opening_book._Tally]


def _load_inputs(db_manager: DatabaseManager) -> _Inputs:
    with db_manager.get_replay_manager() as replay_manager:
        games = competitive_matches(replay_manager)
        return _Inputs(
            games=[game for game in games.values() if game.winning_team > 0],
            stale=replay_manager.computed_stats_are_stale(days=3),
        )


async def _load_projections(
    games: list[MatchInfo], db_manager: DatabaseManager
) -> _Projections:
    """Both full-corpus passes, with the survivor cancelled if either fails.

    asyncio.gather leaves the sibling running when one side raises; on a 512 MB
    dyno an orphaned MatchDetails sweep outliving the lock means the next run
    overlaps it.
    """
    details = asyncio.ensure_future(
        superlatives.load_many_superlative_data([game.id for game in games], db_manager)
    )
    tallies = asyncio.ensure_future(
        opening_book.load_opening_tallies(games, db_manager)
    )
    done, pending = await asyncio.wait(
        {details, tallies}, return_when=asyncio.FIRST_EXCEPTION
    )
    for task in pending:
        task.cancel()
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)
    for task in done:
        task.result()  # re-raises the failure that ended the wait
    return _Projections(details=details.result(), tallies=tallies.result())


def _kind_of(stat_name: str) -> str:
    if stat_name.startswith(general_stats.GENERAL_VALUE_STAT_PREFIX):
        return "general_value"
    if stat_name.startswith(opening_book.OPENING_STAT_PREFIX):
        return "opening_book"
    return "records"


def _emptied_kinds(
    previous: list[Statistic], candidate: list[Statistic]
) -> tuple[str, ...]:
    """Kinds the previous snapshot had rows for and the candidate has none of."""
    before = Counter(_kind_of(stat.stat_name) for stat in previous)
    after = Counter(_kind_of(stat.stat_name) for stat in candidate)
    return tuple(sorted(kind for kind in before if not after[kind]))


def _publish(db_manager: DatabaseManager, stats: list[Statistic]) -> None:
    """Replace the snapshot, refusing a candidate that drops a whole projection.

    Read and write share one transaction so the comparison cannot race another
    writer.
    """
    with db_manager.get_session() as session:
        repo = StatsRepo(session, auto_commit=False)
        emptied = _emptied_kinds(repo.get_computed_stats(), stats)
        if emptied:
            raise IncompleteSnapshot(
                f"refusing to publish: {', '.join(emptied)} would be emptied"
            )
        repo.replace_computed_stats(stats)


async def recompute(db_manager: DatabaseManager) -> superlatives.Superlatives:
    """Compute every projection and publish it in one transaction.

    Atomicity alone does not protect the snapshot: a degraded run raises nothing
    and would commit a truncated replacement over good data. Refuse instead, so
    the previous snapshot survives until a complete run succeeds.
    """
    async with recompute_lock:
        start = datetime.now(UTC)
        games, stale = await asyncio.to_thread(_load_inputs, db_manager)
        if stale:
            await notify_async(
                f"Computing records (started at {start:%Y-%m-%d %H:%M:%S})"
            )
        if not games:
            raise IncompleteSnapshot("refusing to publish: no competitive matches")
        details, tallies = await _load_projections(games, db_manager)
        ratings = await asyncio.to_thread(player_rating.compute_player_ratings, games)
        result, failed_groups = await asyncio.to_thread(
            superlatives.get_superlatives, games, details, ratings
        )
        if failed_groups:
            raise IncompleteSnapshot(
                f"refusing to publish: {len(failed_groups)} stat groups failed "
                f"({', '.join(failed_groups)})"
            )
        value_stats = await asyncio.to_thread(
            general_stats.general_value_stats, games, details
        )
        value_rows = [
            Statistic(
                stat_name=f"{general_stats.GENERAL_VALUE_STAT_PREFIX}{kind}",
                date_computed=result.computed_at,
                value=float(total),
                player=str(int(general)),
            )
            for general, (destroyed, lost) in value_stats.items()
            for kind, total in (("destroyed", destroyed), ("lost", lost))
        ]
        book = await asyncio.to_thread(
            opening_book.build_opening_book, tallies, result.computed_at
        )
        opening_rows = opening_book.opening_book_stat_rows(book)
        snapshot = result.model_copy(
            update={"stats": result.stats + value_rows + opening_rows}
        )
        await asyncio.to_thread(_publish, db_manager, snapshot.stats)
        took = datetime.now(UTC) - start
        logger.info(
            "saved computed statistics",
            count=len(snapshot.stats),
            general_value_rows=len(value_rows),
            opening_book_rows=len(opening_rows),
            took=str(took),
        )
        if stale:
            await notify_async(
                f"Recomputed {len(snapshot.stats)} statistics for records, generals, "
                f"and opening book in {took}."
            )
        return snapshot


def recompute_pending() -> bool:
    """True while a run is queued or running."""
    return _queued or recompute_lock.locked()


def try_reserve_recompute() -> bool:
    """Claim the next run, or return False if one is already queued or running.

    Check and claim happen without an await between them, so two requests on the
    one event loop cannot both succeed.
    """
    global _queued
    if recompute_pending():
        return False
    _queued = True
    return True


async def reserved_recompute(db_manager: DatabaseManager) -> None:
    """Background entry point for the manual trigger; always frees the slot."""
    global _queued
    try:
        await recompute(db_manager)
    finally:
        _queued = False
