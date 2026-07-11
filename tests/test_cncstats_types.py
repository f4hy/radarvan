import json
from pathlib import Path

import pytest

from radarvan.cncstats_types import EnhancedReplay
from radarvan.cncstats_model.zhreplay import EnhancedReplayV2

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
def new_output_data() -> dict:
    return json.loads((TESTS_DIR / "new_cncstats_output.json").read_text())


@pytest.fixture
def new_output_replay(new_output_data: dict) -> EnhancedReplayV2:
    return EnhancedReplayV2.model_validate(new_output_data)


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


@pytest.mark.skip(
    reason="new_format.json fixture is old cncstats format; needs regeneration with new cncstats binary"
)
def test_v2_parses_players(v2_replay: EnhancedReplayV2) -> None:
    players = {p.name: p for p in (v2_replay.summary or [])}
    assert players["Skip"].side == "China"
    assert players["Skip"].win is True
    assert players["131"].win is False
    assert players["Skip"].team != players["131"].team


@pytest.mark.skip(
    reason="new_format.json fixture is old cncstats format; needs regeneration with new cncstats binary"
)
def test_v2_parses_player_stats(v2_replay: EnhancedReplayV2) -> None:
    assert v2_replay.stats is not None
    stats = {p.name: p for p in (v2_replay.summary or [])}
    assert stats["Skip"].faction == "FactionChina"
    assert stats["Skip"].money_spent is not None and stats["Skip"].money_spent > 0
    assert (stats["Skip"].score or 0) > (stats["131"].score or 0)


@pytest.mark.skip(
    reason="new_format.json fixture is old cncstats format; needs regeneration with new cncstats binary"
)
def test_v2_parses_kill_events(v2_replay: EnhancedReplayV2) -> None:
    assert v2_replay.stats is not None
    first_kill = (v2_replay.stats.kill_events or [])[0]
    assert first_kill.killer == "Nuke_ChinaTankGattling"
    assert first_kill.victim == "Tank_ChinaInfantryRedguard"
    assert first_kill.damage_type == "GATTLING"


@pytest.mark.skip(
    reason="new_format.json fixture is old cncstats format; needs regeneration with new cncstats binary"
)
def test_v2_parses_build_events(v2_replay: EnhancedReplayV2) -> None:
    assert v2_replay.stats is not None
    first_build = (v2_replay.stats.build_events or [])[0]
    assert first_build.object == "ChinaCommandCenter"
    assert first_build.cost == 2000


@pytest.mark.skip(
    reason="new_format.json fixture is old cncstats format; needs regeneration with new cncstats binary"
)
def test_v2_parses_money_time_series(v2_replay: EnhancedReplayV2) -> None:
    assert v2_replay.stats is not None
    assert v2_replay.stats.time_series is not None
    series = {p.index: p for p in (v2_replay.stats.time_series.players or [])}
    # money starts at 0 before the game clock (pre-placed buildings), then rises to starting credits
    skip_money = series[1].money or []
    assert skip_money[0] == 0
    assert skip_money[1] == 10000


def test_new_output_parses_header(new_output_replay: EnhancedReplayV2) -> None:
    assert new_output_replay.header is not None
    assert new_output_replay.header.version == "Version 1.04"
    assert new_output_replay.header.time_stamp_begin == 1760577461
    assert new_output_replay.header.desync is False
    assert new_output_replay.header.quit_early is False
    assert new_output_replay.header.metadata is not None
    assert new_output_replay.header.metadata.seed == 49429937
    assert new_output_replay.header.metadata.map_path == "userdata/maps/fata morgana"


def test_new_output_parses_players(new_output_replay: EnhancedReplayV2) -> None:
    assert new_output_replay.summary is not None
    players = {p.name: p for p in new_output_replay.summary}
    assert "Skip" in players
    assert "131" in players
    assert players["Skip"].faction == "FactionChinaNukeGeneral"
    assert players["Skip"].money_spent == 2000
    assert players["Skip"].index == 1
    assert players["Skip"].team == 1


def test_new_output_has_stats(new_output_replay: EnhancedReplayV2) -> None:
    assert new_output_replay.stats is not None
    assert new_output_replay.stats.build_events is not None
    first_build = new_output_replay.stats.build_events[0]
    assert first_build.object == "Nuke_ChinaCommandCenter"
    assert first_build.cost == 2000
    assert first_build.player == 1


def test_new_output_time_series(new_output_replay: EnhancedReplayV2) -> None:
    assert new_output_replay.stats is not None
    assert new_output_replay.stats.time_series is not None
    series = {p.index: p for p in (new_output_replay.stats.time_series.players or [])}
    skip_money = series[1].money or []
    assert skip_money[0] == 0
    assert skip_money[1] == 10000


def test_new_output_game_info(new_output_replay: EnhancedReplayV2) -> None:
    assert new_output_replay.game_info is not None
    assert new_output_replay.game_info.snapshot_interval == 30
    assert new_output_replay.game_info.player_count == 6


def test_new_output_header_players(new_output_replay: EnhancedReplayV2) -> None:
    assert new_output_replay.header is not None
    assert new_output_replay.header.metadata is not None
    hplayers = {p.name: p for p in (new_output_replay.header.metadata.players or [])}
    assert hplayers["Skip"].type == "H"
    assert hplayers["Skip"].color == "ColorGold"
    assert hplayers["131"].team == "2"
