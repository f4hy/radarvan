"""What the ML snapshot trains on.

`is_training_match` is a delegation to `player_rating.is_ratable_team_game`
today, so the *semantics* (which 1v1s, comp-stomps, incomplete games, unknown
players) are pinned once in `test_ratable_games.py` and are not restated here.
What this file pins is the claim the snapshot layer itself makes: that the two
rules are the same one right now, so a future divergence is a choice somebody
makes on purpose rather than a drift nobody noticed.
"""

from datetime import date, datetime

from ml.snapshot import is_1v1, is_training_match
from radarvan import player_rating
from radarvan.api_types import General, MatchInfo, Player, Team, TournamentTag
from radarvan.game_composition import MatchRoster
from radarvan.player_role import PlayerRole

BRACKET = TournamentTag(slug="2026_1v1_bracket", stage="WB2-1")


def _player(name: str, team: Team, color: str, *, won: bool) -> Player:
    return Player(
        name=name,
        general=General.USA,
        team=team,
        color=color,
        won=won,
        role=PlayerRole.HUMAN,
    )


def _match(
    players: list[Player], *, tournament: TournamentTag | None = None
) -> MatchInfo:
    return MatchInfo(
        id=1215088593,
        timestamp=datetime(2026, 8, 13, 6, 35, 18),
        date=date(2026, 8, 12),
        map="some_map",
        winning_team=Team.ONE,
        players=players,
        duration_minutes=17.7,
        filename="game.rep",
        composition=MatchRoster.from_players(players).composition(),
        tournament=tournament,
    )


def _1v1(*, tournament: TournamentTag | None = None) -> MatchInfo:
    return _match(
        [
            _player("Skip", Team.ONE, "red", won=True),
            _player("Neo", Team.TWO, "blue", won=False),
        ],
        tournament=tournament,
    )


def _2v2() -> MatchInfo:
    return _match(
        [
            _player("Skip", Team.ONE, "red", won=True),
            _player("Gorn", Team.ONE, "green", won=True),
            _player("Neo", Team.TWO, "blue", won=False),
            _player("Pancake", Team.TWO, "orange", won=False),
        ]
    )


def test_training_set_is_exactly_the_ratable_set() -> None:
    """The delegation, over the cases that separate the two populations."""
    for match in (_2v2(), _1v1(), _1v1(tournament=BRACKET)):
        assert is_training_match(match) is player_rating.is_ratable_team_game(match)


def test_every_1v1_in_the_snapshot_is_a_tournament_game() -> None:
    """What lets the manifest report a single `n_1v1` count.

    `write_snapshot` records one 1v1 number rather than a tournament-1v1 one
    as well, because under this rule the two cannot differ.
    """
    assert is_training_match(_1v1(tournament=BRACKET)) is True
    assert is_training_match(_1v1()) is False


def test_is_1v1_reads_the_composition() -> None:
    """Shared with ml.split, which routes exactly these into train."""
    assert is_1v1(_1v1()) is True
    assert is_1v1(_2v2()) is False
    assert is_1v1(_1v1().model_copy(update={"composition": None})) is False
