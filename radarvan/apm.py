"""APM (actions per minute) calculations.

Provides both the per-match overall APM (`apms_from_replay`) and a per-minute
windowed time series (`apm_over_time`) for charting APM through the match.

Newer replays from cncstats no longer ship a per-order body stream — `replay.body`
is empty. For those, APM is derived from the player-initiated events recorded in
`replay.stats` (builds, captures, battle plans, science purchases). When `body`
is populated (older format), the original order-stream logic is used.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from .api_types import APM
from .cncstats_model.zhreplay import EnhancedReplayV2
from .utils import minutess_per_step


_NON_ACTIONS = {
    "Chunksum",
    "DeclareUserId",
    "EndReplay",
    "SelectBox",
    "ClearSelection",
}


def is_action(order_name: str) -> bool:
    return order_name not in _NON_ACTIONS and not order_name.startswith("Unknown")


ACTIVE_ACTIONS = {
    "AttackMove",
    "AttackObject",
    "BuildObject",
    "BuildUpgrade",
    "CreateUnit",
    "MoveTo",
    "ForceAttackObjectGuard",
    "FlamewallRocketPodContaminate",
    "Sell",
}


def is_active_action(order_name: str) -> bool:
    return order_name in ACTIVE_ACTIONS


def _tracked_humans(replay: EnhancedReplayV2) -> dict[int, str]:
    """Map summary player index → player name, for non-observer humans."""
    return {
        p.index: p.name
        for p in replay.summary
        if p.team >= 0 and p.player_type == "Human"
    }


def _stats_action_events(replay: EnhancedReplayV2) -> list[tuple[int, int]]:
    """List of (frame, player_index) for every player-initiated stats event.

    Counts builds, captures (by the new owner), battle-plan switches, and
    science purchases as discrete actions. Excludes passive events (rank ups,
    skill points from kills, radar, energy, deaths) since they aren't actions
    the player took at that moment.
    """
    if replay.stats is None:
        return []
    events: list[tuple[int, int]] = []
    events.extend((ev.frame, ev.player) for ev in replay.stats.build_events)
    events.extend(
        (ev.frame, ev.new_owner)
        for ev in replay.stats.capture_events
        if ev.new_owner > 0
    )
    events.extend((ev.frame, ev.player) for ev in replay.stats.battle_plan_events)
    events.extend((ev.frame, ev.player) for ev in replay.stats.science_points_events)
    return events


def _build_apm_records(
    counts: dict[str, int],
    first_frame: dict[str, int],
    last_frame: dict[str, int],
    minutes_per: float,
    fallback_minutes: float = 0.0,
) -> list[APM]:
    """Construct APM records from per-player action counts and first/last frames.

    `fallback_minutes` is used when a player's first/last frame collapse
    (e.g. a single event) — set to total game duration for the stats path,
    0 for the body path (which then reports 0 APM rather than infinite).
    """
    result: list[APM] = []
    for name, count in counts.items():
        if count == 0:
            result.append(APM(player_name=name, action_count=0, minutes=0.0, apm=0.0))
            continue
        active = (last_frame.get(name, 0) - first_frame.get(name, 0)) * minutes_per
        if active <= 0:
            active = fallback_minutes
        result.append(
            APM(
                player_name=name,
                action_count=count,
                minutes=active,
                apm=count / active if active > 0 else 0.0,
            )
        )
    return result


def _apms_from_body(replay: EnhancedReplayV2) -> list[APM]:
    players = replay.header.metadata.players
    counts = {p.name: 0 for p in players if int(p.team) >= 0 and p.type != "C"}
    first_frame: dict[str, int] = {}
    last_frame: dict[str, int] = {}
    for chunk in replay.body:
        if chunk.player_name not in counts:
            continue
        if is_action(chunk.order_name):
            counts[chunk.player_name] += 1
        if is_active_action(chunk.order_name):
            last_frame[chunk.player_name] = chunk.time_code
            first_frame.setdefault(chunk.player_name, chunk.time_code)
    return _build_apm_records(counts, first_frame, last_frame, minutess_per_step(replay))


def _apms_from_stats(replay: EnhancedReplayV2) -> list[APM]:
    tracked = _tracked_humans(replay)
    if not tracked:
        return []
    counts: dict[str, int] = dict.fromkeys(tracked.values(), 0)
    first_frame: dict[str, int] = {}
    last_frame: dict[str, int] = {}
    for frame, idx in _stats_action_events(replay):
        name = tracked.get(idx)
        if name is None:
            continue
        counts[name] += 1
        if frame < first_frame.get(name, frame + 1):
            first_frame[name] = frame
        if frame > last_frame.get(name, -1):
            last_frame[name] = frame
    minutes_per = minutess_per_step(replay)
    total_minutes = (replay.header.frame_count or 1) * minutes_per
    return _build_apm_records(
        counts, first_frame, last_frame, minutes_per, fallback_minutes=total_minutes
    )


def apms_from_replay(replay: EnhancedReplayV2) -> list[APM]:
    """Overall match APM per player.

    Prefers the per-order body stream when present (legacy replays); falls
    back to player-initiated stats events for newer replays where the body
    is empty.
    """
    if replay.body:
        return _apms_from_body(replay)
    return _apms_from_stats(replay)


def _bucket_apm_over_time(
    actions: Iterable[tuple[int, str]],
    tracked: set[str],
    minutes_per: float,
) -> dict[float, dict[str, float]]:
    """Bucket `(frame, player_name)` actions into per-minute APM windows."""
    counts: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    max_minute = 0
    for frame, name in actions:
        if name not in tracked:
            continue
        minute = int(frame * minutes_per)
        counts[minute][name] += 1
        if minute > max_minute:
            max_minute = minute
    result: dict[float, dict[str, float]] = {}
    for minute in range(max_minute + 1):
        bucket = counts.get(minute, {})
        result[float(minute)] = {name: float(bucket.get(name, 0)) for name in tracked}
    return result


def apm_over_time(replay: EnhancedReplayV2) -> dict[float, dict[str, float]]:
    """Per-minute windowed APM time series, shaped as {minute: {player: apm}}.

    Each bucket spans one minute of real (post-scaling) game time, so the
    action count in the bucket equals APM. Empty buckets are filled with 0
    for each tracked player so chart lines stay continuous.
    """
    minutes_per = minutess_per_step(replay)
    if replay.body:
        players = replay.header.metadata.players
        tracked = {p.name for p in players if int(p.team) >= 0 and p.type != "C"}
        if not tracked:
            return {}
        actions = (
            (chunk.time_code, chunk.player_name)
            for chunk in replay.body
            if chunk.player_name in tracked and is_action(chunk.order_name)
        )
        return _bucket_apm_over_time(actions, tracked, minutes_per)
    name_by_idx = _tracked_humans(replay)
    if not name_by_idx:
        return {}
    names = set(name_by_idx.values())
    actions = (
        (frame, name_by_idx[idx])
        for frame, idx in _stats_action_events(replay)
        if idx in name_by_idx
    )
    return _bucket_apm_over_time(actions, names, minutes_per)
