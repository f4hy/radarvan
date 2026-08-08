"""Observer handling in radarvan.utils and radarvan.parse_replay.

1v1 replays arrive teamless (header team "-1" for everyone), so
``reassign_1v1_teams`` numbers the competitors. Spectators share the same
type "H" as real players and are only distinguishable by playerTemplate -2 -
see ``utils.is_observer`` / ``utils.is_competitor``.
"""

from radarvan.cncstats_model.header import Player
from radarvan.game_composition import PlayerAdapter, categorize_game_type
from radarvan.parse_replay import reassign_1v1_teams
from radarvan.utils import determine_team, is_competitor, is_observer


def _player(
    name: str, player_template: str, ptype: str = "H", team: str = "-1"
) -> Player:
    return Player.model_construct(
        name=name, team=team, type=ptype, player_template=player_template
    )


def test_is_observer_only_for_template_minus_two() -> None:
    assert is_observer(_player("Watcher", "-2")) is True
    assert is_observer(_player("Syn", "2")) is False
    assert is_observer(_player("Neo", "10")) is False


def test_reassign_skips_observers() -> None:
    # Match 85567703's real lineup: two spectators listed before the two
    # competitors. Numbering every slot gave teams 1-4 and an FFA verdict;
    # only the competitors may be numbered.
    players = [
        _player("Neo.v.Syn", "-2"),
        _player("Tytan", "-2"),
        _player("Syn", "2"),
        _player("Neo", "10"),
    ]
    result = reassign_1v1_teams(players)
    assert [(p.name, p.team) for p in result] == [
        ("Neo.v.Syn", "-1"),
        ("Tytan", "-1"),
        ("Syn", "1"),
        ("Neo", "2"),
    ]


def test_reassign_plain_1v1_unchanged() -> None:
    players = [_player("Syn", "2"), _player("Neo", "10")]
    result = reassign_1v1_teams(players)
    assert [p.team for p in result] == ["1", "2"]


def test_reassign_does_not_mutate_input() -> None:
    players = [_player("Syn", "2"), _player("Neo", "10")]
    reassign_1v1_teams(players)
    assert [p.team for p in players] == ["-1", "-1"]


def test_is_competitor_covers_humans_cpus_and_spectators() -> None:
    assert is_competitor(_player("Syn", "2")) is True
    assert is_competitor(_player("CPU", "4", ptype="C")) is True
    assert is_competitor(_player("Watcher", "-2")) is False
    assert is_competitor(_player("Slot", "2", ptype="X")) is False


def _composition_as_parse_replay_sees_it(players: list[Player]):
    """Mirror parse_replay_data's 1v1 pre-check."""
    return categorize_game_type(
        [
            PlayerAdapter(team=int(determine_team(p, None)), type=p.type)
            for p in players
            if is_competitor(p)
        ]
    )


def test_team_games_are_not_mistaken_for_1v1() -> None:
    # Header teams are raw and 0-based, while categorize_game_type wants the
    # 1-based scheme. Feeding the raw value in reads a 2v2's "team 0" side as
    # teamless, leaving two participants and a 1v1 verdict - which would fire
    # reassign_1v1_teams and renumber all four players onto separate teams.
    two_v_two = [
        _player("A", "2", team="0"),
        _player("B", "3", team="0"),
        _player("C", "4", team="1"),
        _player("D", "5", team="1"),
    ]
    comp = _composition_as_parse_replay_sees_it(two_v_two)
    assert comp.category == "2v2"
    assert comp.is_1v1 is False


def test_spectated_1v1_is_detected_as_1v1() -> None:
    # Match 85567703: every slot teamless, two of them spectators.
    comp = _composition_as_parse_replay_sees_it(
        [
            _player("Neo.v.Syn", "-2"),
            _player("Tytan", "-2"),
            _player("Syn", "2"),
            _player("Neo", "10"),
        ]
    )
    assert comp.is_1v1 is True
