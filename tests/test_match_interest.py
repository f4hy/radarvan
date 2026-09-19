"""The interest score: a hand-weighted read of how worth retelling a match is.

There is no label for "interesting", so what is pinned is ordering and
explainability - a back-and-forth game outscores a stomp, a short game is
discounted however dramatic its curve, and every quoted reason is one of the
signals that actually fired.
"""

from radarvan import match_interest
from radarvan.api_types import MatchDetails, TimelineEvent

import corpus

BACK_AND_FORTH = corpus.BACK_AND_FORTH
STOMP = corpus.STOMP


def _details(winner_probs: list[float] | None, **overrides: object) -> MatchDetails:
    curve = corpus.win_prob_over_time(winner_probs) if winner_probs is not None else None
    return corpus.details(win_prob_over_time=curve, **overrides)


def _interest(
    winner_probs: list[float] | None, minutes: float = 20.0, **overrides: object
) -> match_interest.Interest | None:
    match = corpus.match(1, day=5, duration_minutes=minutes)
    return match_interest.match_interest(match, _details(winner_probs, **overrides))


def test_a_match_without_a_curve_has_no_score() -> None:
    """None, not zero: an FFA or an unparsed game was never assessed."""
    assert _interest(None) is None


def test_a_stomp_scores_near_zero_and_quotes_no_reason() -> None:
    interest = _interest(STOMP)
    assert interest is not None
    assert interest.score < 0.1
    assert interest.reasons == []


def test_a_back_and_forth_game_outscores_a_stomp() -> None:
    lively, stomp = _interest(BACK_AND_FORTH), _interest(STOMP)
    assert lively is not None and stomp is not None
    assert lively.score > 0.5 > stomp.score


def test_the_reasons_are_the_signals_that_fired() -> None:
    interest = _interest(BACK_AND_FORTH)
    assert interest is not None
    assert "the lead changed hands 3 times" in interest.reasons
    assert any("were down to 15% to win" in reason for reason in interest.reasons)


def test_at_most_three_reasons_are_quoted() -> None:
    launch = TimelineEvent(
        player_name="Skip",
        at_minute=5.0,
        event_name="ScudStorm",
        event_type="superweapon_activated",
    )
    interest = _interest(
        BACK_AND_FORTH, timeline_events=[launch, launch], time_to_hunted={"Syn": 9.0}
    )
    assert interest is not None
    assert len(interest.reasons) == match_interest.MAX_REASONS


def test_a_short_game_is_discounted_however_dramatic() -> None:
    short, long = _interest(BACK_AND_FORTH, minutes=4.0), _interest(BACK_AND_FORTH)
    assert short is not None and long is not None
    assert short.score < long.score


def test_a_generals_power_is_not_spectacle_but_a_superweapon_is() -> None:
    def launch(name: str) -> TimelineEvent:
        return TimelineEvent(
            player_name="Skip",
            at_minute=5.0,
            event_name=name,
            event_type="superweapon_activated",
        )

    plain, power, nuke = (
        _interest(STOMP, timeline_events=events)
        for events in ([], [launch("SpectreGunship")], [launch("NuclearMissile")])
    )
    assert plain is not None and power is not None and nuke is not None
    assert power.score == plain.score
    assert nuke.score > plain.score


def test_an_underdog_win_that_never_trailed_after_the_prior_settles_is_no_comeback() -> None:
    interest = _interest([0.15, 0.2, 0.3, 0.45, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99])
    assert interest is not None
    assert not any("were down to" in reason for reason in interest.reasons)
