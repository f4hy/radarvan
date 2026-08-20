"""Name-cleaning helpers and timeline-event extraction.

The cleaning helpers (`radarvan.replay_helpers.clean_object_name` and
`radarvan.timeline_events.clean_power_name`) are pure functions and are always
exercised. The end-to-end `timeline_events_from_replay` test runs against the
real cncstats fixture `references/example_cncstats_output.json` when present and
is skipped otherwise (that directory is gitignored, so it is unavailable in a
fresh clone / CI).
"""

import json
from pathlib import Path

import pytest

from radarvan.api_types import TimelineEvent
from radarvan.cncstats_model.header import GeneralsHeader, Metadata
from radarvan.cncstats_model.statsfile import HuntedEvent, TimeSeries
from radarvan.cncstats_model.zhreplay import (
    EnhancedReplayV2,
    EnrichedStats,
    PlayerSummaryV2,
)
from radarvan.replay_helpers import clean_object_name
from radarvan.timeline_events import clean_power_name, timeline_events_from_replay

_FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "references"
    / "example_cncstats_output.json"
)


# --- clean_object_name -----------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        # Leading <Prefix>_ token stripped, then the faction prefix.
        ("Lazr_AmericaVehicleChinook", "VehicleChinook"),
        ("Tank_ChinaTankOverlord", "TankOverlord"),
        ("SupW_AmericaVehicleAuroraBomber", "VehicleAuroraBomber"),
        ("Chem_GLAVehicleScudLauncher", "VehicleScudLauncher"),
        # Prefix token without a trailing faction word: only the prefix drops.
        ("Upgrade_SomethingElse", "SomethingElse"),
        # No underscore: only the faction prefix is stripped.
        ("AmericaPowerPlant", "PowerPlant"),
        ("ChinaWarFactory", "WarFactory"),
        ("GLACommandCenter", "CommandCenter"),
        # Neither a prefix token nor a faction word: unchanged.
        ("PlainName", "PlainName"),
    ],
)
def test_clean_object_name(raw: str, expected: str) -> None:
    assert clean_object_name(raw) == expected


# --- clean_power_name -----------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        # Power-tag prefix stripped on top of the object cleaning.
        ("SpecialPowerSpyDrone", "SpyDrone"),
        ("SpecialAbilityCaptureBuilding", "CaptureBuilding"),
        ("SuperweaponParticleCannon", "ParticleCannon"),
        # Faction strip runs again after the power tag exposes a faction word.
        ("Early_SuperweaponChinaCarpetBomb", "CarpetBomb"),
        ("SuperweaponChinaCarpetBomb", "CarpetBomb"),
        # Plain name passes through untouched.
        ("SomethingPlain", "SomethingPlain"),
    ],
)
def test_clean_power_name(raw: str, expected: str) -> None:
    assert clean_power_name(raw) == expected


# --- timeline_events_from_replay (real fixture) ----------------------------

_skip_no_fixture = pytest.mark.skipif(
    not _FIXTURE.exists(),
    reason=f"replay fixture not available: {_FIXTURE}",
)


@pytest.fixture(scope="module")
def replay() -> EnhancedReplayV2:
    with _FIXTURE.open() as f:
        return EnhancedReplayV2.model_validate(json.load(f))


@_skip_no_fixture
def test_timeline_returns_flat_list_of_timeline_events(
    replay: EnhancedReplayV2,
) -> None:
    name_by_idx = {p.index: p.name for p in replay.summary}
    events = timeline_events_from_replay(replay, {}, name_by_idx)

    assert isinstance(events, list)
    assert len(events) > 0
    assert all(isinstance(e, TimelineEvent) for e in events)
    # Every event carries the documented fields with the documented types.
    for e in events:
        assert isinstance(e.player_name, str) and e.player_name
        assert isinstance(e.at_minute, float)
        assert isinstance(e.event_name, str) and e.event_name
        assert isinstance(e.event_type, str) and e.event_type
        assert isinstance(e.cost, int)


@_skip_no_fixture
def test_timeline_is_sorted_by_minute(replay: EnhancedReplayV2) -> None:
    name_by_idx = {p.index: p.name for p in replay.summary}
    events = timeline_events_from_replay(replay, {}, name_by_idx)
    minutes = [e.at_minute for e in events]
    assert minutes == sorted(minutes)


@_skip_no_fixture
def test_timeline_drops_initial_rank_events(replay: EnhancedReplayV2) -> None:
    name_by_idx = {p.index: p.name for p in replay.summary}
    events = timeline_events_from_replay(replay, {}, name_by_idx)
    rank_events = [e for e in events if e.event_type == "rank_up"]
    # Rank 1 (and below) is the initial seed state and must be filtered out.
    assert rank_events, "fixture is expected to contain rank-up events"
    assert all(e.event_name != "Rank 1" for e in rank_events)
    # Rank labels are only derived for rank_level >= 2.
    assert all(int(e.event_name.split()[1]) >= 2 for e in rank_events)


@_skip_no_fixture
def test_timeline_stats_event_player_names_are_resolved(
    replay: EnhancedReplayV2,
) -> None:
    name_by_idx = {p.index: p.name for p in replay.summary}
    events = timeline_events_from_replay(replay, {}, name_by_idx)
    known_names = set(name_by_idx.values())
    # Stats-derived events resolve their player index back to a summary name.
    stats_types = {
        "rank_up",
        "superweapon_built",
        "search_and_destroy",
        "low_power",
        "player_eliminated",
        "tech_capture",
        "first_radar",
        "hunted",
        "unhunted",
    }
    for e in events:
        if e.event_type in stats_types:
            assert e.player_name in known_names


# --- hunted / unhunted markers (synthetic) ---------------------------------
#
# Built from the model classes rather than the gitignored fixture so these run
# in a fresh clone. `stats.huntedEvents` arrived with cncstats statsVersion 3,
# so most committed replay JSON predates it.

_HUNT_FRAME_COUNT = 600
_HUNT_DURATION_MINUTES = 10.0


def _hunt_replay(events: list[HuntedEvent] | None) -> EnhancedReplayV2:
    """A two-player replay carrying only `hunted_events`.

    frame_count/duration are chosen so `minutes_per_step` is exactly 1/60 -
    one frame is one second, so frame 60 lands on minute 1.0.
    """
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
        frame_count=_HUNT_FRAME_COUNT,
        time_stamp_begin=0,
        time_stamp_end=int(_HUNT_DURATION_MINUTES * 60),
        metadata=Metadata.model_construct(players=[]),
    )
    return EnhancedReplayV2.model_construct(
        header=header,
        body=[],
        summary=[
            PlayerSummaryV2.model_construct(name="Alice", index=1),
            PlayerSummaryV2.model_construct(name="Bob", index=2),
        ],
        stats=stats,
    )


def _hunt_timeline(events: list[HuntedEvent] | None) -> list[TimelineEvent]:
    replay = _hunt_replay(events)
    name_by_idx = {p.index: p.name for p in replay.summary}
    out = timeline_events_from_replay(replay, {}, name_by_idx)
    return [e for e in out if e.event_type in ("hunted", "unhunted")]


def test_hunted_event_becomes_a_timeline_marker() -> None:
    events = _hunt_timeline([HuntedEvent(frame=60, player=1, hunted=True)])
    assert len(events) == 1
    (e,) = events
    assert e.player_name == "Alice"
    assert e.event_type == "hunted"
    assert e.event_name == "Hunted"
    assert e.at_minute == pytest.approx(1.0)


def test_hunted_then_unhunted_emits_both_directions() -> None:
    events = _hunt_timeline(
        [
            HuntedEvent(frame=60, player=1, hunted=True),
            HuntedEvent(frame=120, player=1, hunted=False),
        ]
    )
    assert [(e.event_type, e.at_minute) for e in events] == [
        ("hunted", pytest.approx(1.0)),
        ("unhunted", pytest.approx(2.0)),
    ]
    assert events[1].event_name == "No Longer Hunted"


def test_hunted_state_is_tracked_per_player() -> None:
    """Alice going hunted must not suppress Bob's own hunted marker."""
    events = _hunt_timeline(
        [
            HuntedEvent(frame=60, player=1, hunted=True),
            HuntedEvent(frame=120, player=2, hunted=True),
        ]
    )
    assert [(e.player_name, e.event_type) for e in events] == [
        ("Alice", "hunted"),
        ("Bob", "hunted"),
    ]


def test_repeated_hunted_state_emits_only_the_flip() -> None:
    events = _hunt_timeline(
        [
            HuntedEvent(frame=60, player=1, hunted=True),
            HuntedEvent(frame=90, player=1, hunted=True),
            HuntedEvent(frame=120, player=1, hunted=True),
        ]
    )
    assert [e.at_minute for e in events] == [pytest.approx(1.0)]


def test_leading_unhunted_event_is_not_a_flip() -> None:
    """Players start un-hunted, so a hunted=False event before any hunted=True
    one is a restatement of the starting state, not a transition."""
    assert _hunt_timeline([HuntedEvent(frame=60, player=1, hunted=False)]) == []


def test_seed_frame_hunted_event_is_dropped() -> None:
    assert _hunt_timeline([HuntedEvent(frame=0, player=1, hunted=True)]) == []


def test_hunted_event_for_unknown_player_index_is_dropped() -> None:
    assert _hunt_timeline([HuntedEvent(frame=60, player=99, hunted=True)]) == []


def test_hunted_defaults_false_when_omitted_on_the_wire() -> None:
    """`hunted` is `omitempty` in the Go encoder, so an un-hunted event arrives
    with the key missing entirely."""
    event = HuntedEvent.model_validate({"frame": 60, "player": 1})
    assert event.hunted is False


_PRE_V3_STATS: dict[str, object] = {
    "battlePlanEvents": [],
    "buildEvents": [],
    "captureEvents": [],
    "deathEvents": [],
    "energyEvents": [],
    "killEvents": [],
    "radarEvents": [],
    "rankEvents": [],
    "sciencePointsEvents": [],
    "skillPointsEvents": [],
    "timeSeries": {"players": []},
}


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(_PRE_V3_STATS, id="key absent"),
        pytest.param({**_PRE_V3_STATS, "huntedEvents": None}, id="explicit null"),
    ],
)
def test_pre_statsversion_3_hunted_events_parse(payload: dict[str, object]) -> None:
    """Stats predating statsVersion 3 carry no hunted stream, in either of two
    shapes: the key missing, or an explicit `null` (cncstats is Go, so a nil
    slice marshals to `null` rather than `[]`). Both must validate - the null
    shape raised ValidationError and killed the parse for those replays."""
    stats = EnrichedStats.model_validate(payload)

    assert stats.hunted_events is None


def test_absent_hunted_stream_yields_no_markers() -> None:
    """The consumer side of the same thing: `hunted_events` being None must
    read as "no hunted flips", not blow up building the timeline."""
    assert _hunt_timeline(None) == []
