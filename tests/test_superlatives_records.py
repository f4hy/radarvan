"""The records added to, and reshaped on, the Records page.

Covers who is allowed to hold a record (`holds_records`), the corpus-derived
records that need no match details (streaks, attendance, duos, rating peaks,
upsets), the duration floor on the efficiency records, and the
superweapon/tech records read off the timeline.
"""

from datetime import date

import pytest

from radarvan.api_types import (
    MatchDetails,
    SuperlativeData,
    SuperlativePlayerSummary,
    SuperweaponLaunch,
    TimelineEvent,
)
from radarvan import player_rating
from radarvan.player_rating import GameUpset
from radarvan.superlatives import (
    MIN_EFFICIENCY_MINUTES,
    get_attendance_stats,
    get_duo_stats,
    get_efficiency_stats,
    get_superweapon_stats,
    get_tech_capture_stats,
    get_upset_stats,
    get_win_streak_stats,
    holds_records,
    superlative_data_from_details,
)

from corpus import cpu, match, observer

COMPUTED_AT = date(2026, 2, 1)


def _stat(stats: list, name_fragment: str):
    return next((s for s in stats if name_fragment in str(s.stat_name)), None)


# --- who may hold a record -------------------------------------------------


@pytest.mark.parametrize("name", ["Skip", "CoreDawg", "Tytan", "pcap"])
def test_known_humans_hold_records(name: str) -> None:
    assert holds_records(name)


@pytest.mark.parametrize("name", ["HardArmy", "TacticalAI", "MediumArmy", "EasyArmy"])
def test_no_ai_holds_a_record(name: str) -> None:
    """The old check was a one-name blocklist ("HardArmy"), which is why
    "Tactical AI" ended up holding "Worst Record (30d)" on the live page."""
    assert not holds_records(name)


@pytest.mark.parametrize("name", ["domi", "[OoE]ExCaL^", "Gorn.v.131"])
def test_no_stranger_holds_a_record(name: str) -> None:
    """A scraped pickup game passes the competitive filter as long as each team
    has one group member, so passers-by reach the records pass. Two of them
    held "Highest APM" and "Fastest to Rank 5". The caster account is here for
    the same reason - it is a name, not a role, that gives it away."""
    assert not holds_records(name)


# --- streaks ---------------------------------------------------------------


def test_longest_losing_streak_is_the_longest_run_of_losses() -> None:
    # Team two loses matches 1-4, then wins the fifth.
    games = [match(i, day=i) for i in range(1, 5)]
    games.append(match(5, day=5, winner=2))  # type: ignore[arg-type]
    stats = get_win_streak_stats(games, COMPUTED_AT)

    losing = _stat(stats, "Longest Losing Streak")
    assert losing is not None
    assert losing.value == 4
    assert losing.player in ("Syn", "Pancake")


def test_a_win_ends_a_losing_streak() -> None:
    """Two runs of three losses either side of a win is a streak of three, not
    six - the win has to reset the loss counter as well as start a win one."""
    games = [
        match(1, day=1),
        match(2, day=2),
        match(3, day=3),
        match(4, day=4, winner=2),  # type: ignore[arg-type]
        match(5, day=5),
        match(6, day=6),
        match(7, day=7),
    ]
    losing = _stat(get_win_streak_stats(games, COMPUTED_AT), "Longest Losing Streak")
    assert losing is not None
    assert losing.value == 3


def test_watching_does_not_extend_a_losing_streak() -> None:
    """A spectator's slot carries won=False. Reading every slot rather than the
    roster's competitors is the bug that has already booked casters a loss
    twice; the losing streak is a third place it would land.

    Skip wins all three of his own games, then watches three between other
    people. If the observer slot counted, he would leave with a streak of
    three losses instead of none.
    """
    played = [match(i, day=i) for i in range(1, 4)]
    watched = [
        match(
            10 + i,
            day=10 + i,
            team_one=("Neo", "Modus"),
            team_two=("Tytan", "Gorn"),
            extra_players=(observer("Skip"),),
        )
        for i in range(3)
    ]

    def worst(games: list) -> tuple[str, int]:
        stat = _stat(get_win_streak_stats(games, COMPUTED_AT), "Longest Losing Streak")
        assert stat is not None
        return str(stat.player), int(stat.value)  # type: ignore[arg-type]

    holder, count = worst([*played, *watched])
    assert (holder, count) == worst(played)
    assert holder in ("Syn", "Pancake")
    assert count == 3


# --- attendance and game nights --------------------------------------------


def test_most_games_played_counts_human_participants() -> None:
    games = [match(i, day=i) for i in range(1, 4)]
    # One extra game the second team is not in.
    games.append(match(4, day=4, team_two=("Neo", "Modus")))
    stat = _stat(get_attendance_stats(games, COMPUTED_AT), "Most Games Played")
    assert stat is not None
    assert stat.value == 4
    assert stat.player in ("Skip", "CoreDawg")


def test_a_cpu_slot_never_wins_most_games_played() -> None:
    games = [
        match(i, day=i, team_two=("Syn",), extra_players=(cpu(team=2),))  # type: ignore[arg-type]
        for i in range(1, 12)
    ]
    stat = _stat(get_attendance_stats(games, COMPUTED_AT), "Most Games Played")
    assert stat is not None
    assert stat.player != "TacticalAI"


def test_best_game_night_needs_an_undefeated_night() -> None:
    """Four wins and a loss on the same night is not a 4-0."""
    games = [match(i, day=1) for i in range(1, 5)]
    games.append(match(5, day=1, winner=2))  # type: ignore[arg-type]
    assert _stat(get_attendance_stats(games, COMPUTED_AT), "Best Game Night") is None


def test_best_game_night_reports_the_night_and_the_run() -> None:
    games = [match(i, day=7) for i in range(1, 6)]
    stat = _stat(get_attendance_stats(games, COMPUTED_AT), "Best Game Night")
    assert stat is not None
    assert stat.value == "5-0"
    assert "2026-01-07" in str(stat.stat_name)


def test_a_short_night_is_not_a_record() -> None:
    """Two wins is a coin flip, not a run."""
    games = [match(1, day=3), match(2, day=3)]
    assert _stat(get_attendance_stats(games, COMPUTED_AT), "Best Game Night") is None


def test_tied_game_nights_go_to_whoever_got_there_first() -> None:
    early = [match(i, day=5) for i in range(1, 5)]
    late = [match(10 + i, day=9) for i in range(1, 5)]
    stat = _stat(get_attendance_stats([*late, *early], COMPUTED_AT), "Best Game Night")
    assert stat is not None
    assert "2026-01-05" in str(stat.stat_name)


# --- duos ------------------------------------------------------------------


def test_best_duo_needs_enough_games_together() -> None:
    games = [match(i, day=1 + i % 20) for i in range(1, 10)]
    assert get_duo_stats(games, COMPUTED_AT) == []


def test_best_duo_reports_both_names_and_the_record() -> None:
    # Skip & CoreDawg win 20 and lose 5 together.
    games = [match(i, day=1 + i % 20) for i in range(1, 21)]
    games += [match(100 + i, day=1 + i % 20, winner=2) for i in range(5)]  # type: ignore[arg-type]
    stats = get_duo_stats(games, COMPUTED_AT)
    assert len(stats) == 1
    assert "CoreDawg & Skip" in str(stats[0].stat_name)
    assert stats[0].value == "20-5"


def test_a_duo_is_only_counted_on_the_same_team() -> None:
    """Opponents share a match but not a record."""
    games = [match(i, day=1 + i % 20) for i in range(1, 26)]
    stats = get_duo_stats(games, COMPUTED_AT)
    assert len(stats) == 1
    name = str(stats[0].stat_name)
    assert "Syn" not in name and "Pancake" not in name


# --- ratings ---------------------------------------------------------------


def test_no_record_exposes_a_rating_level() -> None:
    """Ratings are admin-only (see CLAUDE.md): the Records page is public, so a
    record may report a rating *change* but never a rating. An all-time peak
    record lived here briefly and had to come out.

    Guarded by feeding the peaks a sentinel no other stat could produce and
    asserting it reaches no card, rather than by naming the record that was
    removed - the next one to reach for `ordinal_high` fails here too.
    """
    from radarvan import superlatives

    games = [match(i, day=1 + i % 20) for i in range(1, 26)]
    ratings = player_rating.compute_player_ratings(games)
    sentinel = 987654.0
    ratings.ordinal_high = dict.fromkeys(ratings.ordinal_high, sentinel)
    ratings.ordinal_low = dict.fromkeys(ratings.ordinal_low, sentinel)
    assert ratings.ordinal_high, "fixture must actually produce peaks to guard"

    for stat in superlatives.get_superlatives(games, None, ratings).stats:
        rendered = f"{stat.stat_name} {stat.value}"
        assert "987654" not in rendered.replace(",", "")
        assert str(round(sentinel * 10)) not in rendered.replace(",", "")


def test_biggest_upset_takes_the_head_of_the_sorted_list() -> None:
    upsets = [
        GameUpset(
            match_id=7,
            at_date=date(2026, 1, 9),
            favored_team=2,
            favored_win_prob=0.9998,
            favored_players=["Tytan", "Neo"],
            winning_team=1,
            winner_win_prob=0.0002,
            winner_players=["Skip", "Pancake"],
        )
    ]
    stats = get_upset_stats(upsets, COMPUTED_AT)
    assert len(stats) == 1
    assert stats[0].match_id == 7
    assert stats[0].value == "0.02% to win"
    assert "Skip & Pancake over Tytan & Neo" in str(stats[0].stat_name)


def test_no_upsets_no_record() -> None:
    assert get_upset_stats([], COMPUTED_AT) == []


# --- efficiency floor ------------------------------------------------------


def _efficiency_details(match_id: int, *, units: int, name: str = "Skip"):
    return SuperlativeData.model_construct(
        match_id=match_id,
        apms=[],
        player_summary=[
            _summary(name=name, won=True, units_created_count=units),
        ],
        upgrade_counts={},
        total_units_killed=0,
        total_buildings_killed=0,
        total_xp=0,
        match_money_spent=0,
        player_money_collected={},
    )


def _summary(*, name: str, won: bool, units_created_count: int):
    return SuperlativePlayerSummary(
        name=name,
        color="red",
        won=won,
        money_spent=5000,
        units_created_count=units_created_count,
        buildings_built_count=8,
    )


def test_a_rage_quit_win_is_not_an_efficiency_record() -> None:
    """Every efficiency record was one of these before the floor: "Fewest Units
    to Win" was 2, in the same match as "⚡ Shortest 4v4" (2m01s)."""
    quit_game = match(1, day=1, duration_minutes=2.0)
    real_game = match(2, day=2, duration_minutes=30.0)
    infos = {g.id: g for g in (quit_game, real_game)}
    details = [
        _efficiency_details(1, units=2),
        _efficiency_details(2, units=40),
    ]
    stat = _stat(get_efficiency_stats(infos, details, COMPUTED_AT), "Fewest Units")
    assert stat is not None
    assert stat.value == 40
    assert stat.match_id == 2


def test_a_win_exactly_on_the_floor_still_counts() -> None:
    game = match(1, day=1, duration_minutes=MIN_EFFICIENCY_MINUTES)
    stat = _stat(
        get_efficiency_stats(
            {game.id: game}, [_efficiency_details(1, units=6)], COMPUTED_AT
        ),
        "Fewest Units",
    )
    assert stat is not None
    assert stat.value == 6


def test_an_incomplete_match_is_not_an_efficiency_record() -> None:
    game = match(1, day=1, duration_minutes=40.0, incomplete="desync")
    assert (
        get_efficiency_stats(
            {game.id: game}, [_efficiency_details(1, units=6)], COMPUTED_AT
        )
        == []
    )


# --- superweapons and tech captures ----------------------------------------


def _details_with_events(match_id: int, events: list[TimelineEvent]) -> SuperlativeData:
    details = MatchDetails.model_construct(
        match_id=match_id,
        costs=[],
        apms=[],
        upgrade_events={},
        stats_data={},
        player_summary=[],
        timeline_events=events,
        player_money_spent={},
        player_money_collected={},
    )
    return superlative_data_from_details(details)


def _event(player: str, name: str, event_type: str, minute: float) -> TimelineEvent:
    return TimelineEvent(
        player_name=player, at_minute=minute, event_name=name, event_type=event_type
    )


def test_only_base_superweapons_count_as_a_launch() -> None:
    """The timeline tags EMP, anthrax and the Spectre gunship
    "superweapon_activated" too, so the chart can mark them - but they are
    generals-panel powers, not superweapons."""
    data = _details_with_events(
        1,
        [
            _event("Skip", "EMPPulse", "superweapon_activated", 5.0),
            _event("Skip", "AnthraxBomb", "superweapon_activated", 6.0),
            _event("Skip", "SpectreGunship", "superweapon_activated", 7.0),
            _event("Skip", "ScudStorm", "superweapon_activated", 8.0),
        ],
    )
    assert data.superweapon_launches == {"Skip": 1}
    assert data.first_superweapon["Skip"] == SuperweaponLaunch(
        weapon="ScudStorm", at_minute=8.0
    )


def test_building_a_superweapon_is_not_launching_one() -> None:
    data = _details_with_events(
        1, [_event("Skip", "ScudStorm", "superweapon_built", 6.0)]
    )
    assert data.superweapon_launches == {}


def test_most_superweapons_launched_takes_the_best_single_match() -> None:
    games = [match(1, day=1), match(2, day=2)]
    details = [
        _details_with_events(
            1,
            [
                _event("Skip", "NeutronMissile", "superweapon_activated", m)
                for m in (10.0, 14.0, 18.0)
            ],
        ),
        _details_with_events(
            2, [_event("Skip", "ParticleCannon", "superweapon_activated", 12.0)]
        ),
    ]
    stat = _stat(
        get_superweapon_stats({g.id: g for g in games}, details, COMPUTED_AT),
        "Most Superweapons",
    )
    assert stat is not None
    assert stat.value == 3
    assert stat.match_id == 1


def test_fastest_superweapon_launch_names_the_weapon() -> None:
    games = [match(1, day=1), match(2, day=2)]
    details = [
        _details_with_events(
            1, [_event("Skip", "NeutronMissile", "superweapon_activated", 14.0)]
        ),
        _details_with_events(
            2, [_event("Syn", "ScudStorm", "superweapon_activated", 9.5)]
        ),
    ]
    stat = _stat(
        get_superweapon_stats({g.id: g for g in games}, details, COMPUTED_AT),
        "Fastest Superweapon",
    )
    assert stat is not None
    assert stat.player == "Syn"
    assert stat.value == "9m 30s"
    assert "ScudStorm" in str(stat.stat_name)


def test_a_stranger_does_not_take_the_superweapon_record() -> None:
    games = [match(1, day=1)]
    details = [
        _details_with_events(
            1,
            [
                *[
                    _event("domi", "ScudStorm", "superweapon_activated", m)
                    for m in (4.0, 5.0, 6.0)
                ],
                _event("Skip", "NeutronMissile", "superweapon_activated", 20.0),
            ],
        )
    ]
    stats = get_superweapon_stats({g.id: g for g in games}, details, COMPUTED_AT)
    assert all(s.player == "Skip" for s in stats)


def test_most_tech_captures_counts_capture_events_per_player() -> None:
    games = [match(1, day=1)]
    details = [
        _details_with_events(
            1,
            [
                *[
                    _event("Skip", "OilDerrick", "tech_capture", m)
                    for m in (4.0, 5.0, 6.0)
                ],
                _event("Syn", "Hospital", "tech_capture", 7.0),
            ],
        )
    ]
    stat = _stat(
        get_tech_capture_stats({g.id: g for g in games}, details, COMPUTED_AT),
        "Tech Captures",
    )
    assert stat is not None
    assert stat.player == "Skip"
    assert stat.value == 3


def test_no_events_no_superweapon_or_tech_records() -> None:
    games = [match(1, day=1)]
    details = [_details_with_events(1, [])]
    infos = {g.id: g for g in games}
    assert get_superweapon_stats(infos, details, COMPUTED_AT) == []
    assert get_tech_capture_stats(infos, details, COMPUTED_AT) == []


# --- what was removed ------------------------------------------------------


def test_only_one_money_podium_survives() -> None:
    """Career money *spent* used to get a podium beside career money collected
    and always named the same three players in the same order."""
    from radarvan.superlatives import get_money_stats, get_player_money_stats

    details = [
        SuperlativeData.model_construct(
            match_id=i,
            apms=[],
            player_summary=[
                _summary(name="Skip", won=True, units_created_count=10),
            ],
            upgrade_counts={},
            total_units_killed=0,
            total_buildings_killed=0,
            total_xp=0,
            match_money_spent=1000 * i,
            player_money_collected={"Skip": 900 * i},
        )
        for i in (1, 2, 3)
    ]
    podium = get_player_money_stats(details, COMPUTED_AT)
    assert [str(s.stat_name) for s in podium] == ["💰 Most Money Collected 🥇"]

    # "Least Money Spent" read $12,200 across a 42-minute 2v2 - a replay whose
    # per-player moneySpent never populated, not a frugal game.
    match_money = get_money_stats(details, COMPUTED_AT)
    assert [str(s.stat_name) for s in match_money] == ["💰 Most Money Spent"]
