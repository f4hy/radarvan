"""Generals-power picks and activations: identity, extraction, and aggregation.

Three layers, tested separately because they fail separately:

* `generals_powers` maps a raw `PurchaseScience` integer to a name, and is the
  one place allowed to say "I don't know".
* `powers.powers_from_replay` turns a replay into the per-match projection.
* `queries.powers` folds that projection into per-player habits with a group
  baseline.
"""

from dataclasses import dataclass

import pytest

from radarvan import generals_powers
from radarvan.api_types import General, MatchPowers
from radarvan.cncstats_model.body import BodyChunk
from radarvan.cncstats_model.header import (
    GeneralsHeader,
    Metadata,
    Player as HeaderPlayer,
)
from radarvan.cncstats_model.statsfile import DeathEvent, TimeSeries
from radarvan.cncstats_model.zhreplay import (
    EnhancedReplayV2,
    EnrichedStats,
    PlayerSummaryV2,
)
from radarvan.powers import powers_from_replay
from radarvan.queries import powers as query_powers


# --- generals_powers -------------------------------------------------------


def test_known_science_ids_resolve_to_their_game_names() -> None:
    """Anchors confirmed against the corpus - see the module docstring there."""
    assert generals_powers.display_name(14, "FactionAmerica") == "Spy Drone"
    assert generals_powers.display_name(16, "FactionAmericaLaserGeneral") == "Paradrop"
    assert (
        generals_powers.display_name(18, "FactionAmericaLaserGeneral") == "Paradrop 3"
    )
    assert generals_powers.display_name(62, "FactionGLAToxinGeneral") == "Cash Bounty"
    assert (
        generals_powers.display_name(69, "FactionChinaNukeGeneral")
        == "Emergency Repair"
    )


def test_a_science_from_another_faction_is_left_unresolved() -> None:
    """A China player cannot buy an America science.

    The tail of the science list is where a non-stock game build is most likely
    to diverge from the file this table came from, and that divergence shows up
    exactly as a faction mismatch. Reporting the stock name anyway would put
    "A-10 Strike" on a China general's page and look like a data bug forever.
    """
    assert generals_powers.resolve(14, "FactionAmerica") is not None
    assert generals_powers.resolve(14, "FactionChinaTankGeneral") is None
    assert generals_powers.display_name(14, "FactionChinaTankGeneral") == "Science #14"


def test_unpurchasable_sciences_are_not_in_the_table() -> None:
    """`SciencePurchasePointCost = 0` means "not purchasable", not "free".

    Ids landing on one of those are a mapping we don't trust, and must not be
    reported under that entry's name.
    """
    assert 75 not in generals_powers.SCIENCES
    assert generals_powers.display_name(75, "FactionGLA") == "Science #75"


def test_every_table_entry_has_a_sane_rank_and_level() -> None:
    for science_id, science in generals_powers.SCIENCES.items():
        assert science_id > 0
        assert science.rank in (1, 3, 5)
        assert 1 <= science.level <= 3
        assert science.faction in ("", "America", "China", "GLA")


@pytest.mark.parametrize(
    "science_id, faction, activation",
    [
        # The science and the power spell it differently in the game files;
        # both have to land on one row of one table.
        (49, "FactionChina", "SuperweaponChinaCarpetBomb"),
        (50, "FactionChinaInfantryGeneral", "Early_SuperweaponChinaCarpetBomb"),
        (51, "FactionChinaNukeGeneral", "Nuke_SuperweaponChinaCarpetBomb"),
        (26, "FactionAmericaAirForceGeneral", "AirF_SuperweaponCarpetBomb"),
        # The Laser general's single-level Spectre Gunship science is named
        # "...Solo"; the power it fires is not.
        (22, "FactionAmericaLaserGeneral", "SuperweaponSpectreGunship"),
        (23, "FactionAmericaSuperWeaponGeneral", "AirF_SuperweaponSpectreGunship"),
        (16, "FactionAmerica", "SuperweaponParadropAmerica"),
        (90, "FactionChinaInfantryGeneral", "Infa_SuperweaponInfantryParadrop"),
        (14, "FactionAmerica", "SpecialPowerSpyDrone"),
    ],
)
def test_a_science_shares_its_name_with_the_power_it_grants(
    science_id: int, faction: str, activation: str
) -> None:
    """Otherwise a pick and its uses render as two unrelated rows.

    This is not cosmetic: the page's whole claim is "here is what they bought
    and here is how often they fired it", and a name mismatch quietly splits
    that into "bought, never used" next to "used, never bought".
    """
    science = generals_powers.resolve(science_id, faction)
    assert science is not None
    assert science.family == generals_powers.pretty_power_name(activation)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("SpecialPowerSpyDrone", "Spy Drone"),
        # A general's own spelling of a power is the same power to a reader.
        ("AirF_SuperweaponSpectreGunship", "Spectre Gunship"),
        ("Early_SuperweaponChinaCarpetBomb", "Carpet Bomb"),
        # Faction as a suffix, so the power's name matches its science's.
        ("SuperweaponParadropAmerica", "Paradrop"),
        ("SpecialPowerRadarVanScan", "Radar Van Scan"),
    ],
)
def test_power_names_collapse_to_one_display_name(raw: str, expected: str) -> None:
    assert generals_powers.pretty_power_name(raw) == expected


def test_general_is_read_off_the_faction_string() -> None:
    assert generals_powers.general_of("FactionAmericaLaserGeneral") is General.LASER
    assert generals_powers.general_of("FactionGLA") is General.GLA
    assert generals_powers.general_of("nonsense") is General.UNRECOGNIZED


# --- powers_from_replay ----------------------------------------------------

_FRAME_COUNT = 600
_DURATION_MINUTES = 10.0


@dataclass(frozen=True)
class Slot:
    name: str
    faction: str
    powers_used: dict[str, int]
    observer: bool = False


def _header_player(slot: Slot, index: int) -> HeaderPlayer:
    return HeaderPlayer.model_construct(
        name=slot.name,
        color=str(index),
        flags="TT",
        ip="",
        nat_behavior="",
        port="",
        starting_position=str(index),
        team="0",
        type="H",
        player_template="-2" if slot.observer else "1",
    )


def _replay(slots: list[Slot], body: list[BodyChunk], deaths: list[DeathEvent] = []):
    """A replay with `minutes_per_step` of exactly 1/60 - one frame, one second."""
    stats = EnrichedStats.model_construct(
        battle_plan_events=[],
        build_events=[],
        capture_events=[],
        death_events=deaths,
        energy_events=[],
        hunted_events=[],
        kill_events=[],
        radar_events=[],
        rank_events=[],
        science_points_events=[],
        skill_points_events=[],
        time_series=TimeSeries.model_construct(players=[]),
    )
    return EnhancedReplayV2.model_construct(
        header=GeneralsHeader.model_construct(
            frame_count=_FRAME_COUNT,
            time_stamp_begin=0,
            time_stamp_end=int(_DURATION_MINUTES * 60),
            metadata=Metadata.model_construct(
                players=[_header_player(s, i) for i, s in enumerate(slots)]
            ),
        ),
        body=body,
        summary=[
            PlayerSummaryV2.model_construct(
                name=slot.name,
                index=i + 1,
                faction=slot.faction,
                powers_used=dict(slot.powers_used),
            )
            for i, slot in enumerate(slots)
        ],
        stats=stats,
    )


def _purchase(player: str, science_id: int, frame: int) -> BodyChunk:
    return BodyChunk.__pydantic_validator__.validate_python(
        {
            "argMetadata": [],
            "arguments": [science_id],
            "details": None,
            "numberOfArguments": 1,
            "orderCode": 1044,
            "orderName": "PurchaseScience",
            "playerID": 2,
            "playerName": player,
            "timeCode": frame,
        }
    )


def _activation(player: str, name: str, frame: int) -> BodyChunk:
    return BodyChunk.__pydantic_validator__.validate_python(
        {
            "argMetadata": [],
            "arguments": [0],
            "details": {"Name": name},
            "numberOfArguments": 1,
            "orderCode": 1041,
            "orderName": "SpecialPowerAtLocation",
            "playerID": 2,
            "playerName": player,
            "timeCode": frame,
        }
    )


def test_a_science_bought_once_is_counted_once() -> None:
    """The order stream repeats a purchase; the game does not.

    A player clicking an already-bought button still emits the order, so
    counting orders would report Artillery Barrage taken three times in one
    game and push a pick *rate* above 1.
    """
    replay = _replay(
        [Slot("Alice", "FactionChinaTankGeneral", {})],
        [_purchase("Alice", 36, 60)] * 3,
    )
    (player,) = powers_from_replay(replay).players
    assert [p.science_id for p in player.picks] == [36]
    assert player.picks[0].at_minute == pytest.approx(1.0)


def test_separate_levels_are_separate_picks() -> None:
    replay = _replay(
        [Slot("Alice", "FactionChinaTankGeneral", {})],
        [_purchase("Alice", 36, 60), _purchase("Alice", 37, 120)],
    )
    (player,) = powers_from_replay(replay).players
    assert [p.science_id for p in player.picks] == [36, 37]
    # Two sciences, one family - the aggregation counts them as one habit
    # taken to level 2 (see test_taking_every_level_is_still_one_pick).
    assert [
        generals_powers.resolve(p.science_id, player.faction).family  # type: ignore[union-attr]
        for p in player.picks
    ] == ["Artillery Barrage"] * 2


def test_unit_abilities_are_not_generals_powers() -> None:
    """A Ranger capturing a building is a unit's button, not a generals point.

    The general-prefixed spellings are the trap: testing the raw name for a
    `SpecialAbility` prefix lets every `Demo_SpecialAbility...` through.
    """
    replay = _replay(
        [
            Slot(
                "Alice",
                "FactionGLADemolitionGeneral",
                {
                    "SpecialAbilityRebelCaptureBuilding": 8,
                    "Demo_SpecialAbilityDemoKellTimedCharges": 3,
                    "SuperweaponRebelAmbush": 2,
                },
            )
        ],
        [],
    )
    (player,) = powers_from_replay(replay).players
    assert [u.name for u in player.uses] == ["Rebel Ambush"]


def test_one_powers_two_spellings_merge_into_one_row() -> None:
    replay = _replay(
        [
            Slot(
                "Alice",
                "FactionAmericaSuperWeaponGeneral",
                {
                    "SuperweaponSpectreGunship": 2,
                    "AirF_SuperweaponSpectreGunship": 3,
                },
            )
        ],
        [],
    )
    (player,) = powers_from_replay(replay).players
    assert [(u.name, u.count) for u in player.uses] == [("Spectre Gunship", 5)]


def test_first_use_minute_comes_from_the_body() -> None:
    replay = _replay(
        [Slot("Alice", "FactionAmerica", {"SpecialPowerSpyDrone": 2})],
        [
            _activation("Alice", "SpecialPowerSpyDrone", 300),
            _activation("Alice", "SpecialPowerSpyDrone", 120),
        ],
    )
    (player,) = powers_from_replay(replay).players
    assert player.uses[0].first_minute == pytest.approx(2.0)


def test_counts_survive_a_replay_with_no_body_stream() -> None:
    """cncstats drops the order stream on some replays; `powersUsed` survives."""
    replay = _replay(
        [Slot("Alice", "FactionAmerica", {"SpecialPowerSpyDrone": 4})], []
    )
    (player,) = powers_from_replay(replay).players
    assert [(u.name, u.count, u.first_minute) for u in player.uses] == [
        ("Spy Drone", 4, None)
    ]
    assert player.picks == []


def test_the_cached_projection_stores_ids_not_names() -> None:
    """Names are a property of the game's science list, not of a match.

    Resolving at read time is what makes identifying an unknown science a
    one-line table edit instead of a DETAILS_VERSION bump and a re-derivation
    of every cached match. A `name`/`family` field creeping back onto the
    stored shape silently gives that up, so assert the shape directly.
    """
    stored = set(MatchPowers.model_json_schema()["$defs"]["PowerPick"]["properties"])
    assert stored == {"atMinute", "scienceId"}


def test_minutes_stop_at_elimination() -> None:
    """The denominator of a per-minute rate is time alive, not match length."""
    replay = _replay(
        [
            Slot("Alice", "FactionAmerica", {}),
            Slot("Bob", "FactionChina", {}),
        ],
        [],
        deaths=[DeathEvent(frame=120, player=1)],
    )
    by_name = {p.player_name: p for p in powers_from_replay(replay).players}
    assert by_name["Alice"].minutes == pytest.approx(2.0)
    assert by_name["Bob"].minutes == pytest.approx(_DURATION_MINUTES)


def test_an_observer_changes_nothing_about_the_players() -> None:
    """Adding a spectator must be a no-op - see tests/test_observer_invariance."""
    players = [Slot("Alice", "FactionAmerica", {"SpecialPowerSpyDrone": 3})]
    body = [_purchase("Alice", 14, 60)]
    without = powers_from_replay(_replay(players, body))
    with_observer = powers_from_replay(
        _replay(
            [*players, Slot("Caster", "FactionAmerica", {}, observer=True)], body
        )
    )
    assert with_observer == without


# --- aggregation -----------------------------------------------------------


def _index(*matches: MatchPowers) -> query_powers.PowerIndex:
    index = query_powers.PowerIndex()
    for match in matches:
        query_powers._fold(index, match)
        index.matches += 1
    return index


def _match(*slot_specs: tuple[str, str, list[int], dict[str, int]]) -> MatchPowers:
    return powers_from_replay(
        _replay(
            [Slot(name, faction, uses) for name, faction, _, uses in slot_specs],
            [
                _purchase(name, science_id, 60)
                for name, _, science_ids, _ in slot_specs
                for science_id in science_ids
            ],
        )
    )


def test_taking_every_level_is_still_one_pick() -> None:
    """Pick *rate* is games, not points - three levels in one game is one game."""
    index = _index(_match(("Alice", "FactionChinaTankGeneral", [36, 37, 38], {})))
    counts = index.by_player[("Alice", General.TANK)]
    assert counts.picked["Artillery Barrage"] == 1
    assert counts.levels["Artillery Barrage"] == 3


def test_the_baseline_leaves_the_player_out_of_their_own_comparison() -> None:
    """With a roster this small, self-inclusion flattens the signal.

    Alice takes Artillery Barrage every game and nobody else ever does. Her
    baseline has to read 0%, not "0% diluted by her own three games".
    """
    matches = [
        _match(
            ("Alice", "FactionChinaTankGeneral", [36], {}),
            ("Bob", "FactionChinaTankGeneral", [32], {}),
            ("Carol", "FactionChinaTankGeneral", [32], {}),
        )
        for _ in range(4)
    ]
    profile = query_powers.profile_for(_index(*matches), "Alice")
    (general,) = profile.generals
    row = next(r for r in general.rows if r.power == "Artillery Barrage")
    assert row.pick_rate == pytest.approx(1.0)
    assert row.group_pick_rate == pytest.approx(0.0)
    assert general.group_games == 8


def test_a_pick_rate_never_exceeds_one() -> None:
    matches = [
        _match(("Alice", "FactionChinaTankGeneral", [36, 37, 38], {})) for _ in range(5)
    ]
    profile = query_powers.profile_for(_index(*matches), "Alice")
    for general in profile.generals:
        for row in general.rows:
            assert 0.0 <= row.pick_rate <= 1.0
            assert 0.0 <= row.group_pick_rate <= 1.0


def test_a_building_granted_power_is_marked_unpurchasable() -> None:
    """Spy Satellite has usage but can never have a pick rate.

    Observed, not hardcoded: a power that appears in the corpus only as an
    activation is one no generals point buys, and rendering it as a 0% pick
    rate would read as a choice nobody makes rather than one nobody has.
    """
    matches = [
        _match(
            (
                "Alice",
                "FactionAmerica",
                [14],
                {"SpecialPowerSpyDrone": 2, "SpecialPowerSpySatellite": 3},
            ),
            ("Bob", "FactionAmerica", [14], {}),
            ("Carol", "FactionAmerica", [14], {}),
        )
        for _ in range(3)
    ]
    profile = query_powers.profile_for(_index(*matches), "Alice")
    (general,) = profile.generals
    rows = {r.power: r for r in general.rows}
    assert rows["Spy Drone"].purchasable
    assert not rows["Spy Satellite"].purchasable


def test_a_power_only_the_group_uses_still_gets_a_row() -> None:
    """"Everyone else sweeps with the satellite and you never do" is a finding.

    A building-granted power has no pick rate, so the only way it can surface
    is its usage - and filtering untouched rows on pick rate alone dropped it
    off the page entirely.
    """
    matches = [
        _match(
            ("Alice", "FactionAmerica", [14], {}),
            ("Bob", "FactionAmerica", [14], {"SpecialPowerSpySatellite": 6}),
            ("Carol", "FactionAmerica", [14], {"SpecialPowerSpySatellite": 6}),
        )
        for _ in range(3)
    ]
    profile = query_powers.profile_for(_index(*matches), "Alice")
    (general,) = profile.generals
    row = next(r for r in general.rows if r.power == "Spy Satellite")
    assert row.uses == 0
    assert row.group_uses_per_minute > 0


def test_recon_rate_sums_the_scouting_powers() -> None:
    matches = [
        _match(
            (
                "Alice",
                "FactionAmerica",
                [14],
                {"SpecialPowerSpyDrone": 4, "SpecialPowerSpySatellite": 6},
            ),
            ("Bob", "FactionAmerica", [14], {}),
            ("Carol", "FactionAmerica", [14], {}),
        )
        for _ in range(3)
    ]
    profile = query_powers.profile_for(_index(*matches), "Alice")
    (general,) = profile.generals
    # 10 activations over a 10-minute game, every game.
    assert general.recon_per_minute == pytest.approx(1.0)
    assert general.group_recon_per_minute == pytest.approx(0.0)


def test_an_unusual_pick_needs_both_a_gap_and_the_games_to_back_it() -> None:
    matches = [
        _match(
            ("Alice", "FactionChinaTankGeneral", [36], {}),
            ("Bob", "FactionChinaTankGeneral", [32], {}),
            ("Carol", "FactionChinaTankGeneral", [32], {}),
            ("Dave", "FactionChinaTankGeneral", [32], {}),
        )
        for _ in range(6)
    ]
    profile = query_powers.profile_for(_index(*matches), "Alice")
    unusual = {u.power: u for u in profile.unusual}
    assert unusual["Artillery Barrage"].direction == "over"
    assert unusual["Battlemaster Training"].direction == "under"
    # Sorted by how much evidence backs the gap, not by the gap alone.
    assert profile.unusual == sorted(
        profile.unusual, key=lambda u: -abs(u.surprise)
    )
