"""Reading the win-probability curve from the winners' side.

The curve is jumpy and snaps to ~100% on its last bucket, so the pinned
behaviour is what each measure ignores: jitter around even odds, slow drifts,
and rises too small to be anything but the model catching up to its prior.
"""

import pytest

from radarvan import win_curve

import corpus


def _curve(winner_probs: list[float]) -> win_curve.WinnerCurve:
    curve = win_curve.winner_curve(corpus.win_prob_over_time(winner_probs))
    assert curve is not None
    return curve


def test_the_curve_is_read_from_the_winning_side() -> None:
    curve = win_curve.winner_curve(corpus.win_prob_over_time([0.2, 0.9], winner="team_b"))
    assert curve is not None
    assert curve.probs == pytest.approx([0.8, 0.1])
    assert curve.winners == ["Syn", "Pancake"]
    assert curve.losers == ["Skip", "CoreDawg"]


def test_no_curve_without_a_decided_winner_or_points() -> None:
    assert win_curve.winner_curve(None) is None
    assert win_curve.winner_curve(corpus.win_prob_over_time([0.5], winner=None)) is None
    assert win_curve.winner_curve(corpus.win_prob_over_time([])) is None


def test_the_biggest_swing_is_the_largest_rise_inside_the_window() -> None:
    swing = win_curve.biggest_swing(_curve([0.5, 0.2, 0.25, 0.7, 0.7, 0.7]))
    assert swing is not None
    assert (swing.start_minute, swing.end_minute) == (1.0, 2.0)
    assert swing.rise == pytest.approx(0.5)


def test_a_rise_slower_than_the_window_is_not_a_swing() -> None:
    """0.30 -> 0.60 over four minutes is a drift, however far it goes."""
    drift = [0.30 + 0.30 * i / 8 for i in range(9)]
    assert win_curve.biggest_swing(_curve(drift)) is None


def test_a_rise_below_the_floor_is_the_model_settling_not_a_swing() -> None:
    assert win_curve.biggest_swing(_curve([0.5, 0.6, 0.7])) is None


def test_only_the_winners_rise_counts_as_a_swing() -> None:
    """A collapse of the eventual winners is not their turning point."""
    assert win_curve.biggest_swing(_curve([0.9, 0.5, 0.4])) is None


def _settled_curve(winner_probs: list[float]) -> win_curve.WinnerCurve:
    """The same curve after the two minutes the model spends settling off its prior."""
    return _curve([0.5] * 4 + winner_probs)


def test_jitter_around_even_odds_is_not_a_lead_change() -> None:
    assert win_curve.lead_changes(_settled_curve([0.45, 0.55, 0.48, 0.56, 0.5])) == 0


def test_a_lead_changes_hands_once_it_clears_the_band_on_the_other_side() -> None:
    assert win_curve.lead_changes(_settled_curve([0.8, 0.5, 0.3, 0.2, 0.7])) == 2


def test_a_wire_to_wire_game_never_changes_lead() -> None:
    assert win_curve.lead_changes(_settled_curve([0.7, 0.8, 0.9, 1.0])) == 0


def test_contested_share_is_the_fraction_of_points_within_reach() -> None:
    assert win_curve.contested_share(_curve([0.5, 0.6, 0.9, 0.99])) == 0.5


def test_an_underdog_climbing_off_its_prior_is_not_a_lead_change() -> None:
    """Started at 20% on the roster alone and never trailed anything real."""
    assert win_curve.lead_changes(_curve([0.2, 0.3, 0.45, 0.6, 0.7, 0.8, 0.9])) == 0


def test_the_deepest_deficit_ignores_the_prior_and_a_game_too_short_to_settle() -> None:
    assert win_curve.deepest_deficit(_curve([0.1, 0.1, 0.1, 0.1, 0.6, 0.8])) == 0.6
    assert win_curve.deepest_deficit(_curve([0.1, 0.2, 0.3, 0.4])) == 0.5


def test_a_swing_owns_its_window_and_whether_it_flipped_the_lead() -> None:
    from_behind = win_curve.Swing(1.5, 3.0, 0.25, 0.9)
    assert from_behind.flipped_lead
    assert not win_curve.Swing(1.5, 3.0, 0.49, 0.92).flipped_lead
    assert from_behind.contains(3.0) and from_behind.contains(2.0)
    assert not from_behind.contains(1.5) and not from_behind.contains(3.1)
