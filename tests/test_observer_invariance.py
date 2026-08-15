"""Spectators must not change what a match *is*.

Adding or removing an observer changes nothing about who played, so it must
change nothing about categorization, ratability, or any per-player stat. This
had regressed in two places at once: `filter_for_rating` read every slot, so a
caster account named for the matchup ("Gorn.v.131" - nobody in `player_ids`)
made the whole game unratable, and the win-streak pass counted a spectator's
`won=False` slot as a loss.

The invariance is stated as "same answer with and without the observer" rather
than as a fixed expected value on purpose: it holds no matter what the rule
underneath decides.
"""

from datetime import date, datetime

import pytest

from ml.snapshot import is_training_match
from radarvan import player_rating, superlatives
from radarvan.api_types import General, MatchInfo, Player, Team, TournamentTag
from radarvan.player_role import PlayerRole

# Real names: filter_for_rating rejects anyone outside player_ids.
TEAM_A = ["Skip", "Gorn"]
TEAM_B = ["Neo", "Pancake"]

# The account the bracket is streamed from. Deliberately not a known player.
CASTER = "Gorn.v.131"


def _player(name: str, team: Team, color: str, *, won: bool) -> Player:
    return Player(
        name=name,
        general=General.USA,
        team=team,
        color=color,
        won=won,
        role=PlayerRole.HUMAN,
    )


def _observer(name: str = CASTER) -> Player:
    return Player(
        name=name,
        general=General.UNRECOGNIZED,
        team=Team.OBSERVER,
        color="-1",
        won=False,
        role=PlayerRole.OBSERVER,
    )


def _match(
    players: list[Player],
    *,
    match_id: int = 1215088593,
    when: datetime = datetime(2026, 8, 13, 6, 35, 18),
    night: date = date(2026, 8, 12),
    tournament: TournamentTag | None = None,
) -> MatchInfo:
    """A match whose composition is derived from the slots, as in production."""
    from radarvan.game_composition import MatchRoster

    return MatchInfo(
        id=match_id,
        timestamp=when,
        date=night,
        map="some_map",
        winning_team=Team.ONE,
        players=players,
        duration_minutes=17.7,
        filename=f"game_{match_id}.rep",
        composition=MatchRoster.from_players(players).composition(),
        tournament=tournament,
    )


def _2v2_slots() -> list[Player]:
    return [
        _player(TEAM_A[0], Team.ONE, "red", won=True),
        _player(TEAM_A[1], Team.ONE, "green", won=True),
        _player(TEAM_B[0], Team.TWO, "blue", won=False),
        _player(TEAM_B[1], Team.TWO, "orange", won=False),
    ]


def _1v1_slots() -> list[Player]:
    return [
        _player(TEAM_A[0], Team.ONE, "red", won=True),
        _player(TEAM_B[0], Team.TWO, "blue", won=False),
    ]


@pytest.fixture(params=["2v2", "1v1"], ids=["2v2", "1v1"])
def slots(request: pytest.FixtureRequest) -> list[Player]:
    return _2v2_slots() if request.param == "2v2" else _1v1_slots()


@pytest.fixture(params=["caster", "known_player"], ids=["unknown", "known"])
def observer(request: pytest.FixtureRequest) -> Player:
    """Both flavours: an unrecognised caster and a known player sitting one out."""
    return _observer() if request.param == "caster" else _observer("Syn")


def test_composition_ignores_observers(
    slots: list[Player], observer: Player
) -> None:
    without = _match(slots).composition
    with_obs = _match([observer, *slots]).composition
    assert without is not None and with_obs is not None
    # total_players counts every slot by design; everything else must match.
    assert with_obs.model_dump(
        exclude={"total_players"}
    ) == without.model_dump(exclude={"total_players"})


def test_filter_for_rating_ignores_observers(
    slots: list[Player], observer: Player
) -> None:
    assert player_rating.filter_for_rating(
        _match([observer, *slots])
    ) is player_rating.filter_for_rating(_match(slots))


def test_is_ratable_team_game_ignores_observers(
    slots: list[Player], observer: Player
) -> None:
    assert player_rating.is_ratable_team_game(
        _match([observer, *slots])
    ) is player_rating.is_ratable_team_game(_match(slots))


def test_snapshot_membership_ignores_observers(
    slots: list[Player], observer: Player
) -> None:
    tag = TournamentTag(slug="2026_1v1_bracket", stage="WB2-1")
    assert is_training_match(
        _match([observer, *slots], tournament=tag)
    ) is is_training_match(_match(slots, tournament=tag))


def test_a_watched_2v2_is_still_ratable() -> None:
    """The concrete case: 23 real games were held out by the caster's slot."""
    assert player_rating.is_ratable_team_game(_match([_observer(), *_2v2_slots()]))


COMPUTED_AT = date(2026, 8, 20)


def _1v1_on(mid: int, day: int, winner: str, loser: str, *extra: Player) -> MatchInfo:
    return _match(
        [
            *extra,
            _player(winner, Team.ONE, "red", won=True),
            _player(loser, Team.TWO, "blue", won=False),
        ],
        match_id=mid,
        when=datetime(2026, 8, day, 1),
        night=date(2026, 8, day),
    )


def test_watching_does_not_break_a_win_streak() -> None:
    """Spectating is not losing.

    Skip wins two 1v1s; between them he sits out a third and watches. Nobody
    else wins twice, so the longest streak is his and his alone - which is what
    makes this fail when the observed game counts as a loss.
    """
    played = [_1v1_on(1, 1, "Skip", "Neo"), _1v1_on(3, 3, "Skip", "Pancake")]
    watched = _1v1_on(2, 2, "Syn", "Neo", _observer("Skip"))

    def longest(games: list[MatchInfo]) -> tuple[str, int]:
        stats = superlatives.get_win_streak_stats(games, COMPUTED_AT)
        stat = next(s for s in stats if "Longest Win Streak" in str(s.stat_name))
        return str(stat.player), int(stat.value)  # type: ignore[arg-type]

    assert longest([*played, watched]) == longest(played) == ("Skip", 2)


def test_watching_does_not_dent_a_30_day_record() -> None:
    """The same bug lived twice in superlatives.py, 700 lines apart.

    `get_monthly_stats` also read every slot, so casting a game booked a loss
    on the 30-day record. Skip goes 5-0 over the window and must still show as
    the best record with a game he only watched in the list.
    """
    played = [_1v1_on(i, i, "Skip", "Neo") for i in range(1, 6)]
    watched = _1v1_on(9, 9, "Syn", "Neo", _observer("Skip"))

    def best_record(games: list[MatchInfo]) -> tuple[str, str]:
        stats = superlatives.get_monthly_stats(games, {}, COMPUTED_AT)
        stat = next(s for s in stats if "Best Record" in str(s.stat_name))
        return str(stat.player), str(stat.value)

    assert best_record([*played, watched]) == best_record(played) == ("Skip", "5-0")
