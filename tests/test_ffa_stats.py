"""`ffa_stats` - free-for-all leaderboards, and the expected-wins correction.

Win rate alone is meaningless in FFA: the null expectation is 1/N, so a 25% rate
is average in a 4-player game and outstanding in a 10-player one. The module
carries `expected_wins` and `dominance` for that reason, and those are the
numbers most worth pinning - they are arithmetic no endpoint test would catch.

Also pinned: the eligibility predicate. `is_ffa_game` deliberately does *not*
use `competitive_game_filter` (it requires `is_team_game`, which would drop every
FFA), so the "no CPUs" intent is enforced by a separate guard that nothing else
checks - and `include_cpu` is the page toggle that lifts it.
"""

import pytest

from radarvan import ffa_stats
from radarvan.api_types import General

from corpus import FFA_NAMES, MAPS, ffa_match, observer

FOUR = FFA_NAMES[:4]


def _series(n: int, *, names=FOUR, winner_index: int = 0, map_name=None, start=7000):
    return [
        ffa_match(
            start + i,
            day=5 + (i % 23),
            names=names,
            winner_index=winner_index,
            map_name=map_name,
        )
        for i in range(n)
    ]


# --- is_ffa_game ------------------------------------------------------------


def test_a_plain_four_player_ffa_counts() -> None:
    assert ffa_stats.is_ffa_game(ffa_match(1, day=5, names=FOUR))


def test_an_incomplete_ffa_does_not_count() -> None:
    assert not ffa_stats.is_ffa_game(
        ffa_match(1, day=5, names=FOUR, incomplete="Disconnect")
    )


def test_a_team_game_is_not_an_ffa() -> None:
    from corpus import match

    assert not ffa_stats.is_ffa_game(match(1, day=5))


def test_an_ffa_containing_any_cpu_does_not_count() -> None:
    """Comp-stomps and mixed games are excluded so the stats are player-vs-player."""
    assert not ffa_stats.is_ffa_game(ffa_match(1, day=5, names=FOUR, num_computers=1))


@pytest.mark.parametrize("size,expected", [(2, False), (3, True)])
def test_three_players_is_the_floor(size: int, expected: bool) -> None:
    assert (
        ffa_stats.is_ffa_game(ffa_match(1, day=5, names=FFA_NAMES[:size])) is expected
    )


# --- headline aggregates ----------------------------------------------------


def test_totals_count_only_eligible_games() -> None:
    games = _series(3)
    games.append(ffa_match(7900, day=25, names=FOUR, incomplete="Disconnect"))
    games.append(ffa_match(7901, day=26, names=FOUR, num_computers=2))
    stats = ffa_stats.get_ffa_stats(games)
    assert stats.total_games == 3
    assert stats.distinct_players == 4
    assert stats.avg_players_per_game == 4.0


def test_expected_wins_is_one_over_the_field_size() -> None:
    """Eight 4-player FFAs: each entrant is 'owed' 8 * 1/4 = 2 wins."""
    stats = ffa_stats.get_ffa_stats(_series(8, winner_index=0))
    by_name = {s.name: s for s in stats.player_stats}
    assert by_name[FOUR[0]].expected_wins == pytest.approx(2.0)
    assert by_name[FOUR[1]].expected_wins == pytest.approx(2.0)


def test_dominance_is_actual_over_expected() -> None:
    """The player who won all eight of their eight 4-player games is 8/2 = 4x."""
    stats = ffa_stats.get_ffa_stats(_series(8, winner_index=0))
    by_name = {s.name: s for s in stats.player_stats}
    assert by_name[FOUR[0]].wins == 8
    assert by_name[FOUR[0]].win_rate == pytest.approx(1.0)
    assert by_name[FOUR[0]].dominance == pytest.approx(4.0)
    assert by_name[FOUR[1]].dominance == pytest.approx(0.0)


def test_expected_wins_tracks_field_size_not_game_count() -> None:
    """The whole point of the correction: a win in a big FFA is worth more."""
    small = ffa_stats.get_ffa_stats(_series(8, names=FFA_NAMES[:4], winner_index=0))
    large = ffa_stats.get_ffa_stats(_series(8, names=FFA_NAMES[:8], winner_index=0))
    small_dom = {s.name: s.dominance for s in small.player_stats}[FOUR[0]]
    large_dom = {s.name: s.dominance for s in large.player_stats}[FOUR[0]]
    assert large_dom > small_dom, (
        "winning every 8-player FFA should read as more dominant than winning "
        "every 4-player one, but the correction did not apply"
    )
    assert large_dom == pytest.approx(8.0)


def test_a_player_under_the_game_threshold_is_not_listed() -> None:
    """`MIN_PLAYER_GAMES` is inclusive: 8 games qualifies, 7 does not."""
    assert ffa_stats.get_ffa_stats(_series(7)).player_stats == []
    assert ffa_stats.get_ffa_stats(_series(8)).player_stats != []


def test_totals_still_count_players_who_miss_the_leaderboard() -> None:
    stats = ffa_stats.get_ffa_stats(_series(3))
    assert stats.player_stats == []
    assert stats.distinct_players == 4, (
        "the threshold is a display filter; it must not change the totals"
    )


def test_players_are_ranked_by_wins_then_dominance() -> None:
    games = _series(8, winner_index=0) + _series(8, winner_index=1, start=7100)
    stats = ffa_stats.get_ffa_stats(games)
    ranked = [(s.wins, s.dominance) for s in stats.player_stats]
    assert ranked == sorted(ranked, reverse=True)


# --- generals and maps ------------------------------------------------------


def test_unrecognized_generals_are_left_off_the_general_table() -> None:
    """Two separate guards enforce this, and only one of them is reachable.

    `entries` already drops any slot failing `has_known_general` (general < 0),
    so `General.UNRECOGNIZED` can never reach `gen_games` and the
    `general != General.UNRECOGNIZED` filter in the comprehension below is
    unreachable. This asserts the outcome rather than either guard, so it stays
    true if the redundant one is removed.
    """
    games = [
        ffa_match(
            7200 + i,
            day=5 + i,
            names=FOUR,
            generals=(General.UNRECOGNIZED, General.CHINA, General.GLA, General.USA),
        )
        for i in range(8)
    ]
    listed = {s.general for s in ffa_stats.get_ffa_stats(games).general_stats}
    assert General.UNRECOGNIZED not in listed
    assert General.CHINA in listed


def test_a_slot_with_no_known_general_does_not_join_the_field() -> None:
    """`entries` drops it before `n` is taken, so it shrinks the field size too."""
    games = [
        ffa_match(
            7300 + i,
            day=5 + i,
            names=FFA_NAMES[:4],
            generals=(General.UNRECOGNIZED, General.CHINA, General.GLA, General.USA),
            winner_index=1,
        )
        for i in range(8)
    ]
    stats = ffa_stats.get_ffa_stats(games)
    assert stats.avg_players_per_game == 3.0, (
        "the unparsed slot should not count toward the field size"
    )
    by_name = {s.name: s for s in stats.player_stats}
    assert by_name[FOUR[1]].expected_wins == pytest.approx(8 / 3)


def test_maps_below_the_threshold_are_dropped() -> None:
    games = _series(2, map_name=MAPS[0]) + _series(1, map_name=MAPS[1], start=7400)
    listed = {m.map for m in ffa_stats.get_ffa_stats(games).map_stats}
    assert listed == {MAPS[0]}


def test_maps_are_ranked_by_games_played() -> None:
    games = (
        _series(2, map_name=MAPS[0])
        + _series(4, map_name=MAPS[1], start=7500)
        + _series(3, map_name=MAPS[2], start=7600)
    )
    played = [m.games for m in ffa_stats.get_ffa_stats(games).map_stats]
    assert played == sorted(played, reverse=True)


# --- most recent ------------------------------------------------------------


def test_most_recent_is_the_latest_game_not_the_last_in_the_list() -> None:
    early = ffa_match(7800, day=6, names=FOUR, winner_index=0)
    late = ffa_match(7801, day=20, names=FOUR, winner_index=1)
    stats = ffa_stats.get_ffa_stats([late, early])
    assert stats.most_recent is not None
    assert stats.most_recent.match_id == 7801
    assert stats.most_recent.winner == FOUR[1]


def test_no_eligible_games_leaves_most_recent_unset() -> None:
    stats = ffa_stats.get_ffa_stats([ffa_match(7802, day=6, names=FFA_NAMES[:2])])
    assert stats.most_recent is None
    assert stats.total_games == 0
    assert stats.avg_players_per_game == 0.0


def test_an_observer_changes_nothing() -> None:
    """The spectator holds a *recognized* general on purpose.

    With no general, `has_known_general` would drop it and the test would pass
    even if the module read `roster().slots` instead of `roster().humans` - i.e.
    for the wrong reason. Giving it a real general leaves its role as the only
    thing that can exclude it, which is the property that has broken before.
    """
    plain = _series(8)
    watched = [
        g.model_copy(update={"players": [*g.players, observer(general=General.CHINA)]})
        for g in plain
    ]
    assert ffa_stats.get_ffa_stats(watched) == ffa_stats.get_ffa_stats(plain)


def test_a_field_that_shrinks_below_three_after_filtering_is_skipped() -> None:
    """The size check runs twice, against different numbers.

    `is_ffa_game` reads the *composition*'s human count; this one reads the
    entries left after dropping slots whose general did not parse. A 4-player
    FFA where two slots are unparsed is a 2-player field and must not count.
    """
    games = [
        ffa_match(
            7950 + i,
            day=5 + i,
            names=FOUR,
            generals=(
                General.UNRECOGNIZED,
                General.UNRECOGNIZED,
                General.GLA,
                General.USA,
            ),
            winner_index=2,
        )
        for i in range(8)
    ]
    stats = ffa_stats.get_ffa_stats(games)
    assert stats.total_games == 0, "a two-player field was counted as an FFA"
    assert stats.player_stats == []


# --- include_cpu ------------------------------------------------------------
#
# The toggle picks a corpus, and inside a counted game the AI slots are full
# participants: they size the field, hold leaderboard rows, and can win. What is
# worth pinning is that both halves of that move together - a CPU that sizes the
# field but is missing from the totals would make two numbers on the page
# disagree, and each half is one call site away from the other.


def _mixed(n: int, *, humans=FOUR, cpus=("Tactical AI", "Hard Army"), winner_index=0):
    return [
        ffa_match(
            8000 + i,
            day=5 + (i % 23),
            names=humans,
            cpu_names=cpus,
            winner_index=winner_index,
        )
        for i in range(n)
    ]


def test_the_default_is_still_the_human_only_corpus() -> None:
    assert ffa_stats.get_ffa_stats(_mixed(8)).total_games == 0


def test_include_cpu_admits_the_same_games() -> None:
    stats = ffa_stats.get_ffa_stats(_mixed(8), include_cpu=True)
    assert stats.total_games == 8


def test_include_cpu_leaves_the_human_only_corpus_untouched() -> None:
    """A game with no AI in it must read identically under either setting."""
    plain = _series(8)
    assert ffa_stats.get_ffa_stats(plain, include_cpu=True) == ffa_stats.get_ffa_stats(
        plain
    )


def test_ai_slots_size_the_field() -> None:
    """Four humans plus two AI is a six-player FFA, not a four-player one."""
    stats = ffa_stats.get_ffa_stats(_mixed(12), include_cpu=True)
    assert stats.avg_players_per_game == 6.0
    by_name = {s.name: s for s in stats.player_stats}
    assert by_name[FOUR[0]].expected_wins == pytest.approx(2.0)


def test_ai_gets_its_own_leaderboard_row() -> None:
    stats = ffa_stats.get_ffa_stats(_mixed(8), include_cpu=True)
    by_name = {s.name: s for s in stats.player_stats}
    assert by_name["Tactical AI"].is_cpu
    assert not by_name[FOUR[0]].is_cpu


def test_no_row_is_flagged_cpu_in_the_human_only_corpus() -> None:
    """`is_cpu` is what stops the page linking a profile that can't exist."""
    stats = ffa_stats.get_ffa_stats(_series(8))
    assert stats.player_stats
    assert not any(s.is_cpu for s in stats.player_stats)


def test_a_game_the_ai_won_is_that_ais_win() -> None:
    """winner_index 4 is the first AI slot: humans first, then the CPUs."""
    stats = ffa_stats.get_ffa_stats(_mixed(8, winner_index=4), include_cpu=True)
    by_name = {s.name: s for s in stats.player_stats}
    assert by_name["Tactical AI"].wins == 8
    assert all(s.wins == 0 for s in stats.player_stats if not s.is_cpu)


def test_an_ai_win_is_the_most_recent_ffas_winner() -> None:
    late = ffa_match(8100, day=20, names=FOUR, cpu_names=("Hard Army",), winner_index=4)
    stats = ffa_stats.get_ffa_stats([late], include_cpu=True)
    assert stats.most_recent is not None
    assert stats.most_recent.winner == "Hard Army"


def test_ai_generals_are_counted_and_can_hold_the_wins() -> None:
    games = [
        ffa_match(
            8300 + i,
            day=5 + i,
            names=FFA_NAMES[:3],
            cpu_names=("Tactical AI",),
            generals=(General.USA, General.CHINA, General.GLA, General.NUKE),
            winner_index=3,
        )
        for i in range(8)
    ]
    by_general = {
        s.general: s
        for s in ffa_stats.get_ffa_stats(games, include_cpu=True).general_stats
    }
    assert by_general[General.NUKE].wins == 8, (
        "the AI's general held every win but was left off the table"
    )
    assert General.NUKE not in {
        s.general for s in ffa_stats.get_ffa_stats(games).general_stats
    }


def test_the_size_floor_counts_the_whole_field_not_just_the_humans() -> None:
    """Two humans and two AI is a four-player FFA and counts; two alone does not."""
    assert ffa_stats.is_ffa_game(
        ffa_match(1, day=5, names=FFA_NAMES[:2], num_computers=2), include_cpu=True
    )
    assert not ffa_stats.is_ffa_game(
        ffa_match(1, day=5, names=FFA_NAMES[:2]), include_cpu=True
    )


def test_ai_names_are_not_alias_resolved() -> None:
    """Alias resolution exists for humans' in-game spellings.

    "pc" is the live example - it maps to a person by colour. An AI slot whose
    name collided with an alias must stay itself rather than be folded onto a
    player's row.
    """
    humans = ("Skip", "CoreDawg", "Syn")
    games = [
        ffa_match(8400 + i, day=5 + i, names=humans, cpu_names=("pc",))
        for i in range(8)
    ]
    listed = {
        s.name for s in ffa_stats.get_ffa_stats(games, include_cpu=True).player_stats
    }
    assert listed == {*humans, "pc"}, (
        "the AI slot was alias-resolved onto a person's row"
    )


def test_identically_named_ai_slots_collapse_into_one_row() -> None:
    """Three AI opponents in one game are all "Tactical AI" in a real replay.

    They share a row, so its `games` counts slots rather than matches - and
    `expected_wins` has to collapse the same way or `dominance` would read three
    times too high.
    """
    games = _mixed(8, humans=FFA_NAMES[:3], cpus=("Tactical AI",) * 3)
    stats = ffa_stats.get_ffa_stats(games, include_cpu=True)
    by_name = {s.name: s for s in stats.player_stats}
    ai = by_name["Tactical AI"]
    assert ai.games == 24, "one row per name, one game per slot"
    assert ai.expected_wins == pytest.approx(4.0), "24 slots at 1/6 of a 6-player field"
    assert ai.dominance == pytest.approx(0.0)


def test_an_observer_changes_nothing_with_cpus_included() -> None:
    """The invariant has to survive the partition swap, not just `humans`."""
    plain = _mixed(8)
    watched = [
        g.model_copy(update={"players": [*g.players, observer(general=General.CHINA)]})
        for g in plain
    ]
    assert ffa_stats.get_ffa_stats(
        watched, include_cpu=True
    ) == ffa_stats.get_ffa_stats(plain, include_cpu=True)
