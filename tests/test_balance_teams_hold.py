"""The six-hour hold on /api/balance_teams/.

The numbers themselves come from `create_teams.balance_teams`, which is a
derivation over CORPUS and so re-ranks the splits whenever a game lands. Some of
the group want that; the rest want the teams they were handed at the start of the
evening to still be the teams an hour later. The route resolves that by freezing
its answer per roster, and this pins the promise it makes:

* the same roster inside the window gets the same numbers back,
* *even if the corpus moved underneath it* - which is the whole point, and the
  one property a version-keyed cache cannot provide,
* a different roster is a fresh computation.

The hold is exercised with a counter standing in for the derivation rather than
real ratings: `tests/corpus.py` has 15 games against `player_rating.MIN_GAMES`,
so every real rating would be empty and "the two answers match" would be true for
the wrong reason.
"""

import pytest

from radarvan.routes import players


@pytest.fixture(autouse=True)
def _empty_hold():
    """Each test starts with an empty hold and leaves one behind."""
    with players._balance_cache_lock:
        players._balance_cache.clear()
    yield
    with players._balance_cache_lock:
        players._balance_cache.clear()


class _Scores:
    """Stands in for the derivation; returns a different answer every call."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, games, player_list):
        self.calls += 1
        # Keyed by a real team tuple so the route's name-remapping still runs.
        return {("Skip", "CoreDawg"): float(self.calls)}


@pytest.fixture
def scores(monkeypatch: pytest.MonkeyPatch) -> _Scores:
    stub = _Scores()
    monkeypatch.setattr(players.create_teams, "balance_teams", stub)
    # The corpus read only happens on a miss; a hit must not reach it at all.
    monkeypatch.setattr(players, "competitive_matches", lambda rm: {})
    return stub


ROSTER = ["Skip", "CoreDawg", "Syn", "Pancake"]


def _call(roster: list[str]) -> dict[str, float]:
    return players.balance_teams(players=roster, replay_manager=object())


def test_the_same_roster_gets_the_same_numbers_back(scores: _Scores) -> None:
    first = _call(ROSTER)
    second = _call(ROSTER)
    assert first == second, "the hold did not hold; the roster was re-derived"
    assert scores.calls == 1


def test_the_hold_survives_the_corpus_moving(
    scores: _Scores, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The reason this is a wall clock and not a version token.

    A game landing mid-evening changes the ratings, and a derivation would
    re-rank the splits. Here it must not.
    """
    first = _call(ROSTER)

    # A game lands: the corpus the route would read is now a different one.
    monkeypatch.setattr(players, "competitive_matches", lambda rm: {1: object()})

    assert _call(ROSTER) == first, (
        "a new game changed the answer inside the hold window; the teams handed "
        "out at the start of the evening would shuffle under the group"
    )
    assert scores.calls == 1


def test_an_alias_is_the_same_roster(scores: _Scores) -> None:
    """Clients send in-game aliases; `skp` and `Skip` are one player.

    The *scores* are shared; the labels are not, because each caller gets the
    spellings they sent (see the next test).
    """
    first = _call(["skp", "CoreDawg", "Syn", "Pancake"])
    second = _call(ROSTER)
    assert scores.calls == 1, "an alias spelling opened a second hold entry"
    assert sorted(first.values()) == sorted(second.values())


def test_the_caller_sees_the_names_they_sent(scores: _Scores) -> None:
    """The raw spelling is re-applied per request, so it must not be frozen too."""
    _call(ROSTER)
    aliased = _call(["skp", "CoreDawg", "Syn", "Pancake"])
    assert "skp,CoreDawg" in aliased, (
        f"the second caller got the first caller's spelling back: {aliased}"
    )


def test_a_different_roster_is_a_fresh_computation(scores: _Scores) -> None:
    _call(ROSTER)
    _call([*ROSTER, "Modus", "OneThree111"])
    assert scores.calls == 2


def test_too_few_players_is_not_held(scores: _Scores) -> None:
    assert _call(["Skip", "CoreDawg", "Syn"]) == {}
    assert scores.calls == 0, "a roster too small to split still reached the model"


def test_the_window_is_six_hours() -> None:
    assert players._balance_cache.ttl == 6 * 60 * 60
