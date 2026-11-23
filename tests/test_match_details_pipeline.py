"""Golden values for replay JSON -> MatchDetails on the checked-in fixture
(match 92990953, a 3v3), and the durable details-cache tiers around it."""

import json
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from radarvan import s3_store
from radarvan.api_types import General, MatchDetails
from radarvan.cncstats_model.zhreplay import EnhancedReplayV2
from radarvan.db_utils import ReplayManager
from radarvan.match_details import (
    DETAILS_VERSION,
    load_match_details,
    match_details_from_replay,
)

_FIXTURE = (
    Path(__file__).resolve().parents[1] / "references" / "example_cncstats_output.json"
)
_JSON_URI = "s3://bucket/reps/92990953.json"


@pytest.fixture(scope="module")
def details() -> MatchDetails:
    replay = EnhancedReplayV2.model_validate_json(_FIXTURE.read_bytes())
    result = match_details_from_replay(replay)
    assert result is not None
    return result


def test_identity_and_teams(details: MatchDetails) -> None:
    assert details.match_id == 92990953
    assert details.map_name == "userdata/maps/unity b zh v2"
    rows = {(p.Name, p.Team, p.Win, p.Side) for p in details.player_summary}
    assert rows == {
        ("Skip", 1, True, "USA Lazr"),
        ("Mod", 1, True, "GLA"),
        ("Wld", 1, True, "China"),
        ("Tytan", 2, False, "China Tank"),
        ("131", 2, False, "USA Superweapon"),
        ("Syn", 2, False, "GLA Stealth"),
    }


def test_generals_and_aliases(details: MatchDetails) -> None:
    # powers/win_prob carry alias-resolved names; player_summary keeps raw ones.
    assert {p.player_name: p.general for p in details.powers.players} == {
        "Skip": General.LASER,
        "Modus": General.GLA,
        "WildCard": General.CHINA,
        "Tytan": General.TANK,
        "OneThree111": General.SUPER,
        "Syn": General.STEALTH,
    }
    wp = details.win_prob_over_time
    assert wp is not None
    assert set(wp.team_a_players) == {"Skip", "Modus", "WildCard"}
    assert wp.actual_winner == "team_a"


def test_economy(details: MatchDetails) -> None:
    assert details.player_money_spent == {
        "Skip": 69425,
        "Mod": 87250,
        "Tytan": 109055,
        "131": 37975,
        "Syn": 83900,
        "Wld": 79950,
    }
    assert details.player_money_collected == {
        "Skip": 60590,
        "Mod": 82174,
        "Tytan": 95906,
        "131": 25770,
        "Syn": 72246,
        "Wld": 69569,
    }


def test_kills(details: MatchDetails) -> None:
    kills = details.kill_events
    assert len(kills) == 571
    assert sum(k.value for k in kills) == 239265
    assert Counter(k.killer_player for k in kills) == {
        "Skip": 172,
        "Mod": 131,
        "Wld": 108,
        "Syn": 72,
        "Tytan": 52,
        "131": 36,
    }
    assert Counter(k.victim_player for k in kills)["Syn"] == 236
    assert all(k.killer_player != k.victim_player for k in kills)
    assert [k.at_minute for k in kills] == sorted(k.at_minute for k in kills)

    assert details.first_blood is not None
    assert (details.first_blood.attacker, details.first_blood.victim) == ("Skip", "Syn")
    assert details.first_blood.atMinute == pytest.approx(1.2438, abs=1e-4)
    assert details.building_first_blood is not None
    assert (
        details.building_first_blood.attacker,
        details.building_first_blood.victim,
    ) == ("Wld", "Tytan")


def test_build_orders_apm_and_milestones(details: MatchDetails) -> None:
    openings = {
        p: [(b.name, b.count) for b in bo.buildings[:4]]
        for p, bo in details.build_orders.items()
    }
    assert openings["Skip"] == [
        ("PowerPlant", 1),
        ("Barracks", 1),
        ("SupplyCenter", 1),
        ("PatriotBattery", 2),
    ]
    assert openings["Syn"] == [
        ("Barracks", 1),
        ("SupplyStash", 2),
        ("TunnelNetwork", 3),
        ("ArmsDealer", 3),
    ]
    assert {a.player_name: a.action_count for a in details.apms} == {
        "Skip": 555,
        "Mod": 870,
        "Tytan": 634,
        "131": 509,
        "Syn": 1103,
        "Wld": 624,
    }
    assert {k: len(v.upgrades) for k, v in details.upgrade_events.items()} == {
        "Skip": 16,
        "Mod": 8,
        "Tytan": 10,
        "131": 5,
        "Syn": 15,
        "Wld": 9,
    }
    assert details.time_to_search_destroy == pytest.approx(
        {"131": 10.7644, "Skip": 11.9605}, abs=1e-3
    )
    assert (
        Counter(e.event_type for e in details.timeline_events)["player_eliminated"] == 3
    )


def test_cached_json_round_trip_keeps_the_latest_sample(details: MatchDetails) -> None:
    # The DB tier stores model_dump(mode="json"), whose Minute serializer rounds
    # float dict keys to 3dp: samples one frame apart collide (this fixture has
    # several). That is only safe because the later, cumulative sample wins.
    payload = json.dumps(details.model_dump(mode="json", by_alias=True))
    cached = MatchDetails.model_validate_json(payload)
    assert set(cached.stats_data) == set(details.stats_data)
    for series, points in details.stats_data.items():
        latest_per_key: dict[float, dict[str, int]] = {}
        for minute, values in points.items():
            latest_per_key[round(minute, 3)] = values
        assert cached.stats_data[series] == latest_per_key, series
    assert len(cached.apm_over_time) == len(details.apm_over_time)
    assert len(cached.kill_events) == len(details.kill_events)
    assert cached.player_money_spent == details.player_money_spent
    # A cache hit re-serializes identically, so hit and miss responses agree.
    assert json.dumps(cached.model_dump(mode="json", by_alias=True)) == payload


class _FakeReplayManager:
    def __init__(self, cached: MatchDetails | None = None, known: bool = True) -> None:
        self.cached = cached
        self.known = known
        self.cache_lookups: list[str] = []
        self.saved: list[tuple[int, str]] = []

    def get_cached_details(self, match_id: int, version: str) -> MatchDetails | None:
        self.cache_lookups.append(version)
        return self.cached

    def get_replay_json_by_match_id(self, match_id: int) -> SimpleNamespace | None:
        if not self.known:
            return None
        return SimpleNamespace(replay_file_url="https://example/92990953.rep")

    def get_replay_file(self, path: str) -> SimpleNamespace:
        return SimpleNamespace(s3_uri=_JSON_URI.replace(".json", ".rep"))

    def get_parsed_file(self, json_path: str) -> SimpleNamespace:
        return SimpleNamespace(is_v2=True)

    def save_cached_details(
        self, match_id: int, details: MatchDetails, version: str
    ) -> None:
        self.saved.append((match_id, version))


@pytest.fixture
def s3_reads(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    reads: list[str] = []

    class _Store:
        def read_bytes(self, uri: str) -> bytes:
            reads.append(uri)
            return _FIXTURE.read_bytes()

    monkeypatch.setattr(s3_store, "get_store", _Store)
    return reads


def test_cache_hit_never_touches_s3(details: MatchDetails, s3_reads: list[str]) -> None:
    rm = _FakeReplayManager(cached=details)
    assert load_match_details(92990953, cast(ReplayManager, rm)) is details
    assert rm.cache_lookups == [DETAILS_VERSION]
    assert s3_reads == []
    assert rm.saved == []


def test_cache_miss_parses_from_s3_and_writes_back(
    details: MatchDetails, s3_reads: list[str]
) -> None:
    rm = _FakeReplayManager()
    result = load_match_details(92990953, cast(ReplayManager, rm))
    assert result == details
    assert s3_reads == [_JSON_URI]
    assert rm.saved == [(92990953, DETAILS_VERSION)]


def test_unknown_match_is_none_and_not_cached(s3_reads: list[str]) -> None:
    rm = _FakeReplayManager(known=False)
    assert load_match_details(1, cast(ReplayManager, rm)) is None
    assert s3_reads == []
    assert rm.saved == []
