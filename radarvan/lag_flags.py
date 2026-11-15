"""Score a match's `NetstatsSummary` into the potato (stutter) and poor-connection flags."""

from __future__ import annotations

import os
from collections.abc import Callable
from operator import attrgetter
from typing import NamedTuple

from .api_types import LagFlag, MatchLagFlags, NetstatsSummary, RosterSlot
from .player_ids import resolve_player_name


class Thresholds(NamedTuple):
    min_ms: int
    min_ms_per_min: float
    min_share: float
    min_lead: float

    @classmethod
    def from_env(cls, prefix: str, defaults: Thresholds) -> Thresholds:
        def get(name: str, default: float) -> float:
            return float(os.environ.get(f"{prefix}_{name}", default))

        return cls(
            min_ms=int(get("MIN_MS", defaults.min_ms)),
            min_ms_per_min=get("MIN_MS_PER_MIN", defaults.min_ms_per_min),
            min_share=get("MIN_SHARE", defaults.min_share),
            min_lead=get("MIN_LEAD", defaults.min_lead),
        )


POTATO_DEFAULTS = Thresholds(
    min_ms=30_000, min_ms_per_min=3000, min_share=0.5, min_lead=2.0
)
CONNECTION_DEFAULTS = Thresholds(
    min_ms=5000, min_ms_per_min=500, min_share=0.5, min_lead=2.0
)
# Short stalls point at a PC that can't hold 60 fps; long freezes at a connection.
POTATO = Thresholds.from_env("POTATO", POTATO_DEFAULTS)
CONNECTION = Thresholds.from_env("CONNECTION", CONNECTION_DEFAULTS)


def find_flag(
    roster: list[RosterSlot],
    ms: Callable[[RosterSlot], int],
    count: Callable[[RosterSlot], int],
    duration_minutes: float,
    thresholds: Thresholds,
) -> LagFlag | None:
    """The one slot that clearly caused this kind of waiting, or None if shared or minor."""
    ranked = sorted((r for r in roster if r.views), key=ms, reverse=True)
    # A lone log can't be outvoted, and it may be the culprit's own.
    if not ranked or sum(r.has_logs for r in roster) < 2:
        return None
    if ranked[0].views < min(2, len(roster) - 1):
        return None
    worst = ms(ranked[0])
    runner_up = ms(ranked[1]) if len(ranked) > 1 else 0
    total = sum(ms(r) for r in ranked)
    if (
        worst < thresholds.min_ms
        or worst < thresholds.min_ms_per_min * max(duration_minutes, 1.0)
        or worst < thresholds.min_share * total
        or worst < thresholds.min_lead * runner_up
    ):
        return None
    return LagFlag(
        name=resolve_player_name(ranked[0].name),
        count=count(ranked[0]),
        wait_ms=worst,
        share=worst / total,
    )


def lag_flags(
    summary: NetstatsSummary,
    duration_minutes: float,
    potato: Thresholds = POTATO,
    connection: Thresholds = CONNECTION,
) -> MatchLagFlags:
    return MatchLagFlags(
        potato=find_flag(
            summary.roster,
            attrgetter("stall_ms"),
            attrgetter("stalls"),
            duration_minutes,
            potato,
        ),
        connection=find_flag(
            summary.roster,
            attrgetter("freeze_ms"),
            attrgetter("freezes"),
            duration_minutes,
            connection,
        ),
    )
