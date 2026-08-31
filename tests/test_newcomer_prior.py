"""What the rating pass assumes about someone it has barely seen play.

A brand-new player used to be seeded at openskill's own default of mu=25. That
is not a neutral number here: this corpus has drifted to a mu range of roughly
10..38, so the default seeded a newcomer above two thirds of the regulars, and a
newcomer with a barely-winning record came out fifth of seventeen.

Two things had to change together, and both are asserted below. The prior is now
*relative* - one beta below the weakest established player, at double the usual
uncertainty - because lowering it in absolute terms does nothing: openskill has
no anchor, so shifting every seed down shifts every rating down and leaves the
ordering identical. And its mu is re-applied on every pass, because
``compute_player_ratings`` feeds each pass the previous pass's output, so a
starting prior only ever constrains pass 1 and is swamped by the ones after it.
"""

from radarvan import player_ids, player_rating
from radarvan.api_types import Team

from corpus import TEAM_ONE, match, rated_corpus


def _corpus_with_newcomer(newcomer: str, games: int, first_id: int):
    """An established four-player corpus, plus `games` more with the newcomer.

    The newcomer replaces a regular on team one and wins every one of them, so
    their record alone argues for a high rating and only the prior holds it down.
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


def test_a_brand_new_player_is_seeded_below_every_regular() -> None:
    result = player_rating.compute_player_ratings(rated_corpus())
    prior = result.newcomer_prior

    assert result.ratings, "fixture problem: nobody cleared MIN_GAMES"
    weakest = min(r.mu for r in result.ratings)
    assert prior.mu < weakest, (
        f"a newcomer is seeded at mu={prior.mu:.2f}, at or above the weakest "
        f"established player's {weakest:.2f}"
    )


def test_a_brand_new_player_is_seeded_with_high_uncertainty() -> None:
    result = player_rating.compute_player_ratings(rated_corpus())
    prior = result.newcomer_prior

    assert prior.sigma > max(r.sigma for r in result.ratings), (
        "'we have not seen you play' has to be a wider claim than any rating "
        "we have actually measured"
    )
    assert prior.sigma == player_rating.get_model().sigma * (
        player_rating.NEW_PLAYER_SIGMA_SCALE
    )


def test_the_prior_tracks_the_scale_rather_than_a_fixed_number() -> None:
    """It is defined against the players we know, not against openskill's origin.

    The whole mu scale is free to drift - which is how the library default of 25
    ended up seeding a newcomer near the top of this group. Anchoring to the
    weakest established player is what keeps 'assume they are the weakest here'
    true as it moves.
    """
    result = player_rating.compute_player_ratings(rated_corpus())
    prior = result.newcomer_prior

    model = player_rating.get_model()
    weakest = min(
        r.mu for r in result.ratings if not player_ids.is_cpu_name(r.name)
    )
    assert prior.mu == weakest - player_rating.NEW_PLAYER_MARGIN_BETAS * model.beta


def test_with_no_established_players_the_prior_falls_back_to_the_default() -> None:
    """First pass, or a corpus too small for anyone to qualify: no information
    to be relative to, so the model's own default is the honest answer."""
    result = player_rating.compute_player_ratings(rated_corpus(games=3))
    assert not result.ratings, "fixture problem: someone cleared MIN_GAMES"
    assert result.newcomer_prior.mu == player_rating.get_model().mu


def test_a_newcomer_on_a_winning_run_is_held_below_the_regulars() -> None:
    """Ten straight wins is not yet evidence of being the best player here.

    Before the prior was re-applied per pass, a sub-MIN_GAMES player with a
    winning record came out near the top of the table: the seed washed out and
    nothing else pulled them back.
    """
    games = _corpus_with_newcomer("WilyWolf", games=10, first_id=771000)
    result = player_rating.compute_player_ratings(games)

    newcomer = result.all_ratings["WilyWolf"]
    established = [r for r in result.ratings if not player_ids.is_cpu_name(r.name)]
    assert established, "fixture problem: nobody cleared MIN_GAMES"
    assert newcomer.mu < max(r.mu for r in established), (
        f"a 10-game newcomer was rated the strongest player in the group "
        f"(mu={newcomer.mu:.2f})"
    )


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


def test_full_trust_arrives_without_a_step() -> None:
    """The trust weight ramps to 1.0 and stays there, so crossing the line is
    not an event. A threshold would jump a player's rating the night they hit
    it; here the weight is already 1.0 on the last game before."""
    counts = {"Established": player_rating.MIN_GAMES}
    ratings = {"Established": player_rating.NamedRating("Established", 30.0, 2.0)}
    model = player_rating.get_model()

    at_threshold = player_rating._reseed(ratings, counts, model)["Established"]
    counts["Established"] += 1
    past_threshold = player_rating._reseed(ratings, counts, model)["Established"]

    assert at_threshold.mu == past_threshold.mu == 30.0
    assert at_threshold.sigma == past_threshold.sigma == player_rating.MIN_SIGMA


def test_an_established_player_keeps_their_own_rating_through_a_reseed() -> None:
    """The reseed has to reduce to the plain sigma floor it replaced, or every
    pass would drag the whole table toward the newcomer prior."""
    model = player_rating.get_model()
    counts = {"Veteran": 500, "HardArmy": 3}
    ratings = {
        "Veteran": player_rating.NamedRating("Veteran", 9.0, 6.0),
        # A CPU is exempt whatever its game count: it gets its own seed in
        # `initialize_player` and is not a newcomer.
        "HardArmy": player_rating.NamedRating("HardArmy", 23.0, 6.0),
    }
    reseeded = player_rating._reseed(ratings, counts, model)

    assert reseeded["Veteran"].mu == 9.0
    assert reseeded["Veteran"].sigma == 6.0
    assert reseeded["HardArmy"].mu == 23.0
    assert reseeded["HardArmy"].sigma == 6.0
