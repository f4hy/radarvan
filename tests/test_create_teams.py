"""`create_teams` - team-split enumeration, balance scoring, and the fudge table.

`balance_teams` itself only had `tests/test_balance_teams_hold.py`, which stubs
the computation to test the route's six-hour hold. Nothing exercised the maths.

Two of these functions are pure and are tested directly. The two that need
ratings use `corpus.rated_corpus()`: the default 15-game corpus sits under
`player_rating.MIN_GAMES` (45), so every rating derived from it is filtered out
and an assertion about "the balanced split" would pass against an empty table.
"""

import pytest

from openskill.models import PlackettLuceRating

from radarvan import create_teams, player_rating

from corpus import rated_corpus

FOUR = frozenset({"Skip", "CoreDawg", "Syn", "Pancake"})


# --- partition_into_teams (pure) -------------------------------------------


def test_every_partition_is_generated_exactly_once() -> None:
    """4 players into pairs is 3 distinct splits, not 6 - {A,B} and {C,D} is one
    partition, and the recursion pins the first player to avoid the mirror."""
    parts = list(create_teams.partition_into_teams(["a", "b", "c", "d"], 2))
    assert len(parts) == 3
    normalized = {tuple(sorted(tuple(sorted(t)) for t in p)) for p in parts}
    assert len(normalized) == 3, f"duplicate partitions: {parts}"


def test_every_player_appears_once_per_partition() -> None:
    players = ["a", "b", "c", "d", "e", "f"]
    for part in create_teams.partition_into_teams(players, 3):
        flat = [p for team in part for p in team]
        assert sorted(flat) == sorted(players)
        assert len(part) == 2


def test_six_players_into_pairs() -> None:
    parts = list(create_teams.partition_into_teams(["a", "b", "c", "d", "e", "f"], 2))
    assert len(parts) == 15


def test_an_indivisible_roster_is_rejected() -> None:
    with pytest.raises(ValueError, match="Cannot divide 5 players into teams of 2"):
        list(create_teams.partition_into_teams(["a", "b", "c", "d", "e"], 2))


# --- the same-team fudge (pure) --------------------------------------------


def test_the_fudge_pulls_a_listed_pairing_toward_even() -> None:
    pair = next(iter(create_teams.SAME_TEAM_FUDGE))
    a, b = tuple(pair)
    adjusted = create_teams._apply_fudge(0.60, [a, b], ["Syn", "Pancake"])
    assert adjusted == pytest.approx(0.5 + 0.10 * create_teams.SAME_TEAM_FUDGE[pair])
    assert 0.5 < adjusted < 0.60, "the fudge should shrink the edge, not flip it"


def test_the_fudge_applies_to_whichever_side_holds_the_pair() -> None:
    pair = next(iter(create_teams.SAME_TEAM_FUDGE))
    a, b = tuple(pair)
    assert create_teams._apply_fudge(0.60, ["Syn", "Pancake"], [a, b]) == pytest.approx(
        create_teams._apply_fudge(0.60, [a, b], ["Syn", "Pancake"])
    )


def test_an_unlisted_pairing_is_untouched() -> None:
    assert create_teams._apply_fudge(0.60, ["Skip", "Syn"], ["CoreDawg", "Pancake"]) == 0.60


def test_a_split_pair_is_untouched() -> None:
    """The table is about being *teammates*; opponents get no adjustment."""
    pair = next(iter(create_teams.SAME_TEAM_FUDGE))
    a, b = tuple(pair)
    assert create_teams._apply_fudge(0.60, [a, "Syn"], [b, "Pancake"]) == 0.60


# --- rate_team_partition ----------------------------------------------------


def _rated(**mus: float) -> dict[str, PlackettLuceRating]:
    model = player_rating.get_model()
    return {
        name: model.rating(name=name, mu=mu, sigma=1.0) for name, mu in mus.items()
    }


def test_a_lopsided_split_scores_worse_than_an_even_one() -> None:
    """The score is a loss: squared distance from a coin flip, lower is better."""
    rated = _rated(strong1=40.0, strong2=40.0, weak1=10.0, weak2=10.0)
    even = create_teams.rate_team_partition(
        [["strong1", "weak1"], ["strong2", "weak2"]], rated
    )
    lopsided = create_teams.rate_team_partition(
        [["strong1", "strong2"], ["weak1", "weak2"]], rated
    )
    assert even < lopsided
    assert even == pytest.approx(0.0, abs=1e-9), "an identical split should be a coin flip"


def test_every_player_on_a_team_is_counted() -> None:
    """The bug this guards: dropping a player made a 2v2 read as a 1v2.

    A 25-mu newcomer beside a 25-mu regular is a dead-even 2v2. Skipping them -
    which is what reading the MIN_GAMES-gated table used to do - leaves one mu
    against two, and `predict_win` sums each side, so it scores that as a rout.
    The balancer then went looking for a strong partner to "fix" a team that was
    already balanced.
    """
    rated = _rated(known1=25.0, known2=25.0, known3=25.0, newcomer=25.0)
    even = create_teams.rate_team_partition(
        [["known1", "newcomer"], ["known2", "known3"]], rated
    )
    assert even == pytest.approx(0.0, abs=1e-9), (
        "the newcomer was not counted: this side was scored as a 1v2"
    )


def test_rate_roster_gives_an_unknown_name_the_newcomer_prior() -> None:
    """`rate_roster` is what makes a hole impossible - it rates the roster, not
    the players it happens to recognise, so a name nobody has seen still comes
    back with a rating (under its own name, not the prior's empty one)."""
    computed = player_rating.compute_player_ratings(rated_corpus())
    rated = create_teams.rate_roster(["Skip", "NotAPlayer"], computed)

    assert set(rated) == {"Skip", "NotAPlayer"}
    assert rated["NotAPlayer"].name == "NotAPlayer"
    assert rated["NotAPlayer"].mu == computed.newcomer_prior.mu


# --- the rating-backed entry points ----------------------------------------


@pytest.fixture(scope="module")
def rated_games():
    games = rated_corpus()
    assert player_rating.compute_player_ratings(games).ratings, (
        "fixture problem: the corpus is under MIN_GAMES, so every assertion "
        "below would be checking an empty ratings table"
    )
    return games


def test_balance_teams_only_reports_the_favoured_side(rated_games) -> None:
    scores = create_teams.balance_teams(rated_games, player_list=FOUR)
    assert scores, "no splits were scored at all"
    assert all(v >= 0.5 for v in scores.values()), (
        "only the favoured side of each matchup is stored, so every value is >= 0.5"
    )
    assert all(len(team) == 2 for team in scores)
    assert all(set(team) <= FOUR for team in scores)


def test_balance_teams_covers_every_distinct_split(rated_games) -> None:
    """Four players make three distinct 2v2 splits; each must be represented.

    Compared as sets: the stored tuples take their element order from iterating
    a frozenset, so `("Skip", "Syn")` and `("Syn", "Skip")` are both reachable
    for the same team (see the note in the module docstring).
    """
    scores = create_teams.balance_teams(rated_games, player_list=FOUR)
    splits = {frozenset(team) for team in scores}
    all_splits = {
        frozenset(t)
        for part in create_teams.partition_into_teams(sorted(FOUR), 2)
        for t in part
    }
    assert splits <= all_splits, (
        f"a stored team is not one side of a real split: {splits - all_splits}"
    )
    covered = {frozenset(FOUR) - s for s in splits} | splits
    assert covered == all_splits, "some split was not scored from either side"
    assert len(scores) == len(all_splits) // 2, (
        f"four players make 3 matchups; got {len(scores)} entries: {scores}"
    )


def test_balance_teams_returns_the_closest_matchup_first(rated_games) -> None:
    values = list(create_teams.balance_teams(rated_games, player_list=FOUR).values())
    assert values == sorted(values), "results should be sorted by win probability"


def test_balance_teams_resolves_aliases(rated_games) -> None:
    """`skp` is `Skip`, so the same rosters and the same probabilities come back.

    Compared as {frozenset(team): score} rather than directly: the stored tuple's
    element order comes from frozenset iteration, so it is not stable between two
    differently-spelled inputs even when the teams are identical.
    """
    def normalized(player_list):
        return {
            frozenset(team): round(score, 12)
            for team, score in create_teams.balance_teams(
                rated_games, player_list=player_list
            ).items()
        }

    assert normalized(frozenset({"skp", "CoreDawg", "Syn", "Pancake"})) == normalized(
        FOUR
    )


def test_create_balanced_teams_picks_the_evenest_split(rated_games) -> None:
    teams = create_teams.create_balanced_teams(rated_games, set(FOUR), team_size=2)
    assert sorted(p for t in teams for p in t) == sorted(FOUR)
    assert [len(t) for t in teams] == [2, 2]

    rated = create_teams.rate_roster(
        sorted(FOUR), player_rating.compute_player_ratings(rated_games)
    )
    best = create_teams.rate_team_partition(teams, rated)
    for candidate in create_teams.partition_into_teams(sorted(FOUR), 2):
        assert best <= create_teams.rate_team_partition(candidate, rated) + 1e-12, (
            f"{teams} was chosen over the more even {candidate}"
        )


def test_every_split_is_scored_even_with_strangers_on_the_roster(rated_games) -> None:
    """Two known players plus two strangers still makes three scored matchups.

    Strangers used to be dropped from their team, which both mis-scored the
    splits that kept them apart and left the all-stranger split unscorable. They
    now take the newcomer prior, so every split is a real 2v2.
    """
    roster = frozenset({"Skip", "CoreDawg", "NotAPlayer", "AlsoNotAPlayer"})
    scores = create_teams.balance_teams(rated_games, player_list=roster)
    assert len(scores) == 3, f"three 2v2 matchups expected, got {scores}"
    assert all(len(team) == 2 for team in scores)


def test_a_newcomer_is_not_a_missing_player(rated_games) -> None:
    """The reported bug: a sub-MIN_GAMES player was deleted from their team.

    `compute_player_ratings().ratings` is gated at MIN_GAMES, so reading it
    left the newcomer's side one body short and `predict_win` - which sums each
    side's mu - called the matchup a rout. Every split is now a plausible
    probability rather than a near-certainty.
    """
    roster = frozenset({"Skip", "CoreDawg", "Syn", "Pancake", "Neo", "AFreshFace"})
    scores = create_teams.balance_teams(rated_games, player_list=roster)
    assert scores, "no splits were scored at all"
    assert max(scores.values()) < 0.999, (
        f"a split was scored as a certainty, which is what a short-handed team "
        f"looks like to predict_win: {scores}"
    )


def test_team_member_order_is_deterministic(rated_games) -> None:
    """Element order used to come from iterating a frozenset, so it depended on
    PYTHONHASHSEED - the same roster rendered as "Skip,Syn" on one dyno and
    "Syn,Skip" after a restart, because the route joins these with a comma."""
    scores = create_teams.balance_teams(rated_games, player_list=FOUR)
    for team in scores:
        assert list(team) == sorted(team), f"{team} is not in a canonical order"


def test_each_matchup_is_reported_once(rated_games) -> None:
    """Both halves of a dead-even matchup used to be stored.

    `combinations` yields each even split from either side, and both branches
    were `>= 0.5`, so a 0.500/0.500 pairing landed twice - the UI listed the two
    halves of one matchup as if they were separate options.
    """
    scores = create_teams.balance_teams(rated_games, player_list=FOUR)
    for team in scores:
        complement = tuple(sorted(FOUR - set(team)))
        assert complement not in scores, (
            f"{team} and its complement {complement} are the same matchup, "
            f"but both were reported"
        )


def test_two_aliases_for_one_player_are_one_person(rated_games) -> None:
    """`{"skp", "Skip", ...}` is a three-player roster, not a four-player one."""
    doubled = create_teams.balance_teams(
        rated_games, player_list=frozenset({"skp", "Skip", "Syn", "Pancake"})
    )
    single = create_teams.balance_teams(
        rated_games, player_list=frozenset({"Skip", "Syn", "Pancake"})
    )
    assert doubled == single
    for team in doubled:
        assert len(set(team)) == len(team), f"{team} lists the same player twice"
