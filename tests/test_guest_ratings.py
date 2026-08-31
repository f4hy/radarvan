"""Guest ratings - the two (semi-)pro visitors whose rating is asserted, not learned.

`player_rating.GUEST_RATING_MULTIPLIERS` puts a deliberate finger on the scale so
`/api/balance_teams/` can build a fair game around someone who outclasses the
whole group. What the tests here pin down is the *blast radius* of that lie: it
must reach `rating_for` (which is what the balancer and the ML baseline ask) and
nothing else - not the passes that rate everybody's real games, not the newcomer
prior, and not the published leaderboard.
"""

import pytest

from radarvan import create_teams, player_ids, player_rating

from corpus import TEAM_ONE, TEAM_TWO, rated_corpus


GUESTS = ("Excal", "Domi")


@pytest.fixture(scope="module")
def computed():
    games = rated_corpus()
    result = player_rating.compute_player_ratings(games)
    assert result.ratings, (
        "fixture problem: the corpus is under MIN_GAMES, so there is no leader "
        "to anchor the guest multipliers to"
    )
    return result


@pytest.fixture(scope="module")
def leader_ordinal(computed):
    return computed.ratings[0].ordinal()


# --- the aliases -----------------------------------------------------------


@pytest.mark.parametrize(
    ("spelling", "canonical"),
    [
        ("[OoE]ExCaL^", "Excal"),
        ("excal", "Excal"),
        ("Domi", "Domi"),
        ("domi", "Domi"),
        ("-DoMiNaToR-", "Domi"),
    ],
)
def test_the_in_game_spellings_resolve(spelling: str, canonical: str) -> None:
    """These are the spellings that actually appear in the corpus. A guest whose
    in-game name does not resolve gets none of the boost - `rating_for` would be
    asked about "[OoE]ExCaL^" and hand back the newcomer prior."""
    assert player_ids.resolve_player_name(spelling) == canonical


@pytest.mark.parametrize("name", GUESTS)
def test_a_guest_is_a_selectable_player(name: str) -> None:
    """`PlayerEnum` - the Balance Teams checkboxes - is generated from
    `PLAYER_NAMES`, so membership here *is* being on the page."""
    assert name in player_ids.PLAYER_NAMES
    assert name in player_ids.HUMAN_NAMES


# --- the asserted rating ---------------------------------------------------


@pytest.mark.parametrize("name", GUESTS)
def test_a_guest_rating_is_the_asserted_multiple_of_the_leader(
    computed, leader_ordinal, name: str
) -> None:
    multiplier = player_rating.GUEST_RATING_MULTIPLIERS[name]
    assert computed.rating_for(name).ordinal() == pytest.approx(
        multiplier * leader_ordinal
    )


def test_the_guests_outrank_everyone_in_the_stated_order(computed) -> None:
    best_real = computed.ratings[0].ordinal()
    excal = computed.rating_for("Excal").ordinal()
    domi = computed.rating_for("Domi").ordinal()
    assert excal > domi > best_real


def test_a_guest_who_has_never_played_still_has_a_rating(computed) -> None:
    """The point of the feature is next week's game night, before which one of
    them may have no games in the corpus at all. `rated_corpus` contains neither
    guest, so this is that case."""
    assert "Excal" not in {p.name for g in rated_corpus() for p in g.players}
    assert computed.rating_for("Excal").sigma == player_rating.GUEST_SIGMA


def test_a_guest_is_stated_confidently(computed) -> None:
    """`predict_win` divides the mu gap by the teams' pooled uncertainty, so a
    wide sigma would make the 2x guest read as a *smaller* edge than the 1.5x
    one. Both are floored at the same converged sigma every other rating gets."""
    assert {computed.rating_for(n).sigma for n in GUESTS} == {player_rating.MIN_SIGMA}


# --- the blast radius ------------------------------------------------------


def test_a_guest_does_not_reach_the_published_leaderboard(computed) -> None:
    """`.ratings` is the display list and the only place a rating *level* is
    meant to reach the wire (see CLAUDE.md). A guest is under MIN_GAMES, so the
    asserted number stays off it - which is what keeps a fabricated 2x rating
    from appearing on a page a normal visitor sees."""
    assert not {r.name for r in computed.ratings} & set(GUESTS)


def test_the_assertion_moves_nobody_else(monkeypatch) -> None:
    """The override is the last step of `compute_player_ratings`, after the
    passes. Rating the group's real games against an asserted 2x opponent would
    mean losing to Excal barely dents anyone and beating him is worth a fortune
    - a far bigger lie than the one being told."""
    games = rated_corpus()
    boosted = player_rating.compute_player_ratings(games)

    monkeypatch.setattr(player_rating, "GUEST_RATING_MULTIPLIERS", {})
    try:
        # `compute_player_ratings` is @derived: its key is the corpus, which has
        # not changed, so the patched run needs the entry gone both on the way
        # in and on the way out. Skipping the second clear leaves the *unboosted*
        # ratings cached under the real corpus key for every later test.
        player_rating.compute_player_ratings.cache_clear()
        plain = player_rating.compute_player_ratings(games)
    finally:
        player_rating.compute_player_ratings.cache_clear()

    for name in plain.all_ratings:
        assert boosted.rating_for(name).mu == pytest.approx(plain.rating_for(name).mu)
    assert boosted.newcomer_prior.mu == pytest.approx(plain.newcomer_prior.mu)


def test_a_guest_does_not_anchor_the_newcomer_prior(computed) -> None:
    """The prior is one beta *below the weakest established player*. A guest
    leaking into that set would drag every stranger's assumed rating with it."""
    assert computed.newcomer_prior.mu < computed.ratings[-1].mu


# --- what it is for --------------------------------------------------------


def test_the_balancer_hands_a_guest_the_weaker_partner() -> None:
    """The whole point of the feature. Given Excal, the group's best player and
    its two weakest, the closest game is the one that does *not* put Excal with
    the best player - which is the answer the balancer gave before the override
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
    """A sanity floor on the multiplier: taking Excal has to outweigh every
    swap available among the regulars, or the balancer would still be shuffling
    the group and ignoring him."""
    games = rated_corpus()
    computed = player_rating.compute_player_ratings(games)
    ordinals = [computed.rating_for(n).ordinal() for n in TEAM_ONE + TEAM_TWO]
    spread = max(ordinals) - min(ordinals)
    assert computed.rating_for("Excal").ordinal() - max(ordinals) > spread
