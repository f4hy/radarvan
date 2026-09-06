"""Guest ratings - the (semi-)pro visitors seeded at a static, high starting mu.

`player_rating.GUEST_INITIAL_MU` gives each guest a rating floor high enough to
reflect that they already outclass the group, without waiting on MIN_GAMES worth
of real results to prove it - useful both for `/api/balance_teams/` (building a
fair game around someone who outclasses the whole roster) and for the admin
ratings page, which now lists them too. Unlike the old asserted-forever design,
the seed is only a *starting point*: `compute_player_ratings` runs a single
pass (see its module docstring), so nothing ever pulls a guest back toward a
prior the way a multi-pass design would - real games just move their rating
like anyone else's from there.
"""

import pytest

from radarvan.api_types import Team
from radarvan import create_teams, player_ids, player_rating, player_synergy

from corpus import TEAM_ONE, TEAM_TWO, match, rated_corpus


GUESTS = ("Excal", "Marakar", "Domi")


@pytest.fixture(scope="module")
def computed():
    games = rated_corpus()
    result = player_rating.compute_player_ratings(games)
    assert result.ratings, "fixture problem: nobody cleared MIN_GAMES"
    return result


# --- the aliases -----------------------------------------------------------


@pytest.mark.parametrize(
    ("spelling", "canonical"),
    [
        ("[OoE]ExCaL^", "Excal"),
        ("excal", "Excal"),
        ("[OoE]Marakar*", "Marakar"),
        ("marakar", "Marakar"),
        ("[OoE]Maraka*", "Marakar"),
        ("Domi", "Domi"),
        ("domi", "Domi"),
        ("-DoMiNaToR-", "Domi"),
    ],
)
def test_the_in_game_spellings_resolve(spelling: str, canonical: str) -> None:
    """These are the spellings that actually appear in the corpus. A guest whose
    in-game name does not resolve gets none of the seed - `rating_for` would be
    asked about "[OoE]ExCaL^" and hand back the newcomer prior."""
    assert player_ids.resolve_player_name(spelling) == canonical


@pytest.mark.parametrize("name", GUESTS)
def test_a_guest_is_a_selectable_player(name: str) -> None:
    """`PlayerEnum` - the Balance Teams checkboxes - is generated from
    `PLAYER_NAMES`, so membership here *is* being on the page."""
    assert name in player_ids.PLAYER_NAMES
    assert name in player_ids.HUMAN_NAMES


# --- the starting seed -------------------------------------------------------


@pytest.mark.parametrize("name", GUESTS)
def test_a_guest_who_has_not_played_sits_exactly_at_its_seed(
    computed, name: str
) -> None:
    """With no real games to move it, a guest's rating is exactly the static
    value in `GUEST_INITIAL_MU` - `rated_corpus` contains none of the three."""
    assert computed.rating_for(name).mu == player_rating.GUEST_INITIAL_MU[name]


def test_the_guests_outrank_everyone_in_the_stated_order(computed) -> None:
    best_real = next(r for r in computed.ratings if r.name not in GUESTS).ordinal()
    excal = computed.rating_for("Excal").ordinal()
    marakar = computed.rating_for("Marakar").ordinal()
    domi = computed.rating_for("Domi").ordinal()
    assert excal > marakar > domi > best_real


def test_a_guest_who_has_never_played_still_has_a_rating(computed) -> None:
    """The point of the feature is next week's game night, before which one of
    them may have no games in the corpus at all. `rated_corpus` contains neither
    guest, so this is that case."""
    assert "Excal" not in {p.name for g in rated_corpus() for p in g.players}
    assert computed.rating_for("Excal").sigma == player_rating.GUEST_SIGMA


def test_a_guest_is_stated_confidently(computed) -> None:
    """`predict_win` divides the mu gap by the teams' pooled uncertainty, so a
    wide sigma would make a guest read as a smaller edge than intended. All
    three start at the tight guest sigma - not the wide "unseen newcomer"
    default a name we don't recognize at all would get."""
    assert {computed.rating_for(n).sigma for n in GUESTS} == {player_rating.GUEST_SIGMA}
    assert player_rating.GUEST_SIGMA < player_rating.NEWCOMER_PRIOR_SIGMA


# --- real games move it -----------------------------------------------------


def _excal_losing_streak():
    """Four real losses for Excal against a clearly weaker opponent."""
    return [
        match(9500 + i, day=28 + i, winner=Team.TWO, team_one=("Excal", "Skip"))
        for i in range(4)
    ]


def test_a_guest_who_actually_lost_moves_off_the_seed() -> None:
    """The whole point of seeding rather than asserting forever: a real losing
    streak against clearly weaker opponents has to pull the rating down, not
    leave it pinned at the starting value."""
    computed = player_rating.compute_player_ratings(rated_corpus() + _excal_losing_streak())
    assert computed.rating_for("Excal").mu < player_rating.GUEST_INITIAL_MU["Excal"]


def test_a_guest_who_actually_won_stays_at_or_above_the_seed() -> None:
    """Symmetric check: winning every real game should not pull the rating
    down from the seed the way losing does."""
    wins = [
        match(9600 + i, day=28 + i, winner=Team.ONE, team_one=("Excal", "Skip"))
        for i in range(4)
    ]
    computed = player_rating.compute_player_ratings(rated_corpus() + wins)
    assert computed.rating_for("Excal").mu >= player_rating.GUEST_INITIAL_MU["Excal"]


def test_a_few_losses_do_not_drop_a_guest_below_a_converged_regular() -> None:
    """A regression case: a guest's tight starting sigma (`GUEST_SIGMA`) exists
    so their ordinal isn't crushed by uncertainty a handful of games can never
    shrink away the way hundreds of real games let a regular's sigma converge
    - without it, a guest could read as *worse* on ordinal than an established
    regular despite a clearly higher mu, backwards for someone asserted to
    outclass the group. A losing streak should cost a guest ground, but not
    hand it all back this fast."""
    established = [
        match(9700 + i, day=5 + (i % 23), winner=Team.ONE if i % 3 else Team.TWO)
        for i in range(500)
    ]
    computed = player_rating.compute_player_ratings(
        rated_corpus() + established + _excal_losing_streak()
    )
    best_regular = next(r for r in computed.ratings if r.name not in GUESTS)
    assert computed.rating_for("Excal").ordinal() > best_regular.ordinal()


def test_a_guest_who_has_played_shows_up_in_rating_over_time() -> None:
    """`over_time` normally cuts anyone under 30 tracked entries - guests are
    exempted from that cut too, since the point of a starting seed instead of
    a forever-asserted number is to be able to see it move."""
    computed = player_rating.compute_player_ratings(rated_corpus() + _excal_losing_streak())
    assert "Excal" in computed.over_time
    assert len(computed.over_time["Excal"]) == 4


# --- the blast radius --------------------------------------------------------


def test_a_guest_does_reach_the_published_leaderboard(computed) -> None:
    """`.ratings` is the display list and the only place a rating *level* is
    meant to reach the wire (see CLAUDE.md) - but that page is admin-gated, so
    there's no public-exposure concern here. A guest's rating starts asserted
    rather than earned, so the MIN_GAMES "not enough games to trust it" cut
    doesn't apply: guests are exempted from it and always appear."""
    assert {r.name for r in computed.ratings} & set(GUESTS) == set(GUESTS)


def test_a_guest_does_not_reach_synergy() -> None:
    """`player_synergy` filters on `.ratings` membership to keep out anyone
    under MIN_GAMES - since a guest now sits on `.ratings` regardless of games
    played, that filter alone no longer excludes them, so `compute_player_synergy`
    has its own explicit guest exclusion. A guest's handful of real games must
    not seed a pair coefficient off so little data."""
    games = rated_corpus() + [
        match(9800 + i, day=28 + i, winner=Team.ONE, team_one=("Excal", "Skip"))
        for i in range(4)
    ]
    pairs = player_synergy.compute_player_synergy(games)
    assert not any("Excal" in (p.player_a, p.player_b) for p in pairs)


def test_the_seed_moves_nobody_else(monkeypatch) -> None:
    """Seeding a guest high changes how *their own* real games rate (see the
    tests above) - it must not change anyone else's rating who never played
    them. `rated_corpus` contains no guest games, so this isolates the seed
    itself from the real-game-movement behavior."""
    games = rated_corpus()
    seeded = player_rating.compute_player_ratings(games)

    monkeypatch.setattr(player_rating, "GUEST_INITIAL_MU", {})
    try:
        # `compute_player_ratings` is @derived: its key is the corpus, which has
        # not changed, so the patched run needs the entry gone both on the way
        # in and on the way out. Skipping the second clear leaves the *unseeded*
        # ratings cached under the real corpus key for every later test.
        player_rating.compute_player_ratings.cache_clear()
        plain = player_rating.compute_player_ratings(games)
    finally:
        player_rating.compute_player_ratings.cache_clear()

    for name in plain.all_ratings:
        assert seeded.rating_for(name).mu == pytest.approx(plain.rating_for(name).mu)
    assert seeded.newcomer_prior.mu == pytest.approx(plain.newcomer_prior.mu)


def test_a_guest_does_not_anchor_the_newcomer_prior(computed) -> None:
    """The prior is one beta *below the weakest established player*. A guest
    leaking into that set would drag every stranger's assumed rating with it."""
    assert computed.newcomer_prior.mu < computed.ratings[-1].mu


# --- what it is for --------------------------------------------------------


def test_the_balancer_hands_a_guest_the_weaker_partner() -> None:
    """The whole point of the feature. Given Excal, the group's best player and
    its two weakest, the closest game is the one that does *not* put Excal with
    the best player - which is the answer the balancer gave before the seed
    only by accident, when the guest read as a newcomer and got stacked with the
    strongest side to make up the difference.

    Asserted as "not the strongest" rather than a named partner: the fixture
    corpus has two exact rating tiers, so which of the two weak regulars comes
    back is a tie-break, not a result.
    """
    games = rated_corpus()
    computed = player_rating.compute_player_ratings(games)
    by_ordinal = sorted(
        TEAM_ONE + TEAM_TWO,
        key=lambda n: computed.rating_for(n).ordinal(),
        reverse=True,
    )
    strongest, *_ = by_ordinal
    roster = {"Excal", strongest, *by_ordinal[-2:]}

    scores = create_teams.balance_teams(games, player_list=frozenset(roster))
    closest, _ = min(scores.items(), key=lambda kv: abs(kv[1] - 0.5))
    # Only the favoured side is stored, so the guest's side may be either one.
    guest_side = set(closest) if "Excal" in closest else roster - set(closest)
    assert strongest not in guest_side


def test_a_guest_is_worth_more_than_the_whole_gap_between_regulars() -> None:
    """A sanity floor on the seed: taking Excal has to outweigh every swap
    available among the regulars, or the balancer would still be shuffling
    the group and ignoring him."""
    games = rated_corpus()
    computed = player_rating.compute_player_ratings(games)
    ordinals = [computed.rating_for(n).ordinal() for n in TEAM_ONE + TEAM_TWO]
    spread = max(ordinals) - min(ordinals)
    assert computed.rating_for("Excal").ordinal() - max(ordinals) > spread
