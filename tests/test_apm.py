"""Tests for radarvan.apm.

Covers the pure `is_action` / `is_active_action` predicates and the two APM
derivation paths (`apms_from_replay` / `apm_over_time`):

  * the legacy per-order *body* stream, and
  * the newer player-initiated *stats* events used when `body` is empty.

No committed replay fixture round-trips through the current `EnhancedReplayV2`
schema (the checked-in `tests/*.json` are the older PascalCase v1 shape), so
minimal replays are assembled directly from the model classes. Only the fields
the APM code actually reads are populated; `model_construct` skips the dozens of
unrelated required fields without running validation.
"""

from radarvan import apm
from radarvan.cncstats_model.body import BodyChunk
from radarvan.cncstats_model.header import GeneralsHeader, Metadata
from radarvan.cncstats_model.header import Player as HeaderPlayer
from radarvan.cncstats_model.zhreplay import (
    EnhancedReplayV2,
    EnrichedBuildEvent,
    EnrichedStats,
    PlayerSummaryV2,
)


# 1800 frames over 10 minutes -> 1/180 minute per frame; chosen so the math in
# the assertions stays exact.
FRAME_COUNT = 1800
DURATION_MINUTES = 10.0
MINUTES_PER_FRAME = DURATION_MINUTES / FRAME_COUNT


def _header(players: list[HeaderPlayer]) -> GeneralsHeader:
    metadata = Metadata.model_construct(players=players)
    return GeneralsHeader.model_construct(
        frame_count=FRAME_COUNT,
        time_stamp_begin=0,
        time_stamp_end=int(DURATION_MINUTES * 60),
        metadata=metadata,
    )


def _header_player(name: str, team: int, ptype: str) -> HeaderPlayer:
    return HeaderPlayer.model_construct(name=name, team=str(team), type=ptype)


def _chunk(name: str, order: str, time_code: int) -> BodyChunk:
    return BodyChunk.model_construct(
        player_name=name, order_name=order, time_code=time_code
    )


def _summary(name: str, index: int, team: int, ptype: str) -> PlayerSummaryV2:
    return PlayerSummaryV2.model_construct(
        name=name, index=index, team=team, player_type=ptype
    )


def _build(frame: int, player: int) -> EnrichedBuildEvent:
    return EnrichedBuildEvent.model_construct(frame=frame, player=player)


def _stats(build_events: list[EnrichedBuildEvent]) -> EnrichedStats:
    return EnrichedStats.model_construct(
        build_events=build_events,
        capture_events=[],
        battle_plan_events=[],
        science_points_events=[],
    )


# --- pure predicates -------------------------------------------------------


def test_is_action_true_for_normal_orders() -> None:
    assert apm.is_action("BuildObject") is True
    assert apm.is_action("MoveTo") is True
    assert apm.is_action("AttackObject") is True


def test_is_action_false_for_non_actions_and_unknown() -> None:
    assert apm.is_action("Checksum") is False
    assert apm.is_action("SelectBox") is False
    assert apm.is_action("ClearSelection") is False
    assert apm.is_action("EndReplay") is False
    # Anything cncstats couldn't name is excluded.
    assert apm.is_action("Unknown_42") is False


def test_is_active_action() -> None:
    assert apm.is_active_action("BuildObject") is True
    assert apm.is_active_action("MoveTo") is True
    # An action, but not a movement/build "active" action.
    assert apm.is_active_action("Checksum") is False
    assert apm.is_active_action("SelectBox") is False


# --- body path -------------------------------------------------------------


def _body_replay() -> EnhancedReplayV2:
    players = [
        _header_player("P1", 1, "H"),
        _header_player("P2", 2, "H"),
        _header_player("CPU", 1, "C"),  # computer: excluded
        _header_player("Obs", -1, "H"),  # observer (team < 0): excluded
    ]
    body = [
        # P1: three counted actions (all "active") spanning frames 100..300.
        _chunk("P1", "CreateUnit", 100),
        _chunk("P1", "MoveTo", 200),
        _chunk("P1", "BuildObject", 300),
        # ...plus two that must not count toward actions.
        _chunk("P1", "Checksum", 310),
        _chunk("P1", "Unknown_7", 320),
        # P2: a single action.
        _chunk("P2", "MoveTo", 150),
        # CPU / observer actions must be ignored entirely.
        _chunk("CPU", "MoveTo", 160),
        _chunk("Obs", "MoveTo", 170),
    ]
    return EnhancedReplayV2.model_construct(
        body=body, header=_header(players), summary=[], stats=None
    )


def test_body_apms_counts_and_excludes() -> None:
    by_name = {a.player_name: a for a in apm.apms_from_replay(_body_replay())}
    # Only tracked humans appear; CPU and observer are absent.
    assert set(by_name) == {"P1", "P2"}

    p1 = by_name["P1"]
    assert p1.action_count == 3  # Checksum + Unknown excluded
    # Active span is first->last active-action frame: (300 - 100) frames.
    assert p1.minutes == (300 - 100) * MINUTES_PER_FRAME
    assert p1.apm == p1.action_count / p1.minutes

    # P2 has a single action, so its active span collapses; the body path uses
    # a 0-minute fallback and reports 0 APM rather than an absurd value.
    p2 = by_name["P2"]
    assert p2.action_count == 1
    assert p2.apm == 0.0


def test_body_apm_values_non_negative() -> None:
    for a in apm.apms_from_replay(_body_replay()):
        assert a.action_count >= 0
        assert a.minutes >= 0.0
        assert a.apm >= 0.0


def test_body_apm_over_time_shape_and_invariants() -> None:
    series = apm.apm_over_time(_body_replay())
    assert isinstance(series, dict)
    assert series  # non-empty

    # Keyed by window-start minute (float), values are {player: rate}.
    for minute, per_player in series.items():
        assert isinstance(minute, float)
        assert set(per_player) == {"P1", "P2"}
        assert all(rate >= 0.0 for rate in per_player.values())

    # Each value is a per-minute rate (count / window_minutes). Summing the
    # rates and multiplying back by the window width recovers the action count.
    window_minutes = apm._APM_WINDOW_MINUTES
    p1_total = sum(per_player["P1"] for per_player in series.values()) * window_minutes
    assert round(p1_total) == 3


# --- stats path (empty body) ----------------------------------------------


def _stats_replay() -> EnhancedReplayV2:
    summary = [
        _summary("P1", 1, 1, "Human"),
        _summary("P2", 2, 2, "Human"),
        _summary("CPU", 3, 1, "Computer"),  # excluded: not Human
        _summary("Obs", 4, -1, "Human"),  # excluded: team < 0
    ]
    stats = _stats(
        [
            _build(100, 1),  # P1
            _build(200, 1),  # P1
            _build(150, 2),  # P2
            _build(160, 3),  # CPU -> ignored
            _build(170, 4),  # Obs -> ignored
        ]
    )
    players = [_header_player("P1", 1, "H"), _header_player("P2", 2, "H")]
    return EnhancedReplayV2.model_construct(
        body=[], header=_header(players), summary=summary, stats=stats
    )


def test_stats_apms_counts_and_excludes() -> None:
    by_name = {a.player_name: a for a in apm.apms_from_replay(_stats_replay())}
    assert set(by_name) == {"P1", "P2"}

    p1 = by_name["P1"]
    assert p1.action_count == 2  # two builds; CPU/observer builds ignored
    assert p1.minutes == (200 - 100) * MINUTES_PER_FRAME
    assert p1.apm == p1.action_count / p1.minutes

    # P2's single build collapses its span; the stats path falls back to the
    # full game duration as the denominator (not 0), so APM stays finite.
    p2 = by_name["P2"]
    assert p2.action_count == 1
    assert p2.minutes == DURATION_MINUTES
    assert p2.apm == 1 / DURATION_MINUTES


def test_stats_apm_over_time_shape() -> None:
    series = apm.apm_over_time(_stats_replay())
    assert isinstance(series, dict)
    assert series
    names = set().union(*(set(v) for v in series.values()))
    assert names == {"P1", "P2"}
    for per_player in series.values():
        assert all(rate >= 0.0 for rate in per_player.values())


def test_no_tracked_players_returns_empty() -> None:
    # Stats path with only excluded players yields no series and no records.
    summary = [_summary("Obs", 1, -1, "Human"), _summary("CPU", 2, 1, "Computer")]
    replay = EnhancedReplayV2.model_construct(
        body=[],
        header=_header([]),
        summary=summary,
        stats=_stats([_build(100, 1), _build(200, 2)]),
    )
    assert apm.apm_over_time(replay) == {}
    assert apm.apms_from_replay(replay) == []
