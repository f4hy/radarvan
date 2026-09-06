"""What the rating pass assumes about someone it has barely seen play.

A brand-new player used to be seeded at openskill's own default of mu=25. That
is not a neutral number here: this corpus has drifted to a mu range of roughly
10..38, so the default seeded a newcomer above two thirds of the regulars, and a
newcomer with a barely-winning record came out fifth of seventeen.

The prior is now a flat constant (``NEWCOMER_PRIOR_MU``/``NEWCOMER_PRIOR_SIGMA``)
comfortably below and wider than the corpus's real players - the same static
style as ``GUEST_INITIAL_MU`` sits comfortably above them. If the corpus drifts
enough that it stops being comfortably low, move the constant; that tradeoff is
already accepted for the guests.

Unlike before, this prior is used *only* as `rating_for`'s fallback for a name
that hasn't played a single game yet (`compute_player_ratings` runs a single
pass now, not three - see player_rating.py's module docstring) - once someone
has played even one real game, their rating is whatever that single pass
computed from it, with no further artificial pull-back. A short winning streak
is allowed to move someone's rating a lot; openskill's own uncertainty (a wide
starting sigma moves more per game) is what keeps that appropriately provisional,
not a second layer of discounting on top.
"""

from radarvan import player_rating

from corpus import TEAM_ONE, match, rated_corpus
from radarvan.api_types import Team


def _corpus_with_newcomer(newcomer: str, games: int, first_id: int):
    """An established four-player corpus, plus `games` more with the newcomer.

    The newcomer replaces a regular on team one and wins every one of them.
    """
    base = rated_corpus()
    extra = [
        match(
            first_id + i,
            day=5 + (i % 23),
            winner=Team.ONE,
            team_one=(TEAM_ONE[0], newcomer),
        )
        for i in range(games)
    ]
    return base + extra


def test_the_prior_is_the_stated_constant() -> None:
    """A flat constant threaded straight through, not computed per corpus - so
    one call confirms the wiring; there's no leaderboard-dependent behavior
    left to test for it (no first-pass/bootstrap case, no corpus-size case)."""
    result = player_rating.compute_player_ratings(rated_corpus())
    assert result.newcomer_prior.mu == player_rating.NEWCOMER_PRIOR_MU
    assert result.newcomer_prior.sigma == player_rating.NEWCOMER_PRIOR_SIGMA


def test_a_brand_new_player_is_seeded_below_every_regular() -> None:
    """The prior only ever reaches the wire via `rating_for`'s fallback, for
    someone with zero games anywhere in the corpus - a hypothetical stranger
    being considered for next week's draft, say."""
    result = player_rating.compute_player_ratings(rated_corpus())
    real = [r for r in result.ratings if not player_rating.is_guest_name(r.name)]
    assert real, "fixture problem: nobody cleared MIN_GAMES"

    prior = result.newcomer_prior
    weakest = min(r.mu for r in real)
    assert prior.mu < weakest, (
        f"a newcomer is seeded at mu={prior.mu:.2f}, at or above the weakest "
        f"established player's {weakest:.2f}"
    )


def test_a_brand_new_player_is_seeded_with_high_uncertainty() -> None:
    result = player_rating.compute_player_ratings(rated_corpus())
    real = [r for r in result.ratings if not player_rating.is_guest_name(r.name)]
    prior = result.newcomer_prior

    assert prior.sigma > max(r.sigma for r in real), (
        "'we have not seen you play' has to be a wider claim than any rating "
        "we have actually measured"
    )


def test_a_real_winning_streak_can_outrate_established_players() -> None:
    """Deliberate, not a regression: a single pass has nothing left to hold a
    real, if thin, record down artificially. A newcomer who has actually won
    every one of their (few) real games is allowed to show it - openskill's
    own uncertainty (their sigma is still wide) is the only thing tempering
    it, not a second discount layered on top."""
    games = _corpus_with_newcomer("WilyWolf", games=10, first_id=771000)
    result = player_rating.compute_player_ratings(games)

    newcomer = result.all_ratings["WilyWolf"]
    real_regulars = [
        r for r in result.ratings if not player_rating.is_guest_name(r.name)
    ]
    assert real_regulars, "fixture problem: nobody cleared MIN_GAMES"
    assert newcomer.mu > max(r.mu for r in real_regulars)


def test_the_prior_loosens_as_a_newcomer_plays() -> None:
    """Monotone in games played, so nobody is stuck at the prior forever."""
    few = player_rating.compute_player_ratings(
        _corpus_with_newcomer("WilyWolf", games=5, first_id=772000)
    ).all_ratings["WilyWolf"]
    many = player_rating.compute_player_ratings(
        _corpus_with_newcomer("WilyWolf", games=40, first_id=773000)
    ).all_ratings["WilyWolf"]

    assert many.mu > few.mu, "more wins should buy more rating, not less"
    assert many.sigma < few.sigma, "more games should buy more certainty"
