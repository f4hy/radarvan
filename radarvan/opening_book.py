"""Opening-book style clustering of early build orders, per general.

Chess-site framing: the first few buildings a player puts down settle into a
handful of recognizable archetypes (fast War Factory, Patriot turtle, Airfield
tech, ...), and this tracks each archetype's popularity and win rate per
general. Confirmed on the real corpus before building this: capping the key to
a short prefix (rather than a longer one) is what turns noise into signal - at
depth 6, ~300 exact sequences per general with the top 8 covering under a
third of games; at depth 4, ~40-55 sequences with the top 8 covering 73-85%.
Depth 5 trades some of that coverage (30-65% of games per general fall to
"other" instead of a named opening) for one more real distinction - a second
War Factory/Airfield/Patriot Battery as its own line rather than folded into
the first build of that type.

Only cheap enough to run as part of the nightly superlatives recompute, not
live per-request - see routes/superlatives._do_recompute (mirrors
general_stats.general_value_stats).
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import NamedTuple

import structlog
from pydantic import ValidationError

from . import player_ids
from .api_types import (
    BuildOrder,
    General,
    GeneralOpeningBook,
    MatchInfo,
    Opening,
    OpeningBook,
    Statistic,
)
from .build_order import _MAX_ROWS as _BUILD_ORDER_MAX_ROWS
from .db_utils import DatabaseManager

logger = structlog.get_logger(__name__)

# Non-economy buildings kept per opening key. See module docstring for why 5.
OPENING_DEPTH = 5

# opening_key() expands build_order.py's collapsed runs back into individual
# builds (see its docstring), so it can only ever see _MAX_ROWS collapsed rows'
# worth of raw builds - always >= OPENING_DEPTH today, but nothing else ties
# the two together, so a future drop in _MAX_ROWS would silently start
# truncating openings. Fail loudly instead.
assert OPENING_DEPTH <= _BUILD_ORDER_MAX_ROWS, (
    "OPENING_DEPTH can't exceed build_order._MAX_ROWS - opening_key has "
    "nothing more to expand past that many collapsed rows"
)

# An opening below this many games gets folded into "other" rather than shown
# as its own named row - a one-off build isn't a strategy anyone is playing.
MIN_GAMES_FOR_OPENING = 15

# computed_statistics rows for this feature are tagged with this prefix so the
# reader can pick them out from everything else recompute writes to that
# table (mirrors general_stats.GENERAL_VALUE_STAT_PREFIX).
OPENING_STAT_PREFIX = "__opening_book_"


@dataclass
class _Tally:
    games: int = 0
    wins: int = 0


class _Row(NamedTuple):
    key: tuple[str, ...]
    tally: _Tally


def opening_key(order: BuildOrder) -> tuple[str, ...]:
    """The first OPENING_DEPTH buildings, one entry per build.

    `order.buildings` is already collapsed into runs (`_collapse_runs` in
    build_order.py), so a double SupplyCenter arrives as a single entry with
    `count=2` - expand it back out here, since building the same thing twice
    in a row before moving on is a materially different (slower, more
    economic) opening than building it once.
    """
    expanded: list[str] = []
    for b in order.buildings:
        if b.is_economy:
            continue
        expanded.extend([b.name] * b.count)
        if len(expanded) >= OPENING_DEPTH:
            break
    return tuple(expanded[:OPENING_DEPTH])


def _general_and_won_by_match(
    games: list[MatchInfo],
) -> dict[int, dict[str, tuple[General, bool]]]:
    """Per-match, resolved player name -> (general, won). Mirrors
    general_stats.general_value_stats's general_by_match construction."""
    by_match: dict[int, dict[str, tuple[General, bool]]] = {}
    for g in games:
        entry = {
            player_ids.resolve_player_name(p.name, p.color): (General(p.general), p.won)
            for p in g.roster().humans
            if p.has_known_general
        }
        if entry:
            by_match[g.id] = entry
    return by_match


async def load_opening_tallies(
    games: list[MatchInfo],
    db_manager: DatabaseManager,
    max_concurrent: int = 2,
    chunk_size: int = 10,
) -> dict[tuple[General, tuple[str, ...]], _Tally]:
    """Games-and-wins tally per (general, opening key), across `games`.

    Loads each match's MatchDetails just long enough to read build_orders off
    it, then lets it go - mirrors superlatives.load_many_superlative_data's
    memory-conscious pattern rather than holding every match's full
    MatchDetails (build orders, kill events, APM series, ...) in memory at
    once for the whole corpus.
    """
    from .match_details import load_match_details_threadsafe

    by_match = _general_and_won_by_match(games)
    tallies: dict[tuple[General, tuple[str, ...]], _Tally] = defaultdict(_Tally)
    semaphore = asyncio.Semaphore(max_concurrent)

    async def _bounded(match_id: int) -> None:
        players = by_match[match_id]
        async with semaphore:
            details = await asyncio.to_thread(
                load_match_details_threadsafe, match_id, db_manager
            )
        if details is None:
            return
        for name, order in details.build_orders.items():
            # build_orders is keyed by the raw in-replay name, not the
            # alias-resolved one - resolve here to join against by_match.
            info = players.get(player_ids.resolve_player_name(name))
            if info is None:
                continue
            general, won = info
            key = opening_key(order)
            if not key:
                continue
            tally = tallies[(general, key)]
            tally.games += 1
            if won:
                tally.wins += 1

    match_ids = list(by_match.keys())
    for i in range(0, len(match_ids), chunk_size):
        chunk = match_ids[i : i + chunk_size]
        await asyncio.gather(*[_bounded(mid) for mid in chunk])
    return tallies


def build_opening_book(
    tallies: dict[tuple[General, tuple[str, ...]], _Tally], computed_at: date
) -> OpeningBook:
    """Tallies into the wire shape: named openings above MIN_GAMES_FOR_OPENING,
    everything thinner rolled into that general's "other" bucket."""
    by_general: defaultdict[General, list[_Row]] = defaultdict(list)
    for (general, key), tally in tallies.items():
        by_general[general].append(_Row(key, tally))

    generals: list[GeneralOpeningBook] = []
    for general, rows in by_general.items():
        rows.sort(key=lambda r: -r.tally.games)
        named = [r for r in rows if r.tally.games >= MIN_GAMES_FOR_OPENING]
        other = [r for r in rows if r.tally.games < MIN_GAMES_FOR_OPENING]
        generals.append(
            GeneralOpeningBook(
                general=general,
                total_games=sum(r.tally.games for r in rows),
                openings=[
                    Opening(
                        buildings=list(r.key),
                        game_count=r.tally.games,
                        win_count=r.tally.wins,
                        win_rate=r.tally.wins / r.tally.games,
                    )
                    for r in named
                ],
                other_game_count=sum(r.tally.games for r in other),
                other_win_count=sum(r.tally.wins for r in other),
            )
        )
    generals.sort(key=lambda gb: -gb.total_games)
    return OpeningBook(
        computed_at=computed_at, min_games=MIN_GAMES_FOR_OPENING, generals=generals
    )


def opening_book_stat_rows(book: OpeningBook) -> list[Statistic]:
    """Encode as computed_statistics rows, one per general (JSON in `value`).

    A richer blob than the usual single-float Statistic row, but it reuses the
    same table and the same clear+save cycle as everything else recompute
    writes - no migration, and it never goes stale independently of the rest.
    """
    return [
        Statistic(
            stat_name=f"{OPENING_STAT_PREFIX}{gb.general.name}",
            date_computed=book.computed_at,
            value=gb.model_dump_json(by_alias=True),
            player=str(int(gb.general)),
        )
        for gb in book.generals
    ]


def opening_book_from_computed(stats: list[Statistic]) -> OpeningBook:
    """Decode `__opening_book_*` rows back into an OpeningBook (mirrors
    general_stats.value_stats_from_computed)."""
    generals: list[GeneralOpeningBook] = []
    computed_at: date | None = None
    for s in stats:
        if not s.stat_name.startswith(OPENING_STAT_PREFIX) or not isinstance(
            s.value, str
        ):
            continue
        try:
            generals.append(GeneralOpeningBook.model_validate_json(s.value))
        except ValidationError:
            # A schema change between when this row was written and now - skip
            # it rather than break the whole page over one stale general.
            logger.warning("failed to decode opening book row", stat_name=s.stat_name)
            continue
        computed_at = s.date_computed
    generals.sort(key=lambda gb: -gb.total_games)
    return OpeningBook(
        computed_at=computed_at or date.today(),
        min_games=MIN_GAMES_FOR_OPENING,
        generals=generals,
    )
