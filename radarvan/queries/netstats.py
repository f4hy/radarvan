"""Lag flags and the night-level netstats rollup, from the stored netstats summaries."""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from ..api_types import (
    MatchInfo,
    MatchLagFlags,
    NetstatsSummary,
    NightNetstats,
    NightNetstatsPlayer,
)
from ..cache import sorted_deduped_matches
from ..db_utils import ReplayManager
from ..lag_flags import lag_flags
from ..player_ids import resolve_player_name
from ..repositories import NetstatsRepo
from .game_night import on_night


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


def night_netstats(
    night: date, games: list[MatchInfo], netstats: NetstatsRepo
) -> NightNetstats:
    tonight = {m.id: m for m in on_night(games, night)}
    return roll_up(tonight, netstats.get_summaries(tonight))


def roll_up(
    tonight: dict[int, MatchInfo], summaries: dict[int, NetstatsSummary]
) -> NightNetstats:
    totals: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for match_id, summary in summaries.items():
        flags = lag_flags(summary, tonight[match_id].duration_minutes)
        if flags.connection:
            totals[flags.connection.name]["connection_flags"] += 1
        if flags.potato:
            totals[flags.potato.name]["potato_flags"] += 1
        # views == 0: no other log could see this slot, so no reading either way.
        for slot in (r for r in summary.roster if r.views):
            row = totals[resolve_player_name(slot.name)]
            row["games"] += 1
            row["freezes"] += slot.freezes
            row["freeze_ms"] += slot.freeze_ms
            row["stalls"] += slot.stalls
            row["stall_ms"] += slot.stall_ms
    players = sorted(
        (
            NightNetstatsPlayer(
                name=name,
                games=row["games"],
                freezes=row["freezes"],
                freeze_ms=row["freeze_ms"],
                stalls=row["stalls"],
                stall_ms=row["stall_ms"],
                connection_flags=row["connection_flags"],
                potato_flags=row["potato_flags"],
            )
            for name, row in totals.items()
            if row["games"]
        ),
        key=lambda p: (-(p.freeze_ms + p.stall_ms), p.name),
    )
    return NightNetstats(
        match_count=len(tonight),
        logged_matches=len(summaries),
        logged_minutes=sum(tonight[m].duration_minutes for m in summaries),
        freeze_ms=sum(p.freeze_ms for p in players),
        stall_ms=sum(p.stall_ms for p in players),
        players=players,
    )
