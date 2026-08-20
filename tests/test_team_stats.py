"""`team_stats.get_team_stats` - W/L records grouped by exact team roster.

The module had no direct coverage: the smoke test calls `/api/team_stats/` and
checks the response validates, which says nothing about whether the records are
right. What is pinned here is the set of games a record is allowed to count, and
the shape of the key it counts under.
"""

import pytest

from radarvan import team_stats
from radarvan.api_types import General, Team

from corpus import TEAM_ONE, TEAM_TWO, composition, cpu, match, observer


def _records(games) -> dict[tuple[str, ...], tuple[int, int]]:
    """{team key -> (wins, losses)} across every size group, for easy asserting."""
    resp = team_stats.get_team_stats(games)
    return {
        tuple(t.players): (t.wins, t.losses)
        for group in resp.groups
        for t in group.teams
    }


def _series(n: int, *, team_one_wins: int) -> list:
    """`n` 2v2s between the two fixture teams, `team_one_wins` of them won by team one."""
    return [
        match(9000 + i, day=5 + i, winner=Team.ONE if i < team_one_wins else Team.TWO)
        for i in range(n)
    ]


def test_wins_and_losses_are_counted_per_roster() -> None:
    records = _records(_series(5, team_one_wins=3))
    assert records[tuple(sorted(TEAM_ONE))] == (3, 2)
    assert records[tuple(sorted(TEAM_TWO))] == (2, 3)


def test_the_key_is_sorted_so_roster_order_does_not_split_a_team() -> None:
    """`Skip+CoreDawg` and `CoreDawg+Skip` are one team, not two."""
    games = _series(4, team_one_wins=2)
    games.append(
        match(9500, day=20, winner=Team.ONE, team_one=tuple(reversed(TEAM_ONE)))
    )
    records = _records(games)
    assert records[tuple(sorted(TEAM_ONE))] == (3, 2)
    assert len(records) == 2, f"a reordered roster opened a second record: {records}"


def test_a_team_under_the_threshold_is_dropped() -> None:
    """`MIN_GAMES` is a strict floor: more than 2 games, so 3 is the minimum."""
    assert _records(_series(2, team_one_wins=1)) == {}
    assert _records(_series(3, team_one_wins=2)) != {}


def test_incomplete_games_do_not_count() -> None:
    games = _series(4, team_one_wins=4)
    games.append(match(9501, day=21, winner=Team.TWO, incomplete="Disconnect"))
    assert _records(games)[tuple(sorted(TEAM_ONE))] == (4, 0), (
        "a disconnect was counted as a loss"
    )


def test_games_without_a_winner_do_not_count() -> None:
    games = _series(4, team_one_wins=4)
    games.append(match(9502, day=21, winner=Team.NONE))
    assert _records(games)[tuple(sorted(TEAM_ONE))] == (4, 0)


def test_one_v_ones_are_excluded() -> None:
    """Team records start at 2v2; a 1v1 is a player record, not a team one."""
    games = [
        match(
            9600 + i,
            day=5 + i,
            winner=Team.ONE,
            team_one=(TEAM_ONE[0],),
            team_two=(TEAM_TWO[0],),
            comp=composition(
                category="1v1",
                num_teams=2,
                team_sizes=[1, 1],
                total_players=2,
                num_humans=2,
                is_1v1=True,
            ),
        )
        for i in range(6)
    ]
    assert _records(games) == {}


def test_unbalanced_games_are_excluded() -> None:
    """A 2v1 has no comparable 'team', so it must not land in either group."""
    games = [
        match(
            9700 + i,
            day=5 + i,
            winner=Team.ONE,
            team_two=(TEAM_TWO[0],),
            comp=composition(
                category="2v1",
                team_sizes=[2, 1],
                total_players=3,
                num_humans=3,
                is_balanced=False,
            ),
        )
        for i in range(6)
    ]
    assert _records(games) == {}


def test_groups_are_ordered_by_size_and_teams_by_games_played() -> None:
    games = _series(5, team_one_wins=3)
    games += [
        match(
            9800 + i,
            day=5 + i,
            winner=Team.ONE,
            team_one=("Skip", "CoreDawg", "Neo"),
            team_two=("Syn", "Pancake", "Modus"),
            comp=composition(
                category="3v3",
                team_sizes=[3, 3],
                total_players=6,
                num_humans=6,
            ),
        )
        for i in range(4)
    ]
    resp = team_stats.get_team_stats(games)
    assert [g.size for g in resp.groups] == [2, 3]
    counts = [t.wins + t.losses for t in resp.groups[0].teams]
    assert counts == sorted(counts, reverse=True)


def test_an_observer_changes_nothing() -> None:
    """The invariant that has broken twice: a spectator is not a player.

    The spectator carries a recognized general so that its *role* is the only
    thing that can exclude it - a slot with no general would be dropped by a
    parse-quality check and the test would pass for the wrong reason. A real
    case of this counted a spectator's `won=False` slot as a team loss.
    """
    plain = _series(5, team_one_wins=3)
    watched = [
        match(
            g.id,
            day=g.timestamp.day,
            winner=g.winning_team,
            extra_players=(observer(general=General.CHINA),),
        )
        for g in plain
    ]
    assert _records(watched) == _records(plain)


def test_an_ai_slot_is_not_a_teammate() -> None:
    """`human_participants` is what the record counts; a CPU must not join a key."""
    plain = _series(5, team_one_wins=3)
    with_ai = [
        match(
            g.id,
            day=g.timestamp.day,
            winner=g.winning_team,
            extra_players=(cpu(team=Team.THREE),),
        )
        for g in plain
    ]
    assert _records(with_ai) == _records(plain)


@pytest.mark.parametrize("alias,canonical", [("skp", "Skip")])
def test_aliases_resolve_into_one_team(alias: str, canonical: str) -> None:
    games = _series(4, team_one_wins=2)
    games.append(match(9900, day=25, winner=Team.ONE, team_one=(alias, TEAM_ONE[1])))
    records = _records(games)
    assert len(records) == 2, f"{alias} opened a separate team record: {records}"
    assert records[tuple(sorted(TEAM_ONE))] == (3, 2)


def test_a_game_with_no_human_participants_is_skipped() -> None:
    """An all-AI game reaches the roster stage and must fall out there."""
    games = _series(4, team_one_wins=4)
    all_ai = match(
        9950,
        day=26,
        winner=Team.ONE,
        team_one=("TacticalAI", "EasyArmy"),
        team_two=("MediumArmy", "HardArmy"),
    )
    assert _records([*games, all_ai])[tuple(sorted(TEAM_ONE))] == (4, 0)


def test_a_roster_that_disagrees_with_the_composition_is_skipped() -> None:
    """The size check is made from the *roster*, not the declared composition.

    A game can claim 2v2 while its slots say 2v1 - a disconnect before the
    header was written, say. The team sizes that matter are the ones actually
    played, so this must not produce a lopsided record.
    """
    games = _series(4, team_one_wins=4)
    mismatched = match(
        9951,
        day=27,
        winner=Team.ONE,
        team_two=(TEAM_TWO[0],),
        comp=composition(),  # still claims a balanced 2v2
    )
    assert _records([*games, mismatched])[tuple(sorted(TEAM_ONE))] == (4, 0)
