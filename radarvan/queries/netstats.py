"""Lag flags for one night's matches, from the stored netstats summaries."""

from __future__ import annotations

from datetime import date

from ..api_types import MatchLagFlags
from ..cache import sorted_deduped_matches
from ..db_utils import ReplayManager
from ..lag_flags import lag_flags
from ..repositories import NetstatsRepo


def lag_flags_on(
    night: date, replay_manager: ReplayManager, netstats: NetstatsRepo
) -> dict[int, MatchLagFlags]:
    durations = {
        m.id: m.duration_minutes
        for m in sorted_deduped_matches(replay_manager).values()
        if m.date == night
    }
    flags = {
        match_id: lag_flags(summary, durations[match_id])
        for match_id, summary in netstats.get_summaries(durations).items()
    }
    return {m: f for m, f in flags.items() if f.potato or f.connection}
