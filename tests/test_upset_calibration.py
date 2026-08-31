"""The probability the Biggest Upset card prints has to mean something.

``PlackettLuce.predict_win`` sums a team's mus into the numerator but keeps a
single ``2*beta^2`` in the denominator however many players are on the team, so
its confidence barely moves between a 1v1 and a 4v4 even though what it knows
about the outcome collapses. Measured as-of, the favourite it named won 75% of
1v1s and 49% of 4v4s while it stated 0.81 and 0.71.

``player_rating.displayed_win_probs`` scales the noise with the team instead.
These pin the properties that fix depends on, not the fitted constant - the
number in ``DISPLAY_BETA`` is allowed to be refitted as the corpus grows.
"""

import pytest

from radarvan.player_rating import DISPLAY_BETA, displayed_win_probs, get_model


def _team(mu: float, n: int, sigma: float = 2.1):
    model = get_model()
    return [model.rating(mu=mu, sigma=sigma) for _ in range(n)]


def test_equal_teams_are_a_coin_flip() -> None:
    for n in (1, 2, 3, 4):
        assert displayed_win_probs([_team(25, n), _team(25, n)])[0] == pytest.approx(0.5)


def test_swapping_teams_gives_complementary_probabilities() -> None:
    a, b = _team(35, 2), _team(15, 2)
    p_ab = displayed_win_probs([a, b])[0]
    p_ba = displayed_win_probs([b, a])[0]
    assert p_ab + p_ba == pytest.approx(1.0)


def test_confidence_falls_as_the_same_edge_is_spread_over_more_players() -> None:
    """The property ``predict_win`` lacks, and the whole reason this exists.

    A 20-point total mu advantage is far stronger evidence in a 1v1 than the
    same 20 points shared across four players, because three more coin flips
    ride on the result. ``predict_win`` states ~0.97-0.98 for all four.
    """
    gap = 20.0
    probs = [
        displayed_win_probs([_team(25 + gap / n, n), _team(25, n)])[0]
        for n in (1, 2, 3, 4)
    ]
    assert probs == sorted(probs, reverse=True)
    assert probs[0] > 0.9  # a 20-point 1v1 edge really is near-certain
    assert probs[-1] < 0.75  # the same edge spread over a 4v4 is not


def test_favoured_team_matches_predict_win() -> None:
    """Monotone in the mu difference, so it can never re-pick the favourite.

    That is what lets this replace the printed probability without changing
    which games are flagged as upsets.
    """
    model = get_model()
    for mu_a in (10.0, 20.0, 25.0, 30.0, 40.0):
        for n in (1, 2, 3, 4):
            teams = [_team(mu_a, n), _team(25.0, n)]
            ours = displayed_win_probs(teams)[0]
            theirs = model.predict_win(teams=teams)[0]
            assert (ours > 0.5) == (theirs > 0.5)
            assert (ours < 0.5) == (theirs < 0.5)


def test_more_uncertain_players_widen_the_interval() -> None:
    """A high-sigma (new/rarely-seen) player pulls the prediction toward 0.5."""
    confident = displayed_win_probs([_team(35, 2, sigma=2.0), _team(15, 2, sigma=2.0)])[0]
    unsure = displayed_win_probs([_team(35, 2, sigma=8.0), _team(15, 2, sigma=2.0)])[0]
    assert 0.5 < unsure < confident


def test_rejects_anything_but_two_teams() -> None:
    with pytest.raises(ValueError, match="exactly 2 teams"):
        displayed_win_probs([_team(25, 2), _team(25, 2), _team(25, 2)])


def test_display_beta_is_not_the_rating_beta() -> None:
    """Changing the rating beta would move every rating; these stay independent."""
    assert get_model().beta != DISPLAY_BETA
