import json
from pathlib import Path

import pytest

from radarvan.cncstats_types import EnhancedReplay
from radarvan.cncstats_types_v2 import EnhancedReplayV2

TESTS_DIR = Path(__file__).parent


@pytest.fixture
def parsed_data() -> dict:
    return json.loads((TESTS_DIR / "parsed.json").read_text())


@pytest.fixture
def new_format_data() -> dict:
    return json.loads((TESTS_DIR / "new_format.json").read_text())


@pytest.fixture
def v1_replay(parsed_data: dict) -> EnhancedReplay:
    return EnhancedReplay.model_validate(parsed_data)


@pytest.fixture
def v2_replay(new_format_data: dict) -> EnhancedReplayV2:
    return EnhancedReplayV2.model_validate(new_format_data)


@pytest.fixture
def v2_replay_old_format(parsed_data: dict) -> EnhancedReplayV2:
    return EnhancedReplayV2.model_validate(parsed_data)


def test_v1_parses_players(v1_replay: EnhancedReplay) -> None:
    players = {p.Name: p for p in v1_replay.Summary}
    assert players["Skip"].Side == "China"
    assert players["Skip"].Win is True
    assert players["131"].Win is False
    assert players["Skip"].Team != players["131"].Team


def test_v1_parses_commands(v1_replay: EnhancedReplay) -> None:
    first = v1_replay.Body[0]
    assert first.OrderName == "CreateUnit"
    assert first.PlayerName == "Skip"
    assert first.Details is not None
    assert first.Details.Name == "ChinaVehicleDozer"


def test_v2_parses_players(v2_replay: EnhancedReplayV2) -> None:
    players = {p.Name: p for p in v2_replay.Summary}
    assert players["Skip"].Side == "China"
    assert players["Skip"].Win is True
    assert players["131"].Win is False
    assert players["Skip"].Team != players["131"].Team


def test_v2_parses_player_stats(v2_replay: EnhancedReplayV2) -> None:
    assert v2_replay.Stats is not None
    stats = {p.displayName: p for p in v2_replay.Stats.players}
    assert stats["Skip"].faction == "FactionChina"
    assert stats["Skip"].moneySpent > 0
    assert stats["Skip"].score > stats["131"].score


def test_v2_parses_kill_events(v2_replay: EnhancedReplayV2) -> None:
    assert v2_replay.Stats is not None
    first_kill = v2_replay.Stats.killEvents[0]
    assert first_kill.killer == "Nuke_ChinaTankGattling"
    assert first_kill.victim == "Tank_ChinaInfantryRedguard"
    assert first_kill.damageType == "GATTLING"


def test_v2_parses_build_events(v2_replay: EnhancedReplayV2) -> None:
    assert v2_replay.Stats is not None
    first_build = v2_replay.Stats.buildEvents[0]
    assert first_build.object == "ChinaCommandCenter"
    assert first_build.cost == 2000


def test_v2_parses_money_time_series(v2_replay: EnhancedReplayV2) -> None:
    assert v2_replay.Stats is not None
    series = {p.index: p for p in v2_replay.Stats.timeSeries.players}
    # money starts at 0 before the game clock (pre-placed buildings), then rises to starting credits
    skip_money = series[1].money
    assert skip_money[0] == 0
    assert skip_money[1] == 10000


def test_v2_stats_absent_for_old_format(v2_replay_old_format: EnhancedReplayV2) -> None:
    assert v2_replay_old_format.Stats is None
