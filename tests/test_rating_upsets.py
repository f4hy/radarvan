"""Upset detection: a game is an upset when the model's favored team lost."""

from datetime import date
from types import SimpleNamespace

from radarvan.player_rating import GameUpset, _detect_upset


def _game(match_id: int, winning_team: int) -> SimpleNamespace:
    # _detect_upset only reads id, date, winning_team off the game.
    return SimpleNamespace(id=match_id, date=date(2024, 1, 1), winning_team=winning_team)


def test_favored_team_winning_is_not_an_upset() -> None:
    teams = {1: ["a"], 2: ["b"]}
    # Team 1 is favored (0.8) and team 1 won -> no upset.
    assert _detect_upset(_game(1, 1), teams, {1: 0.8, 2: 0.2}) is None


def test_favored_team_losing_is_an_upset() -> None:
    teams = {1: ["a", "b"], 2: ["c", "d"]}
    # Team 1 favored at 0.75 but team 2 won.
    upset = _detect_upset(_game(7, 2), teams, {1: 0.75, 2: 0.25})
    assert isinstance(upset, GameUpset)
    assert upset.match_id == 7
    assert upset.favored_team == 1
    assert upset.favored_players == ["a", "b"]
    assert upset.favored_win_prob == 0.75
    assert upset.winning_team == 2
    assert upset.winner_players == ["c", "d"]
    assert upset.winner_win_prob == 0.25
    # Surprise is the favorite's edge over the actual winner.
    assert upset.surprise == 0.5
