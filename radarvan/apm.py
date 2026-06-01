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

from .api_types import APM
from .cncstats_model.zhreplay import EnhancedReplayV2
from .utils import minutess_per_step


def is_action(order_name: str) -> bool:
    match order_name:
        case (
            "Chunksum" | "DeclareUserId" | "EndReplay" | "SelectBox" | "ClearSelection"
        ):
            return False
        case _ if order_name.startswith("Unknown"):
            return False
        case _:
            return True


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


def _apms_from_body(replay: EnhancedReplayV2) -> list[APM]:
    players = replay.header.metadata.players
    action_counts = {p.name: 0 for p in players if int(p.team) >= 0 and p.type != "C"}
    player_first_active = {p.name: -1 for p in players if int(p.team) >= 0}
    player_last_active = {p.name: 0 for p in players if int(p.team) >= 0}

    for chunk in replay.body:
        if chunk.player_name not in action_counts:
            continue
        if is_action(chunk.order_name):
            action_counts[chunk.player_name] += 1
        if is_active_action(chunk.order_name):
            player_last_active[chunk.player_name] = chunk.time_code
            if player_first_active[chunk.player_name] < 0:
                player_first_active[chunk.player_name] = chunk.time_code

    minutes_per = minutess_per_step(replay)
    player_minutes = {
        name: (player_last_active[name] - first) * minutes_per
        for name, first in player_first_active.items()
    }
    return [
        APM(
            player_name=name,
            action_count=count,
            minutes=player_minutes[name],
            apm=count / player_minutes[name] if player_minutes[name] > 0 else 0.0,
        )
        for name, count in action_counts.items()
    ]


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
        if name not in first_frame or frame < first_frame[name]:
            first_frame[name] = frame
        if name not in last_frame or frame > last_frame[name]:
            last_frame[name] = frame

    minutes_per = minutess_per_step(replay)
    total_minutes = (replay.header.frame_count or 1) * minutes_per
    result: list[APM] = []
    for name, count in counts.items():
        if count == 0:
            result.append(APM(player_name=name, action_count=0, minutes=0.0, apm=0.0))
            continue
        active_frames = last_frame[name] - first_frame[name]
        active_minutes = active_frames * minutes_per
        if active_minutes <= 0:
            active_minutes = total_minutes
        result.append(
            APM(
                player_name=name,
                action_count=count,
                minutes=active_minutes,
                apm=count / active_minutes,
            )
        )
    return result


def apms_from_replay(replay: EnhancedReplayV2) -> list[APM]:
    """Overall match APM per player.

    Prefers the per-order body stream when present (legacy replays); falls
    back to player-initiated stats events for newer replays where the body
    is empty.
    """
    if replay.body:
        return _apms_from_body(replay)
    return _apms_from_stats(replay)


def _apm_over_time_from_body(
    replay: EnhancedReplayV2,
) -> dict[float, dict[str, float]]:
    players = replay.header.metadata.players
    tracked = {p.name for p in players if int(p.team) >= 0 and p.type != "C"}
    if not tracked:
        return {}
    minutes_per = minutess_per_step(replay)
    counts: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    max_minute = 0
    for chunk in replay.body:
        if chunk.player_name not in tracked:
            continue
        if not is_action(chunk.order_name):
            continue
        minute = int(chunk.time_code * minutes_per)
        counts[minute][chunk.player_name] += 1
        if minute > max_minute:
            max_minute = minute
    return _fill_minute_series(counts, max_minute, tracked)


def _apm_over_time_from_stats(
    replay: EnhancedReplayV2,
) -> dict[float, dict[str, float]]:
    tracked = _tracked_humans(replay)
    if not tracked:
        return {}
    names = set(tracked.values())
    minutes_per = minutess_per_step(replay)
    counts: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    max_minute = 0
    for frame, idx in _stats_action_events(replay):
        name = tracked.get(idx)
        if name is None:
            continue
        minute = int(frame * minutes_per)
        counts[minute][name] += 1
        if minute > max_minute:
            max_minute = minute
    return _fill_minute_series(counts, max_minute, names)


def _fill_minute_series(
    counts: dict[int, dict[str, int]], max_minute: int, names: set[str]
) -> dict[float, dict[str, float]]:
    result: dict[float, dict[str, float]] = {}
    for minute in range(max_minute + 1):
        bucket = counts.get(minute, {})
        result[float(minute)] = {name: float(bucket.get(name, 0)) for name in names}
    return result


def apm_over_time(replay: EnhancedReplayV2) -> dict[float, dict[str, float]]:
    """Per-minute windowed APM time series, shaped as {minute: {player: apm}}.

    Each bucket spans one minute of real (post-scaling) game time, so the
    action count in the bucket equals APM. Empty buckets are filled with 0
    for each tracked player so chart lines stay continuous.
    """
    if replay.body:
        return _apm_over_time_from_body(replay)
    return _apm_over_time_from_stats(replay)
