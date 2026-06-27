"""`matches.matches_differ` field-by-field comparison.

`matches_differ` only reads plain attributes off the two match objects and off
each player in `.players` (see `radarvan/matches.py`), so lightweight
`SimpleNamespace` stand-ins are sufficient (mirrors `tests/test_rating_upsets`).
"""

from types import SimpleNamespace

import pytest

from radarvan.matches import matches_differ


def _player(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "player_name": "Skip",
        "general_id": 3,
        "team_id": 1,
        "color": "red",
        "is_winner": True,
        "starting_position": 0,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _match(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "map": "Tournament Desert",
        "winning_team_id": 1,
        "duration_minutes": 12.5,
        "incomplete": "",
        "game_version": "Version 1.04",
        "players": [
            _player(),
            _player(
                player_name="131",
                general_id=5,
                team_id=2,
                color="blue",
                is_winner=False,
                starting_position=1,
            ),
        ],
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_identical_matches_do_not_differ() -> None:
    assert matches_differ(_match(), _match()) is False


def test_player_order_does_not_matter() -> None:
    # matches_differ sorts players before comparing, so a different ordering of
    # the same players must still compare equal.
    m1 = _match()
    m2 = _match(players=list(reversed(m1.players)))
    assert matches_differ(m1, m2) is False


def test_duration_difference_within_rounding_is_ignored() -> None:
    # Durations are compared rounded to 2 decimals.
    assert matches_differ(_match(duration_minutes=12.5), _match(duration_minutes=12.501)) is False


@pytest.mark.parametrize(
    "field, value",
    [
        ("map", "Other Map"),
        ("winning_team_id", 2),
        ("duration_minutes", 13.0),
        ("incomplete", "disconnect"),
        ("game_version", "Version 1.05"),
    ],
)
def test_top_level_field_difference_is_detected(field: str, value: object) -> None:
    assert matches_differ(_match(), _match(**{field: value})) is True


@pytest.mark.parametrize(
    "field, value",
    [
        ("player_name", "Renamed"),
        ("general_id", 99),
        ("team_id", 7),
        ("color", "green"),
        ("is_winner", False),
        ("starting_position", 4),
    ],
)
def test_player_field_difference_is_detected(field: str, value: object) -> None:
    new_players = [_player(**{field: value}), _match().players[1]]
    assert matches_differ(_match(), _match(players=new_players)) is True
