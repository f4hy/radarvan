"""Game-length distribution over a corpus of matches.

Pure: takes the games, returns the histogram plus order statistics. The
corpus selection (competitive vs all, format filter) is the caller's - see
``queries/games.py`` - so the same function serves the route, a test, and any
future per-map or per-player breakdown without disagreeing about which games
counted.

The top bucket is an overflow bin on purpose. Durations are long-tailed: a
handful of four-hour sessions would otherwise stretch the axis until every
real game sat in the first two bars.
"""

from __future__ import annotations

import math
from collections import defaultdict

from .api_types import (
    DurationBucket,
    DurationDistribution,
    DurationStats,
    MatchInfo,
)

# Two-minute bars over the first two hours is the shape that actually reads:
# fine enough to show the rush/macro split, coarse enough that a game night's
# worth of matches isn't one game per bar.
DEFAULT_BUCKET_MINUTES = 2.0
DEFAULT_MAX_MINUTES = 60.0

# A match whose parsed duration is at or below this is a mis-parse or an
# instant quit, not a game anybody played; counting them puts a spike in the
# first bar that swamps the real distribution.
MIN_REAL_MINUTES = 0.5


def _percentile(ordered: list[float], fraction: float) -> float | None:
    """Linear-interpolated percentile of an already-sorted list."""
    if not ordered:
        return None
    if len(ordered) == 1:
        return ordered[0]
    position = fraction * (len(ordered) - 1)
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def summarize(durations: list[float]) -> DurationStats:
    """Order statistics for one set of game lengths."""
    ordered = sorted(durations)
    return DurationStats(
        count=len(ordered),
        total_minutes=sum(ordered),
        mean_minutes=(sum(ordered) / len(ordered)) if ordered else None,
        median_minutes=_percentile(ordered, 0.5),
        p10_minutes=_percentile(ordered, 0.1),
        p90_minutes=_percentile(ordered, 0.9),
        shortest_minutes=ordered[0] if ordered else None,
        longest_minutes=ordered[-1] if ordered else None,
    )


def playable_durations(games: list[MatchInfo]) -> list[float]:
    """The durations worth charting, dropping mis-parses (see MIN_REAL_MINUTES)."""
    return [g.duration_minutes for g in games if g.duration_minutes > MIN_REAL_MINUTES]


def bucket_durations(
    durations: list[float],
    bucket_minutes: float = DEFAULT_BUCKET_MINUTES,
    max_minutes: float = DEFAULT_MAX_MINUTES,
) -> list[DurationBucket]:
    """Histogram bars, including empty ones, with an overflow bin on the end.

    Empty buckets are returned rather than skipped so the client can draw a
    continuous axis without reconstructing the missing bars itself.
    """
    bar_count = max(1, math.ceil(max_minutes / bucket_minutes))
    counts = [0] * bar_count
    overflow = 0
    for value in durations:
        index = int(value // bucket_minutes)
        if index >= bar_count:
            overflow += 1
        else:
            counts[index] += 1
    buckets = [
        DurationBucket(
            start_minutes=i * bucket_minutes,
            end_minutes=(i + 1) * bucket_minutes,
            count=count,
        )
        for i, count in enumerate(counts)
    ]
    buckets.append(
        DurationBucket(
            start_minutes=bar_count * bucket_minutes,
            end_minutes=None,
            count=overflow,
        )
    )
    return buckets


def _format_of(game: MatchInfo) -> str:
    composition = game.composition
    if composition is None:
        return "Unknown"
    if composition.is_ffa:
        return "FFA"
    return composition.category


def duration_distribution(
    games: list[MatchInfo],
    bucket_minutes: float = DEFAULT_BUCKET_MINUTES,
    max_minutes: float = DEFAULT_MAX_MINUTES,
) -> DurationDistribution:
    """Histogram + summary stats for ``games``, overall and per format."""
    by_format: dict[str, list[float]] = defaultdict(list)
    for game in games:
        if game.duration_minutes > MIN_REAL_MINUTES:
            by_format[_format_of(game)].append(game.duration_minutes)
    durations = [value for values in by_format.values() for value in values]
    return DurationDistribution(
        bucket_minutes=bucket_minutes,
        buckets=bucket_durations(durations, bucket_minutes, max_minutes),
        stats=summarize(durations),
        # Most-played format first, so the client's legend order is stable and
        # meaningful rather than dictionary order.
        by_format={
            fmt: summarize(values)
            for fmt, values in sorted(by_format.items(), key=lambda kv: -len(kv[1]))
        },
    )
