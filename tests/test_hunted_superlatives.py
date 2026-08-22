"""The hunted superlatives and the `time_to_hunted` milestone behind them.

"Hunted" is the engine state a player enters when they have no dozer or worker
left and no way to produce one. cncstats reports it as `stats.huntedEvents`
(statsVersion 3); `milestone_timings_from_replay` reduces the stream to each
player's *first* hunted flip, and `get_hunted_stats` counts those per player
across the corpus.
"""

from datetime import date

import pytest

from radarvan.api_types import SuperlativeData
from radarvan.cncstats_model.header import GeneralsHeader, Metadata
from radarvan.cncstats_model.statsfile import (
    HuntedEvent,
    TimeSeries,
)
from radarvan.cncstats_model.zhreplay import (
    EnhancedReplayV2,
    EnrichedStats,
    PlayerSummaryV2,
)
from radarvan.stats_extraction import milestone_timings_from_replay
from radarvan.superlatives import get_hunted_stats

from corpus import COLORS, match

COMPUTED_AT = date(2026, 2, 1)

# frame_count/duration chosen so minutes_per_step is exactly 1/60: one frame is
# one second, so frame 60 lands on minute 1.0.
_FRAME_COUNT = 600
_DURATION_MINUTES = 10.0


# --- milestone extraction --------------------------------------------------


def _replay(events: list[HuntedEvent] | None) -> EnhancedReplayV2:
    stats = EnrichedStats.model_construct(
        battle_plan_events=[],
        build_events=[],
        capture_events=[],
        death_events=[],
        energy_events=[],
        hunted_events=events,
        kill_events=[],
        radar_events=[],
        rank_events=[],
        science_points_events=[],
        skill_points_events=[],
        time_series=TimeSeries.model_construct(players=[]),
    )
    header = GeneralsHeader.model_construct(
        frame_count=_FRAME_COUNT,
        time_stamp_begin=0,
        time_stamp_end=int(_DURATION_MINUTES * 60),
        metadata=Metadata.model_construct(players=[]),
    )
    return EnhancedReplayV2.model_construct(
        header=header,
        body=[],
        summary=[
            PlayerSummaryV2.model_construct(name="Skip", index=1),
            PlayerSummaryV2.model_construct(name="Syn", index=2),
        ],
        stats=stats,
    )


def _time_to_hunted(events: list[HuntedEvent] | None) -> dict[str, float]:
    replay = _replay(events)
    name_by_idx = {p.index: p.name for p in replay.summary}
    return milestone_timings_from_replay(replay, name_by_idx).time_to_hunted


def test_absent_hunted_stream_has_no_milestones() -> None:
    """Replays predating statsVersion 3 parse with `hunted_events` None; the
    milestone pass must read that as "nobody went hunted" rather than raise."""
    assert _time_to_hunted(None) == {}


def test_time_to_hunted_records_the_minute_per_player() -> None:
    result = _time_to_hunted(
        [
            HuntedEvent(frame=60, player=1, hunted=True),
            HuntedEvent(frame=180, player=2, hunted=True),
        ]
    )
    assert result == {"Skip": pytest.approx(1.0), "Syn": pytest.approx(3.0)}


def test_time_to_hunted_keeps_the_earliest_flip() -> None:
    """A player who rebuilds a dozer and is hunted again keeps the first time."""
    result = _time_to_hunted(
        [
            HuntedEvent(frame=60, player=1, hunted=True),
            HuntedEvent(frame=120, player=1, hunted=False),
            HuntedEvent(frame=300, player=1, hunted=True),
        ]
    )
    assert result == {"Skip": pytest.approx(1.0)}


def test_time_to_hunted_is_frame_ordered_not_stream_ordered() -> None:
    """The earliest flip wins even when the stream arrives out of order."""
    result = _time_to_hunted(
        [
            HuntedEvent(frame=300, player=1, hunted=True),
            HuntedEvent(frame=60, player=1, hunted=True),
        ]
    )
    assert result == {"Skip": pytest.approx(1.0)}


def test_unhunted_events_alone_produce_no_milestone() -> None:
    assert _time_to_hunted([HuntedEvent(frame=60, player=1, hunted=False)]) == {}


def test_seed_frame_hunted_event_is_ignored() -> None:
    assert _time_to_hunted([HuntedEvent(frame=0, player=1, hunted=True)]) == {}


def test_time_to_hunted_empty_without_stats() -> None:
    """Old replays have `stats=None` entirely - the guard must hold."""
    replay = _replay([]).model_copy(update={"stats": None})
    assert milestone_timings_from_replay(replay, {}).time_to_hunted == {}


# --- superlatives ----------------------------------------------------------


def _details(match_id: int, hunted: dict[str, float]) -> SuperlativeData:
    return SuperlativeData.model_construct(
        match_id=match_id,
        apms=[],
        player_summary=[],
        upgrade_counts={},
        total_units_killed=0,
        total_buildings_killed=0,
        total_xp=0,
        match_money_spent=0,
        player_money_collected={},
        time_to_hunted=hunted,
    )


def _stat(stats: list, name: str):
    return next((s for s in stats if s.stat_name == name), None)


def test_most_hunted_counts_matches_per_player() -> None:
    games = [match(1, day=5), match(2, day=6), match(3, day=7)]
    details = [
        _details(1, {"Skip": 1.0, "Syn": 2.0}),
        _details(2, {"Skip": 3.0}),
        _details(3, {"Skip": 4.0, "Pancake": 5.0}),
    ]
    stats = get_hunted_stats({g.id: g for g in games}, details, COMPUTED_AT)

    top = _stat(stats, "🚜 Most Hunted")
    assert top is not None
    # Skip in all three matches, Syn and Pancake in one each - no tie to break.
    assert top.player == "Skip"
    assert top.value == 3


def test_hunted_stats_empty_when_nothing_is_hunted() -> None:
    games = [match(1, day=5)]
    assert get_hunted_stats({g.id: g for g in games}, [_details(1, {})], COMPUTED_AT) == []


def test_hunted_player_names_are_alias_resolved() -> None:
    """Clients see the canonical name, not the in-game alias."""
    games = [match(1, day=5)]
    # "skp" is an alias for "Skip"; give it Skip's real color so the
    # color-disambiguated resolve path is the one exercised.
    skip_color = next(p.color for p in games[0].players if p.name == "Skip")
    game = games[0].model_copy(
        update={
            "players": [
                p.model_copy(update={"name": "skp"}) if p.name == "Skip" else p
                for p in games[0].players
            ]
        }
    )
    assert skip_color in COLORS
    stats = get_hunted_stats({game.id: game}, [_details(1, {"skp": 1.0})], COMPUTED_AT)

    top = _stat(stats, "🚜 Most Hunted")
    assert top is not None
    assert top.player == "Skip"


def test_hunted_row_without_a_match_info_still_counts_the_player() -> None:
    """A details row whose match isn't in the corpus has no roster to read a
    color from - the name still resolves and the player count must survive it."""
    stats = get_hunted_stats({}, [_details(999, {"Skip": 1.0})], COMPUTED_AT)

    top = _stat(stats, "🚜 Most Hunted")
    assert top is not None
    assert top.player == "Skip"


def test_a_cpu_never_holds_the_hunted_record() -> None:
    """Eligibility is a membership test against the known humans, so an AI slot
    is dropped whatever it is called - "Tactical AI" held "Worst Record (30d)"
    while the check was a one-name blocklist of "HardArmy"."""
    games = [match(1, day=5), match(2, day=6)]
    details = [
        _details(1, {"Tactical AI": 1.0, "Skip": 2.0}),
        _details(2, {"Tactical AI": 3.0}),
    ]
    stats = get_hunted_stats({g.id: g for g in games}, details, COMPUTED_AT)

    top = _stat(stats, "🚜 Most Hunted")
    assert top is not None
    # The AI went hunted twice to Skip's once and still must not take it.
    assert top.player == "Skip"
