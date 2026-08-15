"""Temporal splitting, and the 1v1 routing exception.

A plain temporal cut puts every tournament 1v1 in dev - the bracket is recent
and the snapshot holds nothing else 1v1 - which trains the model on none of
them and keeps "1v1" out of the train-only vocab. `temporal_split` routes them
into train instead; these tests pin both halves of that.
"""

from datetime import date, datetime, timedelta

from ml.split import temporal_split
from radarvan.api_types import General, MatchInfo, Player, Team
from radarvan.game_composition import MatchRoster
from radarvan.player_role import PlayerRole

START = datetime(2026, 1, 1)


def _player(name: str, team: Team, color: str) -> Player:
    return Player(
        name=name,
        general=General.USA,
        team=team,
        color=color,
        won=team is Team.ONE,
        role=PlayerRole.HUMAN,
    )


def _match(match_id: int, day: int, *, one_v_one: bool) -> MatchInfo:
    players = [
        _player("Skip", Team.ONE, "red"),
        _player("Neo", Team.TWO, "blue"),
    ]
    if not one_v_one:
        players += [
            _player("Gorn", Team.ONE, "green"),
            _player("Pancake", Team.TWO, "orange"),
        ]
    when = START + timedelta(days=day)
    return MatchInfo(
        id=match_id,
        timestamp=when,
        date=date(when.year, when.month, when.day),
        map="some_map",
        winning_team=Team.ONE,
        players=players,
        duration_minutes=10.0,
        filename=f"game_{match_id}.rep",
        composition=MatchRoster.from_players(players).composition(),
    )


def _corpus() -> list[MatchInfo]:
    """90 team games, then 10 recent 1v1s - the real shape: 1v1s are newest."""
    team_games = [_match(i, i, one_v_one=False) for i in range(90)]
    ones = [_match(100 + i, 90 + i, one_v_one=True) for i in range(10)]
    return [*team_games, *ones]


def test_1v1s_go_to_train_despite_being_newest() -> None:
    train, dev = temporal_split(_corpus(), dev_frac=0.2)
    assert [m.id for m in train if m.id >= 100] == list(range(100, 110))
    assert not [m for m in dev if m.id >= 100]


def test_dev_frac_applies_to_the_splittable_games() -> None:
    """Reserving the 1v1s grows train; it must not shrink dev."""
    train, dev = temporal_split(_corpus(), dev_frac=0.2)
    assert len(dev) == 18  # 20% of the 90 team games, not of all 100
    assert len(train) == 82  # 72 team games + 10 1v1s


def test_dev_is_the_most_recent_team_games() -> None:
    train, dev = temporal_split(_corpus(), dev_frac=0.2)
    assert max(m.timestamp for m in train if m.id < 100) < min(
        m.timestamp for m in dev
    )
    assert [m.id for m in dev] == list(range(72, 90))


def test_train_stays_ordered_by_time() -> None:
    train, _ = temporal_split(_corpus(), dev_frac=0.2)
    assert train == sorted(train, key=lambda m: m.timestamp)


def test_holdout_1v1_restores_the_plain_cut() -> None:
    train, dev = temporal_split(_corpus(), dev_frac=0.2, holdout_1v1=True)
    assert len(train) == 80
    assert [m.id for m in dev] == list(range(80, 90)) + list(range(100, 110))


def test_no_1v1s_present_is_unaffected() -> None:
    team_only = [_match(i, i, one_v_one=False) for i in range(50)]
    assert temporal_split(team_only, dev_frac=0.2) == temporal_split(
        team_only, dev_frac=0.2, holdout_1v1=True
    )
