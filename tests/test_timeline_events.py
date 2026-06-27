"""Name-cleaning helpers and timeline-event extraction.

The cleaning helpers (`radarvan.replay_helpers.clean_object_name` and
`radarvan.timeline_events._clean_power_name`) are pure functions and are always
exercised. The end-to-end `timeline_events_from_replay` test runs against the
real cncstats fixture `references/example_cncstats_output.json` when present and
is skipped otherwise (that directory is gitignored, so it is unavailable in a
fresh clone / CI).
"""

import json
from pathlib import Path

import pytest

from radarvan.api_types import TimelineEvent
from radarvan.cncstats_model.zhreplay import EnhancedReplayV2
from radarvan.replay_helpers import clean_object_name
from radarvan.timeline_events import _clean_power_name, timeline_events_from_replay

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


# --- _clean_power_name -----------------------------------------------------


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
    assert _clean_power_name(raw) == expected


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
    }
    for e in events:
        if e.event_type in stats_types:
            assert e.player_name in known_names
