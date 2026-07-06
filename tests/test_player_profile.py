"""Player profile: peer-normalized favorites/aversions, percentiles, live parts."""

import json
from datetime import date, datetime

from radarvan.api_types import (
    AcademyStats,
    General,
    MatchDetails,
    MatchInfo,
    ObjectSummary,
    Player,
    PlayerSummary,
    Team,
)
from radarvan.cncstats_model.zhreplay import EnhancedReplayV2
from radarvan.match_details import match_details_from_replay
from radarvan.player_ids import resolve_player_name
from radarvan.player_profile import (
    PROFILE_VERSION,
    ObjectCategory,
    PlayerMatchProjection,
    ProfileMatchData,
    aggregate_category,
    compute_all_profiles,
    compute_aversions,
    compute_favorites,
    compute_live_profile,
    profile_data_from_details,
)
from radarvan.player_profile import (
    _compute_academy_badges,
    _drop_zero_cost_objects,
    _reconcile_unit_building_split,
)
from radarvan.player_synergy import PairSynergy


def _academy(**overrides: int) -> AcademyStats:
    values = dict.fromkeys(AcademyStats.model_fields, 0)
    values.update(overrides)
    return AcademyStats(**values)  # type: ignore[arg-type]


def _means(**overrides: float) -> dict[str, float]:
    """A full academy-means dict (all fields present, defaulting to 0)."""
    values: dict[str, float] = dict.fromkeys(AcademyStats.model_fields, 0.0)
    values.update(overrides)
    return values


def _proj(
    name: str,
    general: General = General.USA,
    won: bool = True,
    units: dict[str, int] | None = None,
    buildings: dict[str, int] | None = None,
    upgrades: dict[str, int] | None = None,
    powers: dict[str, int] | None = None,
    unit_spent: dict[str, int] | None = None,
    building_spent: dict[str, int] | None = None,
    upgrade_spent: dict[str, int] | None = None,
    apm: float | None = None,
    got_first_blood: bool = False,
    time_to_rank_5: float | None = None,
    academy: AcademyStats | None = None,
    superweapons_built: int = 0,
) -> PlayerMatchProjection:
    units = units or {}
    buildings = buildings or {}
    upgrades = upgrades or {}
    # Cost defaults to nonzero (a normal, purchasable object) unless a test
    # explicitly wants to simulate a free/automatic object via unit_spent={}.
    return PlayerMatchProjection(
        name=name,
        general=general,
        won=won,
        units=units,
        buildings=buildings,
        upgrades=upgrades,
        powers=powers or {},
        unit_spent=unit_spent if unit_spent is not None else dict.fromkeys(units, 100),
        building_spent=(
            building_spent
            if building_spent is not None
            else dict.fromkeys(buildings, 100)
        ),
        upgrade_spent=(
            upgrade_spent if upgrade_spent is not None else dict.fromkeys(upgrades, 100)
        ),
        apm=apm,
        got_first_blood=got_first_blood,
        time_to_rank_5=time_to_rank_5,
        academy=academy,
        superweapons_built=superweapons_built,
    )


def _matches(per_match_players: list[list[PlayerMatchProjection]]) -> list[ProfileMatchData]:
    return [
        ProfileMatchData(match_id=i, players=players)
        for i, players in enumerate(per_match_players)
    ]


class TestFavoriteScoring:
    def _three_player_data(self) -> list[ProfileMatchData]:
        """12 games, all USA. A builds 4 Quads/game vs peers' 1; everyone
        builds 10 Tanks/game; A builds 30 workers/game (raw max by far)."""
        games = []
        for _ in range(12):
            games.append(
                [
                    _proj(
                        "A",
                        units={
                            "AmericaTankQuad": 4,
                            "AmericaTankCrusader": 10,
                            "GLAInfantryWorker": 30,
                        },
                    ),
                    _proj(
                        "B",
                        units={"AmericaTankQuad": 1, "AmericaTankCrusader": 10},
                    ),
                    _proj(
                        "C",
                        units={"AmericaTankQuad": 1, "AmericaTankCrusader": 10},
                    ),
                ]
            )
        return _matches(games)

    def test_favorite_is_normalized_not_raw_max(self) -> None:
        agg = aggregate_category(self._three_player_data(), ObjectCategory.UNITS)
        favorites = compute_favorites(agg, ObjectCategory.UNITS)
        # The worker (raw max, economy) is excluded; the common tank scores
        # ~1.0; the Quad, built 4x the peer rate, is the signature unit.
        assert favorites["A"].object_name == "TankQuad"
        assert favorites["A"].player_rate == 4.0
        assert favorites["A"].peer_rate == 1.0
        assert favorites["A"].score > 1.25
        # B and C build nothing above the peer rate: no favorite.
        assert "B" not in favorites
        assert "C" not in favorites

    def test_common_object_scores_neutral(self) -> None:
        agg = aggregate_category(self._three_player_data(), ObjectCategory.UNITS)
        count_by_player_obj = {
            (p, o): c for (p, g, o), c in agg.counts.items()
        }
        assert count_by_player_obj[("A", "AmericaTankCrusader")] == 120
        favorites = compute_favorites(agg, ObjectCategory.UNITS, min_score=0.0)
        # Even with the score gate removed, the Quad outranks the Tank for A.
        assert favorites["A"].object_name == "TankQuad"

    def test_no_favorite_without_peers(self) -> None:
        # Only one player ever plays this general: no peer baseline.
        games = [[_proj("A", general=General.TOXIN, units={"Scorpion": 5})]] * 12
        agg = aggregate_category(_matches(games), ObjectCategory.UNITS)
        assert compute_favorites(agg, ObjectCategory.UNITS) == {}

    def test_min_games_gate(self) -> None:
        # A has only 9 games on the general: below the 10-game gate.
        games = [
            [_proj("A", units={"X": 5}), _proj("B", units={}), _proj("C", units={})]
        ] * 9
        agg = aggregate_category(_matches(games), ObjectCategory.UNITS)
        assert "A" not in compute_favorites(agg, ObjectCategory.UNITS)

    def test_unique_object_score_capped(self) -> None:
        # Only A ever builds the Avenger (regularly): score caps at 100.
        games = [
            [
                _proj("A", units={"AmericaVehicleAvenger": 3}),
                _proj("B", units={}),
                _proj("C", units={}),
            ]
        ] * 12
        agg = aggregate_category(_matches(games), ObjectCategory.UNITS)
        favorites = compute_favorites(agg, ObjectCategory.UNITS)
        assert favorites["A"].object_name == "VehicleAvenger"
        assert favorites["A"].peer_rate == 0.0
        assert favorites["A"].score <= 100

    def test_cross_faction_object_is_not_a_favorite(self) -> None:
        # A (playing China) regularly builds GLA Scorpions via a captured Arms
        # Dealer - a foreign-faction unit must never be the signature pick.
        games = [
            [
                _proj("A", general=General.CHINA, units={"GLATankScorpion": 3}),
                _proj("B", general=General.CHINA, units={}),
                _proj("C", general=General.CHINA, units={}),
            ]
        ] * 12
        agg = aggregate_category(_matches(games), ObjectCategory.UNITS)
        assert "A" not in compute_favorites(agg, ObjectCategory.UNITS)

    def test_nameless_cross_faction_object_falls_back_to_usage_dominance(self) -> None:
        # "Upgrade_StealthComanche" carries no faction word at all (Comanche
        # is a USA unit, but its name doesn't say "America"), so the name
        # check can't catch a China player using it via a captured Airfield.
        # Usage dominance must still exclude it: 24 America uses vs 6 China.
        games = []
        for _ in range(24):
            games.append(
                [_proj("Usa", general=General.AIR, upgrades={"Upgrade_StealthComanche": 1})]
            )
        for _ in range(12):
            games.append(
                [_proj("A", general=General.CHINA, upgrades={"Upgrade_StealthComanche": 1})]
            )
        for _ in range(12):
            games.append([_proj("A", general=General.CHINA, upgrades={})])
        agg = aggregate_category(_matches(games), ObjectCategory.UPGRADES)
        favorites = compute_favorites(agg, ObjectCategory.UPGRADES, min_count=3)
        assert "A" not in favorites

    def test_genuinely_neutral_nameless_object_excluded_from_everyone(self) -> None:
        # No faction word AND no usage-dominant faction (used evenly across
        # every faction that plays it): not attributable to any one general,
        # so it can't be anyone's favorite - matches how powers already
        # behave. A2/B2/C2 give each general a peer so the peer-count gate
        # doesn't hide the faction check being exercised.
        games = []
        for _ in range(20):
            games.append(
                [
                    _proj("A", general=General.CHINA, units={"dummy": 3}),
                    _proj("A2", general=General.CHINA, units={}),
                    _proj("B", general=General.GLA, units={"dummy": 3}),
                    _proj("B2", general=General.GLA, units={}),
                    _proj("C", general=General.USA, units={"dummy": 3}),
                    _proj("C2", general=General.USA, units={}),
                ]
            )
        agg = aggregate_category(_matches(games), ObjectCategory.UNITS)
        favorites = compute_favorites(agg, ObjectCategory.UNITS, min_count=3)
        assert favorites == {}

    def test_rare_novelty_is_not_a_favorite(self) -> None:
        # A builds a unique object only 0.25/game: under the rate floor, so
        # the ratio (infinite vs peers) doesn't make it the signature unit.
        games = []
        for i in range(20):
            games.append(
                [
                    _proj("A", units={"NoveltyBike": 1} if i < 5 else {}),
                    _proj("B", units={}),
                    _proj("C", units={}),
                ]
            )
        agg = aggregate_category(_matches(games), ObjectCategory.UNITS)
        assert "A" not in compute_favorites(agg, ObjectCategory.UNITS)

    def test_powers_category_uses_power_cleaner(self) -> None:
        games = [
            [
                _proj("A", powers={"SuperweaponChinaCarpetBomb": 2}),
                _proj("B", powers={}),
                _proj("C", powers={}),
            ]
        ] * 12
        agg = aggregate_category(_matches(games), ObjectCategory.POWERS)
        favorites = compute_favorites(agg, ObjectCategory.POWERS, min_count=3)
        assert favorites["A"].object_name == "CarpetBomb"


class TestAversions:
    def test_flags_avoided_object(self) -> None:
        games = []
        for i in range(16):
            games.append(
                [
                    _proj(
                        "B",
                        units={"AmericaVehicleGattling": 2}
                        | ({"Rare": 1} if i < 4 else {}),
                    ),
                    _proj("C", units={"AmericaVehicleGattling": 2}),
                ]
            )
        for _ in range(12):
            games.append([_proj("A", units={"SomethingElse": 3})])
        agg = aggregate_category(_matches(games), ObjectCategory.UNITS)
        aversions = compute_aversions(agg, ObjectCategory.UNITS)
        names = [s.object_name for s in aversions["A"]]
        # Peers build the Gattling 2/game; A never does.
        assert "VehicleGattling" in names
        # "Rare" (0.125/game) is under the 0.5/game peer-rate floor.
        assert "Rare" not in names

    def test_cross_faction_object_is_not_an_aversion(self) -> None:
        # Peers (playing China) build captured GLA Quad Cannons often; A never
        # does - but China can't normally build them, so it's not an aversion.
        games = []
        for _ in range(16):
            games.append(
                [
                    _proj(
                        "B",
                        general=General.CHINA,
                        units={"GLAVehicleQuadCannon": 2},
                    ),
                    _proj(
                        "C",
                        general=General.CHINA,
                        units={"GLAVehicleQuadCannon": 2},
                    ),
                ]
            )
        for _ in range(12):
            games.append([_proj("A", general=General.CHINA, units={"Other": 1})])
        agg = aggregate_category(_matches(games), ObjectCategory.UNITS)
        assert not compute_aversions(agg, ObjectCategory.UNITS).get("A")

    def test_nameless_cross_faction_upgrade_is_not_an_aversion(self) -> None:
        # Same Comanche-upgrade scenario as the favorites test (70/30 USA-
        # dominant, clears the 65% threshold), checking the aversion side:
        # China peers who occasionally get it via a captured Airfield must
        # not make "never gets it" an aversion for other China players,
        # since it isn't a China-general thing at all.
        games = []
        for _ in range(70):
            games.append(
                [
                    _proj(
                        "Usa", general=General.AIR,
                        upgrades={"Upgrade_StealthComanche": 1},
                    )
                ]
            )
        for _ in range(30):
            games.append(
                [
                    _proj(
                        "ChinaGifted", general=General.CHINA,
                        upgrades={"Upgrade_StealthComanche": 1},
                    )
                ]
            )
        for _ in range(12):
            games.append([_proj("A", general=General.CHINA, upgrades={})])
        agg = aggregate_category(_matches(games), ObjectCategory.UPGRADES)
        assert not compute_aversions(agg, ObjectCategory.UPGRADES).get("A")

    def test_foreign_dominant_power_is_not_an_aversion(self) -> None:
        # Laser-guided missiles is a USA unit ability; China players only use
        # it via gifted units. Even when China peers gift-use it above the
        # rate floor, a China player who never does must not get it as an
        # aversion (the power's usage is USA-dominant).
        power = {"SpecialAbilityMissileDefenderLaserGuidedMissiles": 1}
        games = []
        for _ in range(40):
            games.append(
                [
                    _proj("UsaMain", general=General.SUPER, powers={
                        "SpecialAbilityMissileDefenderLaserGuidedMissiles": 10
                    }),
                    _proj("ChinaGifted", general=General.CHINA, powers=power),
                ]
            )
        for _ in range(12):
            games.append([_proj("A", general=General.CHINA, powers={})])
        agg = aggregate_category(_matches(games), ObjectCategory.POWERS)
        assert not compute_aversions(agg, ObjectCategory.POWERS).get("A")
        # And the gift user must not get it as a favorite either.
        favorites = compute_favorites(agg, ObjectCategory.POWERS, min_count=3)
        assert "ChinaGifted" not in favorites

    def test_neutral_power_is_excluded_entirely(self) -> None:
        # A power used evenly across factions has no dominant owner (e.g.
        # GPSScrambler in this community): a per-general framing for it is
        # meaningless, so it is neither a favorite nor an aversion.
        games = []
        for _ in range(40):
            games.append(
                [
                    _proj("ChinaHabit", general=General.CHINA,
                          powers={"SuperweaponGPSScrambler": 2}),
                    _proj("GlaHabit", general=General.GLA,
                          powers={"SuperweaponGPSScrambler": 2}),
                ]
            )
        for _ in range(12):
            games.append([_proj("A", general=General.CHINA, powers={})])
        agg = aggregate_category(_matches(games), ObjectCategory.POWERS)
        assert not compute_aversions(agg, ObjectCategory.POWERS).get("A")
        favorites = compute_favorites(agg, ObjectCategory.POWERS, min_count=3)
        assert "ChinaHabit" not in favorites
        assert "GlaHabit" not in favorites

    def test_building_some_is_not_aversion(self) -> None:
        games = []
        for _ in range(16):
            games.append(
                [
                    _proj("B", units={"Gattling": 2}),
                    _proj("C", units={"Gattling": 2}),
                ]
            )
        # A builds 1.5/game: above half the peer rate, so not avoided.
        for _ in range(12):
            games.append([_proj("A", units={"Gattling": 2, "Other": 1})])
        agg = aggregate_category(_matches(games), ObjectCategory.UNITS)
        aversions = compute_aversions(agg, ObjectCategory.UNITS)
        assert not aversions.get("A")


class TestComputeAcademyBadges:
    def test_top_three_get_gold_silver_bronze(self) -> None:
        means = {
            "A": _means(heroes_built=5.0),
            "B": _means(heroes_built=3.0),
            "C": _means(heroes_built=1.0),
            "D": _means(heroes_built=0.5),
        }
        badges = _compute_academy_badges(means)
        assert (badges["A"][0].rank, badges["A"][0].tier) == (1, "gold")
        assert (badges["B"][0].rank, badges["B"][0].tier) == (2, "silver")
        assert (badges["C"][0].rank, badges["C"][0].tier) == (3, "bronze")
        assert "D" not in badges
        assert badges["A"][0].total_players == 4
        assert badges["A"][0].value == 5.0

    def test_zero_value_never_medals(self) -> None:
        means = {"A": _means(heroes_built=5.0), "B": _means(heroes_built=0.0)}
        badges = _compute_academy_badges(means)
        assert "B" not in badges

    def test_fewer_than_three_candidates_awards_fewer_medals(self) -> None:
        means = {"A": _means(heroes_built=5.0), "B": _means(heroes_built=3.0)}
        badges = _compute_academy_badges(means)
        assert badges["A"][0].tier == "gold"
        assert badges["B"][0].tier == "silver"
        assert badges["A"][0].total_players == 2
        assert not any(
            bg.tier == "bronze" for player in badges.values() for bg in player
        )

    def test_ties_break_alphabetically(self) -> None:
        means = {"Zed": _means(heroes_built=5.0), "Ann": _means(heroes_built=5.0)}
        badges = _compute_academy_badges(means)
        assert badges["Ann"][0].rank == 1
        assert badges["Zed"][0].rank == 2

    def test_a_player_can_medal_in_multiple_stats(self) -> None:
        means = {
            "A": _means(heroes_built=5.0, mines_cleared=9.0),
            "B": _means(heroes_built=1.0, mines_cleared=1.0),
        }
        badges = _compute_academy_badges(means)
        assert {bg.key for bg in badges["A"]} == {"heroes_built", "mines_cleared"}


class TestComputeAllProfiles:
    def _population(self) -> list[ProfileMatchData]:
        games = []
        for _ in range(12):
            games.append(
                [
                    _proj(
                        "A",
                        apm=100.0,
                        got_first_blood=True,
                        time_to_rank_5=10.0,
                        academy=_academy(heroes_built=3),
                        superweapons_built=1,
                    ),
                    _proj(
                        "B",
                        apm=50.0,
                        time_to_rank_5=8.0,
                        academy=_academy(heroes_built=1),
                    ),
                    _proj("C", apm=30.0, academy=_academy()),
                ]
            )
        return _matches(games)

    def test_percentiles_and_badges(self) -> None:
        profiles = compute_all_profiles(self._population(), min_profile_games=5)
        a, b, c = profiles["A"], profiles["B"], profiles["C"]

        assert a.avg_apm == 100.0
        assert a.apm_percentile == 100.0
        assert b.apm_percentile == 50.0
        assert c.apm_percentile == 0.0

        assert a.first_blood_rate == 1.0
        assert a.first_blood_percentile == 100.0

        # Lower time-to-rank-5 is better; C never ranked (no percentile).
        assert b.rank_5_percentile == 100.0
        assert a.rank_5_percentile == 0.0
        assert c.rank_5_percentile is None

        assert a.superweapons_built_per_game == 1.0
        assert a.superweapon_percentile == 100.0

        # Medals: A built more heroes than B (gold), B is still second among
        # the two players who ever built any (silver); C never did (no medal
        # at all - and C's other zero-valued academy fields never medal).
        a_heroes = next(bg for bg in a.badges if bg.key == "heroes_built")
        b_heroes = next(bg for bg in b.badges if bg.key == "heroes_built")
        assert (a_heroes.rank, a_heroes.tier) == (1, "gold")
        assert (b_heroes.rank, b_heroes.tier) == (2, "silver")
        assert a_heroes.total_players == 2
        assert c.badges == []

        assert a.games_analyzed == 12

    def test_min_profile_games_gate(self) -> None:
        profiles = compute_all_profiles(self._population(), min_profile_games=13)
        assert profiles == {}

    def test_favorites_ignore_below_threshold_peers(self) -> None:
        # Guest plays only 5 games but builds a Quad Cannon every game -
        # an extreme, unrepresentative rate. A and B are the active (>=20
        # games, satisfying the default min_peer_games too) population;
        # Guest must not set their peer bar.
        games = []
        for _ in range(20):
            games.append(
                [
                    _proj("A", units={"AmericaTankQuad": 4}),
                    _proj("B", units={"AmericaTankQuad": 1}),
                ]
            )
        for _ in range(5):
            games.append([_proj("Guest", units={"AmericaTankQuad": 20})])
        profiles = compute_all_profiles(_matches(games), min_profile_games=20)
        assert set(profiles) == {"A", "B"}
        # Peer rate for A must come from B (1/game) alone, not from Guest's 20/game.
        fav = profiles["A"].favorite_unit
        assert fav is not None
        assert fav.peer_per_game == 1.0


def _live_match(
    match_id: int,
    *,
    team1: list[str],
    team2: list[str],
    team1_won: bool,
    general: General = General.AIR,
    map_path: str = "maps/alpha",
    duration: float = 10.0,
) -> MatchInfo:
    colors = ["red", "blue", "green", "violet"]
    players = [
        Player(
            name=n,
            general=general,
            team=Team.ONE,
            color=colors[i % 4],
            won=team1_won,
        )
        for i, n in enumerate(team1)
    ] + [
        Player(
            name=n,
            general=General.NUKE,
            team=Team.TWO,
            color=colors[(i + 2) % 4],
            won=not team1_won,
        )
        for i, n in enumerate(team2)
    ]
    return MatchInfo(
        id=match_id,
        timestamp=datetime(2026, 1, 1, 12, 0, 0),
        date=date(2026, 1, 1),
        map=map_path,
        winning_team=Team.ONE if team1_won else Team.TWO,
        players=players,
        duration_minutes=duration,
        filename=f"game_{match_id}.rep",
    )


class TestLiveProfile:
    def _games(self) -> list[MatchInfo]:
        games = []
        mid = 0
        # 12 games vs C+D: Alice wins 3.
        for i in range(12):
            games.append(
                _live_match(
                    (mid := mid + 1),
                    team1=["Alice", "Bob"],
                    team2=["Carol", "Dave"],
                    team1_won=i < 3,
                    duration=10.0 if i < 3 else 20.0,
                )
            )
        # 12 games vs E+F: Alice wins 10.
        for i in range(12):
            games.append(
                _live_match(
                    (mid := mid + 1),
                    team1=["Alice", "Bob"],
                    team2=["Eve", "Frank"],
                    team1_won=i < 10,
                    map_path="maps/bravo",
                    duration=10.0 if i < 10 else 20.0,
                )
            )
        return games

    def test_record_generals_maps_tempo(self) -> None:
        profile = compute_live_profile(self._games(), "Alice")
        assert (profile.games, profile.wins, profile.losses) == (24, 13, 11)

        assert profile.most_played_general is not None
        assert profile.most_played_general.general == General.AIR
        assert profile.most_played_general.games == 24
        assert profile.best_general is not None
        assert profile.best_general.general == General.AIR

        assert profile.favorite_map is not None
        assert profile.favorite_map.games == 12
        assert profile.best_map is not None
        assert profile.best_map.map == "bravo"  # 10/12 beats 3/12

        assert profile.avg_win_duration_minutes == 10.0
        assert profile.avg_loss_duration_minutes == 20.0

    def test_nemesis_and_victim(self) -> None:
        profile = compute_live_profile(self._games(), "Alice")
        assert profile.nemesis is not None
        assert profile.nemesis.name in ("Carol", "Dave")
        assert (profile.nemesis.wins, profile.nemesis.losses) == (3, 9)
        assert profile.favorite_victim is not None
        assert profile.favorite_victim.name in ("Eve", "Frank")
        assert (profile.favorite_victim.wins, profile.favorite_victim.losses) == (10, 2)

    def test_teammate_fallback_most_games(self) -> None:
        profile = compute_live_profile(self._games(), "Alice")
        assert profile.favorite_teammate is not None
        assert profile.favorite_teammate.name == "Bob"
        assert profile.favorite_teammate.games_together == 24
        assert profile.favorite_teammate.wins_together == 13
        assert profile.favorite_teammate.synergy is None

    def test_teammate_from_synergy(self) -> None:
        pair = PairSynergy(
            player_a="Alice",
            player_b="Bob",
            synergy=0.42,
            win_prob_delta=0.1,
            games_together=24,
            wins_together=13,
            expected_wins=11.0,
            std_error=0.2,
            z_score=2.1,
            games_apart=0,
            main_a=0.0,
            main_b=0.0,
            adjusted_expected_wins=11.5,
        )
        profile = compute_live_profile(self._games(), "Alice", synergy_pairs=[pair])
        assert profile.favorite_teammate is not None
        assert profile.favorite_teammate.name == "Bob"
        assert profile.favorite_teammate.synergy == 0.42

    def test_player_not_in_games(self) -> None:
        profile = compute_live_profile(self._games(), "Nobody")
        assert profile.games == 0
        assert profile.generals == []
        assert profile.nemesis is None


class TestReconcileUnitBuildingSplit:
    def test_moves_minority_occurrences_to_dominant_category(self) -> None:
        # cncstats logs "Outpost" as a building 1/6 of the time overall
        # (dominant = unit); every occurrence must end up under units.
        games = _matches(
            [
                [_proj("A", units={"Outpost": 5})],
                [_proj("B", buildings={"Outpost": 1})],
            ]
        )
        fixed = _reconcile_unit_building_split(games)
        for match in fixed:
            for proj in match.players:
                assert "Outpost" not in proj.buildings
        by_name = {p.name: p for m in fixed for p in m.players}
        assert by_name["A"].units["Outpost"] == 5
        assert by_name["B"].units["Outpost"] == 1

    def test_reversed_when_buildings_dominate(self) -> None:
        games = _matches(
            [
                [_proj("A", buildings={"Weird": 9})],
                [_proj("B", units={"Weird": 1})],
            ]
        )
        fixed = _reconcile_unit_building_split(games)
        by_name = {p.name: p for m in fixed for p in m.players}
        assert "Weird" not in by_name["B"].units
        assert by_name["B"].buildings["Weird"] == 1
        assert by_name["A"].buildings["Weird"] == 9

    def test_unambiguous_objects_untouched(self) -> None:
        games = _matches(
            [[_proj("A", units={"Tank": 3}, buildings={"WarFactory": 1})]]
        )
        fixed = _reconcile_unit_building_split(games)
        proj = fixed[0].players[0]
        assert proj.units == {"Tank": 3}
        assert proj.buildings == {"WarFactory": 1}

    def test_merges_into_an_existing_count_in_the_dominant_dict(self) -> None:
        # B already has 2 real Outposts as a unit; the 1 misclassified
        # building occurrence must add into that same count, not overwrite it.
        games = _matches(
            [
                [_proj("A", units={"Outpost": 5})],
                [_proj("B", units={"Outpost": 2}, buildings={"Outpost": 1})],
            ]
        )
        fixed = _reconcile_unit_building_split(games)
        by_name = {p.name: p for m in fixed for p in m.players}
        assert by_name["B"].units["Outpost"] == 3
        assert "Outpost" not in by_name["B"].buildings

    def test_end_to_end_favorite_uses_reconciled_category(self) -> None:
        # Without reconciliation, A's Outpost count is split 5 unit / 12
        # building and could spuriously become a "favorite building"; after
        # reconciliation all 17 land under units where they belong.
        games = []
        for _ in range(12):
            games.append([_proj("A", buildings={"Outpost": 1})])
        for _ in range(12):
            games.append(
                [
                    _proj("A", units={"Outpost": 1}),
                    _proj("B", units={}),
                ]
            )
        for _ in range(20):
            games.append([_proj("B", units={})])
        profiles = compute_all_profiles(_matches(games), min_profile_games=12)
        assert profiles["A"].favorite_building is None
        fav = profiles["A"].favorite_unit
        assert fav is not None
        assert fav.name == "Outpost"


class TestDropZeroCostObjects:
    def test_drops_object_that_never_costs_anything(self) -> None:
        # HoleTunnelNetwork is always logged with TotalSpent 0 - a free,
        # automatically-spawned exit point, not something the player built.
        games = _matches(
            [
                [
                    _proj(
                        "A",
                        buildings={"HoleTunnelNetwork": 4, "WarFactory": 1},
                        building_spent={"HoleTunnelNetwork": 0, "WarFactory": 800},
                    )
                ],
            ]
        )
        fixed = _drop_zero_cost_objects(games)
        proj = fixed[0].players[0]
        assert "HoleTunnelNetwork" not in proj.buildings
        assert "HoleTunnelNetwork" not in proj.building_spent
        assert proj.buildings == {"WarFactory": 1}

    def test_object_with_any_nonzero_spend_is_kept(self) -> None:
        # If the object ever costs something anywhere in the data, it's real.
        games = _matches(
            [
                [_proj("A", buildings={"Radar": 1}, building_spent={"Radar": 0})],
                [_proj("B", buildings={"Radar": 1}, building_spent={"Radar": 500})],
            ]
        )
        fixed = _drop_zero_cost_objects(games)
        by_name = {p.name: p for m in fixed for p in m.players}
        assert by_name["A"].buildings == {"Radar": 1}
        assert by_name["B"].buildings == {"Radar": 1}

    def test_units_and_upgrades_also_checked(self) -> None:
        games = _matches(
            [
                [
                    _proj(
                        "A",
                        units={"FreeScout": 1},
                        unit_spent={"FreeScout": 0},
                        upgrades={"FreeUpgrade": 1},
                        upgrade_spent={"FreeUpgrade": 0},
                    )
                ],
            ]
        )
        fixed = _drop_zero_cost_objects(games)
        proj = fixed[0].players[0]
        assert proj.units == {}
        assert proj.upgrades == {}

    def test_powers_are_unaffected(self) -> None:
        # Powers have no cost field; the filter must not touch them.
        games = _matches([[_proj("A", powers={"SomePower": 3})]])
        fixed = _drop_zero_cost_objects(games)
        assert fixed[0].players[0].powers == {"SomePower": 3}

    def test_end_to_end_free_object_never_a_favorite(self) -> None:
        games = []
        for _ in range(20):
            games.append(
                [
                    _proj(
                        "A",
                        buildings={"HoleTunnelNetwork": 10, "SupplyStash": 1},
                        building_spent={"HoleTunnelNetwork": 0, "SupplyStash": 500},
                    ),
                    _proj("B", buildings={"SupplyStash": 1}, building_spent={"SupplyStash": 500}),
                ]
            )
        profiles = compute_all_profiles(_matches(games), min_profile_games=20)
        fav = profiles["A"].favorite_building
        assert fav is None or fav.name != "HoleTunnelNetwork"


class TestProjection:
    def test_projection_from_reference_fixture(self) -> None:
        replay = EnhancedReplayV2.model_validate(
            json.load(open("references/example_cncstats_output.json"))
        )
        details = match_details_from_replay(replay)
        assert details is not None
        players = [
            Player(
                name=ps.Name,
                general=General.AIR,
                team=Team(ps.Team),
                color=ps.Color,
                won=ps.Win,
            )
            for ps in details.player_summary
        ]
        info = MatchInfo(
            id=details.match_id,
            timestamp=datetime(2026, 1, 1, 12, 0, 0),
            date=date(2026, 1, 1),
            map="maps/test",
            winning_team=Team.ONE,
            players=players,
            duration_minutes=20.0,
            filename="x.rep",
        )
        data = profile_data_from_details(details, info)
        assert data.match_id == details.match_id
        assert len(data.players) == len(details.player_summary)

        by_name = {p.name: p for p in data.players}
        for ps in details.player_summary:
            proj = by_name[resolve_player_name(ps.Name, ps.Color)]
            assert proj.units == {k: v.Count for k, v in ps.UnitsCreated.items()}
            assert proj.buildings == {
                k: v.Count for k, v in ps.BuildingsBuilt.items()
            }
            assert proj.powers == ps.PowersUsed

    def test_cpu_and_observer_excluded(self) -> None:
        def summary(name: str, team: int) -> PlayerSummary:
            return PlayerSummary(
                Name=name,
                Side="USA",
                Team=team,
                Win=False,
                Color="red",
                UnitsCreated={"X": ObjectSummary(Count=1, TotalSpent=100)},
                BuildingsBuilt={},
                UpgradesBuilt={},
                PowersUsed={},
            )

        details = MatchDetails(
            match_id=1,
            costs=[],
            apms=[],
            upgrade_events={},
            stats_data={},
            player_summary=[summary("Human", 1), summary("cpu", 1)],
        )
        players = [
            Player(name="Human", general=General.USA, team=Team.ONE, color="red"),
            Player(name="cpu", general=General.USA, team=Team.ONE, color="blue"),
            Player(
                name="Watcher",
                general=General.USA,
                team=Team.OBSERVER,
                color="green",
            ),
        ]
        info = MatchInfo(
            id=1,
            timestamp=datetime(2026, 1, 1),
            date=date(2026, 1, 1),
            map="maps/test",
            winning_team=Team.TWO,
            players=players,
            duration_minutes=5.0,
            filename="x.rep",
        )
        data = profile_data_from_details(details, info)
        assert [p.name for p in data.players] == ["Human"]


def test_profile_version_format() -> None:
    logic, schema_hash = PROFILE_VERSION.split("-")
    assert logic.isdigit()
    assert len(schema_hash) == 12
