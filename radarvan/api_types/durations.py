"""Game-length distribution: how long our games actually run.

A histogram plus the order statistics that go with it, computed over a corpus
the route selects (see ``queries/games.py``). Buckets are returned already
counted rather than as raw durations - the whole corpus is thousands of
matches and the client only ever draws the bars.
"""

# See radarvan/api_types/__init__.py for why this package is split by context.
# Needed so forward/self references resolve under Python < 3.14 (PEP 649 defers
# by default on 3.14+); required for the ml/ 3.13 training venv.
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class DurationBucket(BaseModel):
    """One histogram bar: games whose duration is in [start, end) minutes.

    The final bucket is the overflow bin and is half-open the other way -
    ``end_minutes`` is null and it holds everything at or beyond ``start``, so
    one four-hour marathon widens the tail label instead of the whole axis.
    """

    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    start_minutes: float = Field(alias="startMinutes")
    end_minutes: float | None = Field(default=None, alias="endMinutes")
    count: int


class DurationStats(BaseModel):
    """Order statistics for one set of game lengths, all in minutes."""

    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    count: int
    total_minutes: float = Field(alias="totalMinutes")
    mean_minutes: float | None = Field(default=None, alias="meanMinutes")
    median_minutes: float | None = Field(default=None, alias="medianMinutes")
    p10_minutes: float | None = Field(default=None, alias="p10Minutes")
    p90_minutes: float | None = Field(default=None, alias="p90Minutes")
    shortest_minutes: float | None = Field(default=None, alias="shortestMinutes")
    longest_minutes: float | None = Field(default=None, alias="longestMinutes")


class DurationDistribution(BaseModel):
    """The histogram, its summary stats, and the same stats per game format.

    ``by_format`` is computed over whatever corpus reached the route, so it
    collapses to a single entry when the caller passed ``game_format``.
    """

    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    bucket_minutes: float = Field(alias="bucketMinutes")
    buckets: list[DurationBucket] = Field(default_factory=list)
    stats: DurationStats
    by_format: dict[str, DurationStats] = Field(default_factory=dict, alias="byFormat")
