"""Pure-function tests for radarvan.game_composition.

Covers the snake->camel alias helper, the game-type categorizer across its
branches (1v1, 2v2, comp-stomp, and the team-0 = observers rule), and the
competitive-game filter.
"""

from collections.abc import Sequence

from radarvan.game_composition import (
    GameComposition,
    PlayerAdapter,
    categorize_game_type,
    competitive_game_filter,
    to_camel,
)


def _categorize(players: Sequence[tuple[int, str]]) -> GameComposition:
    return categorize_game_type([PlayerAdapter(team, ptype) for team, ptype in players])


def test_to_camel_basic() -> None:
    assert to_camel("is_comp_stomp") == "isCompStomp"
    assert to_camel("num_teams") == "numTeams"
    assert to_camel("a_b_c") == "aBC"


def test_to_camel_single_word_unchanged() -> None:
    assert to_camel("category") == "category"
    assert to_camel("ffa") == "ffa"


def test_empty_player_list_is_unknown() -> None:
    comp = _categorize([])
    assert comp.category == "Unknown"
    assert comp.total_players == 0
    assert comp.num_teams == 0
    assert comp.team_sizes == []


def test_single_player_is_unknown() -> None:
    comp = _categorize([(1, "H")])
    assert comp.category == "Unknown"
    assert comp.total_players == 1


def test_two_players_is_1v1() -> None:
    comp = _categorize([(1, "H"), (2, "H")])
    assert comp.category == "1v1"
    assert comp.is_1v1 is True
    assert comp.num_teams == 2
    assert comp.team_sizes == [1, 1]
    assert comp.is_team_game is True
    assert comp.is_comp_stomp is False


def test_two_v_two_balanced_team_game() -> None:
    comp = _categorize([(1, "H"), (1, "H"), (2, "H"), (2, "H")])
    assert comp.category == "2v2"
    assert comp.is_1v1 is False
    assert comp.num_teams == 2
    assert comp.team_sizes == [2, 2]
    assert comp.is_balanced is True
    assert comp.is_team_game is True
    assert comp.is_comp_stomp is False
    assert comp.num_humans == 4
    assert comp.num_computers == 0


def test_comp_stomp_detected() -> None:
    # Two humans (team 1) vs two computers (team 2): a comp-stomp.
    comp = _categorize([(1, "H"), (1, "H"), (2, "C"), (2, "C")])
    assert comp.category == "2v2"
    assert comp.is_comp_stomp is True
    assert comp.num_humans == 2
    assert comp.num_computers == 2


def test_team_zero_players_ignored_for_game_type() -> None:
    # Per CLAUDE.md, team-0 players are observers/disconnected and must not
    # affect the determined game type. A 2v2 with two extra team-0 spectators
    # is still a 2v2, even though they bump the total player count.
    comp = _categorize([(1, "H"), (1, "H"), (2, "H"), (2, "H"), (0, "H"), (0, "H")])
    assert comp.category == "2v2"
    assert comp.num_teams == 2
    assert comp.team_sizes == [2, 2]
    assert comp.total_players == 6


def test_competitive_filter_none_is_false() -> None:
    assert competitive_game_filter(None) is False


def test_competitive_filter_accepts_clean_team_game() -> None:
    comp = _categorize([(1, "H"), (1, "H"), (2, "H"), (2, "H")])
    assert competitive_game_filter(comp) is True


def test_competitive_filter_accepts_1v1() -> None:
    comp = _categorize([(1, "H"), (2, "H")])
    assert competitive_game_filter(comp) is True


def test_competitive_filter_allows_single_computer() -> None:
    # One AI in an otherwise balanced team game is still competitive.
    comp = _categorize([(1, "H"), (1, "H"), (2, "H"), (2, "C")])
    assert comp.num_computers == 1
    assert competitive_game_filter(comp) is True


def test_competitive_filter_rejects_comp_stomp() -> None:
    comp = _categorize([(1, "H"), (1, "H"), (2, "C"), (2, "C")])
    assert competitive_game_filter(comp) is False


def test_competitive_filter_rejects_many_computers() -> None:
    # Multiple computers (>1) disqualifies even a balanced human-vs-human game.
    comp = _categorize([(1, "H"), (1, "C"), (2, "H"), (2, "C")])
    assert comp.num_computers == 2
    assert competitive_game_filter(comp) is False


def test_competitive_filter_rejects_unbalanced() -> None:
    # 1v2 (teams of size 1 and 2) is not balanced.
    comp = _categorize([(1, "H"), (2, "H"), (2, "H")])
    assert comp.is_balanced is False
    assert competitive_game_filter(comp) is False
