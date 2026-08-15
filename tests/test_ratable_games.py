"""Which games move ratings: `player_rating.is_ratable_team_game`.

Tournament 1v1s count - a bracket game is a real result between two people.
Casual 1v1s don't: most are matchup practice, and they're concentrated enough
(one pairing is over half of them) that rating them would rate a rivalry
rather than the ladder. Everything else is unchanged, so the tests that matter
are the 1v1 boundary and the proof that the tournament link can't launder a
game that fails the gate for some other reason.
"""

from datetime import date, datetime

import pytest

from radarvan import player_rating
from radarvan.api_types import General, MatchInfo, Player, Team, TournamentTag
from radarvan.game_composition import MatchRoster
from radarvan.player_role import PlayerRole

BRACKET = TournamentTag(slug="2026_1v1_bracket", stage="WB2-1", round_name="WB R2")


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
    players: list[Player],
    *,
    tournament: TournamentTag | None = None,
    incomplete: str = "",
    match_id: int = 1215088593,
) -> MatchInfo:
    return MatchInfo(
        id=match_id,
        timestamp=datetime(2026, 8, 13, 6, 35, 18),
        date=date(2026, 8, 12),
        map="some_map",
        winning_team=Team.ONE,
        players=players,
        duration_minutes=17.7,
        filename="game.rep",
        incomplete=incomplete,
        composition=MatchRoster.from_players(players).composition(),
        tournament=tournament,
    )


def _1v1(**kwargs: object) -> MatchInfo:
    return _match(
        [
            _player("Skip", Team.ONE, "red", won=True),
            _player("Neo", Team.TWO, "blue", won=False),
        ],
        **kwargs,  # type: ignore[arg-type]
    )


def _2v2(**kwargs: object) -> MatchInfo:
    return _match(
        [
            _player("Skip", Team.ONE, "red", won=True),
            _player("Gorn", Team.ONE, "green", won=True),
            _player("Neo", Team.TWO, "blue", won=False),
            _player("Pancake", Team.TWO, "orange", won=False),
        ],
        **kwargs,  # type: ignore[arg-type]
    )


def test_tournament_1v1_is_ratable() -> None:
    match = _1v1(tournament=BRACKET)
    assert player_rating.is_tournament_1v1(match) is True
    assert player_rating.is_ratable_team_game(match) is True


def test_casual_1v1_is_not_ratable() -> None:
    match = _1v1()
    assert player_rating.is_tournament_1v1(match) is False
    assert player_rating.is_ratable_team_game(match) is False


@pytest.mark.parametrize("incomplete", ["disconnect", "too short"])
def test_incomplete_tournament_1v1_is_not_ratable(incomplete: str) -> None:
    """A tournament link doesn't make a disconnect a result."""
    assert (
        player_rating.is_ratable_team_game(_1v1(tournament=BRACKET, incomplete=incomplete))
        is False
    )


def test_unknown_player_in_a_tournament_1v1_is_not_ratable() -> None:
    """The link can't launder a game with someone outside player_ids."""
    match = _match(
        [
            _player("Skip", Team.ONE, "red", won=True),
            _player("SomeRandomPubbie", Team.TWO, "blue", won=False),
        ],
        tournament=BRACKET,
    )
    assert player_rating.is_ratable_team_game(match) is False


def test_team_games_are_unaffected_by_the_tournament_tag() -> None:
    """The 1v1 rule must not change anything about team games."""
    assert player_rating.is_ratable_team_game(_2v2()) is True
    assert player_rating.is_ratable_team_game(_2v2(tournament=BRACKET)) is True


def test_a_2v2_is_never_a_tournament_1v1() -> None:
    assert player_rating.is_tournament_1v1(_2v2(tournament=BRACKET)) is False


def test_ratings_move_for_a_tournament_1v1() -> None:
    """End to end: the rating pass actually consumes the game.

    `is_ratable_team_game` is the gate, but `build_teams` has to cope with
    one-player teams for the game to reach the model at all.
    """
    result = player_rating.compute_player_ratings([_1v1(tournament=BRACKET)])
    assert result.game_counts["Skip"] == 1
    assert result.game_counts["Neo"] == 1
    # `.ratings` is gated on MIN_GAMES, so read the per-match deltas instead:
    # the winner gained rating and the loser lost it.
    assert result.match_changes["Skip"][0].delta > 0
    assert result.match_changes["Neo"][0].delta < 0


def test_a_casual_1v1_moves_nothing() -> None:
    # A distinct id on purpose: compute_player_ratings is cached on the set of
    # match ids, so reusing the default would return the other test's result.
    result = player_rating.compute_player_ratings([_1v1(match_id=999000001)])
    assert result.game_counts.get("Skip", 0) == 0
    assert result.match_changes.get("Skip", []) == []
