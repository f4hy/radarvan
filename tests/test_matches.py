"""`matches.matches_differ` field-by-field comparison.

`matches_differ` only reads plain attributes off the two match objects and off
each player in `.players` (see `radarvan/matches.py`), so lightweight
`SimpleNamespace` stand-ins are sufficient (mirrors `tests/test_rating_upsets`).
"""

from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from radarvan.cncstats_model import header
from radarvan.cncstats_model.zhreplay import EnhancedReplayV2, PlayerSummaryV2
from radarvan.matches import filter_by_months_back, is_incomplete, matches_differ
from radarvan.player_role import PlayerRole


def _header_player(name: str, team: str) -> header.Player:
    # player_template is read by utils.is_competitor on is_incomplete's
    # no-winner path; "2" is an ordinary competitor (-2 would be a spectator).
    return header.Player.model_construct(
        name=name, team=team, type="H", starting_position="0", player_template="2"
    )


def _summary_player(index: int, name: str, win: bool) -> PlayerSummaryV2:
    return PlayerSummaryV2.model_construct(index=index, name=name, win=win)


def _replay(
    teams: list[str], player_discons: list[bool], wins: list[bool]
) -> EnhancedReplayV2:
    names = [f"P{i}" for i in range(len(teams))]
    metadata = header.Metadata.model_construct(
        players=[_header_player(n, t) for n, t in zip(names, teams)]
    )
    head = header.GeneralsHeader.model_construct(
        desync=False,
        quit_early=False,
        player_discons=player_discons,
        metadata=metadata,
        time_stamp_begin=0,
        time_stamp_end=600,
    )
    summary = [
        _summary_player(i + 1, n, w) for i, (n, w) in enumerate(zip(names, wins))
    ]
    return EnhancedReplayV2.model_construct(header=head, stats=None, summary=summary)


def test_disconnect_with_a_surviving_teammate_is_not_flagged() -> None:
    # 3v3: one member of team "0" disconnects, but two teammates remain and
    # the team still won - should not read as "Disconnect".
    replay = _replay(
        teams=["0", "0", "0", "1", "1", "1"],
        player_discons=[True, False, False, False, False, False],
        wins=[True, True, True, False, False, False],
    )
    assert is_incomplete(replay) == ""


def test_disconnect_of_a_solo_slot_with_a_winner_is_not_flagged() -> None:
    # 1v1 (each side is a "team" of one) - a disconnect on a slot with no
    # teammate doesn't invalidate the match as long as a winner was decided.
    replay = _replay(
        teams=["0", "1"], player_discons=[True, False], wins=[True, False]
    )
    assert is_incomplete(replay) == ""


def test_whole_team_disconnecting_is_still_flagged() -> None:
    # Both members of team "0" disconnect - the team was wiped out purely by
    # disconnection, so this still counts as a match-ending "Disconnect".
    replay = _replay(
        teams=["0", "0", "1", "1"],
        player_discons=[True, True, False, False],
        wins=[False, False, True, True],
    )
    assert is_incomplete(replay) == "Disconnect"


def _player(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "player_name": "Skip",
        "general_id": 3,
        "team_id": 1,
        "color": "red",
        "is_winner": True,
        "starting_position": 0,
        "role": PlayerRole.HUMAN,
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
        # An un-backfilled row must compare unequal to a classified one so the
        # reparse paths pick the role up.
        ("role", None),
        ("role", PlayerRole.CPU),
    ],
)
def test_player_field_difference_is_detected(field: str, value: object) -> None:
    new_players = [_player(**{field: value}), _match().players[1]]
    assert matches_differ(_match(), _match(players=new_players)) is True


def _game_on(d: date) -> SimpleNamespace:
    return SimpleNamespace(date=d)


def test_filter_by_months_back_none_returns_unchanged() -> None:
    games = [_game_on(date(2020, 1, 1))]
    assert filter_by_months_back(games, None) == games


def test_filter_by_months_back_drops_older_games() -> None:
    today = date(2026, 6, 30)
    recent = _game_on(date(2026, 6, 1))  # within the last month
    old = _game_on(date(2025, 1, 1))  # well over a year ago
    result = filter_by_months_back([recent, old], 1, today=today)
    assert result == [recent]


def test_filter_by_months_back_boundary_is_inclusive() -> None:
    today = date(2026, 6, 30)
    cutoff_day = _game_on(today - timedelta(days=30))
    result = filter_by_months_back([cutoff_day], 1, today=today)
    assert result == [cutoff_day]
