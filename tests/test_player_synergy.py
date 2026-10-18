import pytest

from corpus import match, observer
from radarvan import player_synergy as pairs
from radarvan import player_rating
from radarvan.api_types import Team
from radarvan.api_types.ratings import PlayerSynergy


def test_residuals_use_pregame_ratings_and_give_both_sides_credit():
    game = match(91001, day=1, winner=Team.TWO)
    model = player_rating.get_model()
    teams = player_rating.build_teams(game)
    assert teams is not None
    expected = player_rating.displayed_win_probs(
        [
            [player_rating.initialize_player(n, model).to_rating(model) for n in team]
            for team in teams.teams.values()
        ]
    )
    rows = pairs.compute_player_synergy([game], min_games_together=1)
    assert len(rows) == 2
    loser = next(p for p in rows if p.wins_together == 0)
    winner = next(p for p in rows if p.wins_together == 1)
    assert loser.excess_wins == pytest.approx(-expected[0])
    assert winner.excess_wins == pytest.approx(1 - expected[1])
    assert loser.excess_wins + winner.excess_wins == pytest.approx(0)
    assert PlayerSynergy.model_validate(winner).win_rate_delta == winner.excess_wins


def test_future_results_do_not_change_earlier_expectations():
    first = match(91002, day=1)
    later = match(91003, day=2, winner=Team.TWO)
    original = pairs.pregame_expectations([first])[0]
    assert pairs.pregame_expectations([later, first])[0] == original
    assert (
        pairs.pregame_expectations([first, later])[1].probabilities
        != original.probabilities
    )


def test_every_pair_on_a_team_receives_the_full_bump():
    game = match(
        91004,
        day=1,
        team_one=("Skip", "CoreDawg", "Neo"),
        team_two=("Syn", "Pancake", "Modus"),
    )
    result = pairs.compute_player_synergy([game], min_games_together=1)
    assert len(result) == 6
    winners = [p for p in result if p.wins_together == 1]
    assert len(winners) == 3
    assert len({p.excess_wins for p in winners}) == 1
    assert all(p.player_a < p.player_b for p in result)


def test_format_filter_preserves_full_rating_history_and_matches_main_pass():
    first = match(
        91005,
        day=1,
        team_one=("Skip", "CoreDawg", "Neo"),
        team_two=("Syn", "Pancake", "Modus"),
    )
    second = match(91006, day=2)
    ratings = player_rating.compute_player_ratings([first])
    model = player_rating.get_model()
    teams = player_rating.build_teams(second)
    assert teams is not None
    expected = player_rating.displayed_win_probs(
        [
            [ratings.rating_for(n).to_rating(model) for n in t]
            for t in teams.teams.values()
        ]
    )[0]
    result = pairs.compute_player_synergy(
        [second, first], min_games_together=1, game_format="2v2"
    )
    winner = next(p for p in result if p.wins_together == 1)
    assert winner.expected_wins == pytest.approx(expected)
    assert winner.games_together == 1
    assert pairs.compute_player_synergy([second, first], min_games_together=3) == []
    assert player_rating.compute_player_ratings([first]) == ratings


def test_invalid_games_and_observers_do_not_change_results():
    game = match(91007, day=1)
    invalid = match(91008, day=2, incomplete="disconnect")
    original = pairs.compute_player_synergy([game], min_games_together=1)
    assert (
        pairs.compute_player_synergy([game, invalid], min_games_together=1) == original
    )
    observed = game.model_copy(update={"players": [*game.players, observer()]})
    assert pairs.pregame_expectations.__wrapped__(
        [observed]
    ) == pairs.pregame_expectations([game])


def test_guest_games_move_ratings_but_do_not_receive_pair_scores():
    guest = match(91009, day=1, team_one=("Excal", "Skip"))
    game = match(91010, day=2)
    rows = pairs.pregame_expectations([guest, game])
    assert [r.match_id for r in rows] == [game.id]
    assert rows[0].probabilities != pairs.pregame_expectations([game])[0].probabilities
    assert pairs.compute_player_synergy([guest], min_games_together=1) == []


def test_z_score_uses_model_variance_and_orders_results():
    game = match(91011, day=1)
    rows = pairs.compute_player_synergy([game], min_games_together=1)
    for row in rows:
        p = row.expected_wins
        assert row.variance == pytest.approx(p * (1 - p))
        assert row.z_score == pytest.approx(row.excess_wins / (p * (1 - p)) ** 0.5)
    assert [r.z_score for r in rows] == sorted((r.z_score for r in rows), reverse=True)


def test_solo_baseline_excludes_games_with_the_partner():
    together = [match(91100 + i, day=i + 1) for i in range(3)]
    apart = [match(91200 + i, day=10 + i, team_one=("Skip", "Neo")) for i in range(6)]
    games = together + apart
    pair = next(
        r
        for r in pairs.compute_player_synergy(games, min_games_together=3)
        if (r.player_a, r.player_b) == ("CoreDawg", "Skip")
    )
    skip_without_coredawg = [
        outcome - p
        for row in pairs.pregame_expectations(games)
        for team, p, outcome in zip(
            row.teams, row.probabilities, row.outcomes, strict=True
        )
        if "Skip" in team and "CoreDawg" not in team
    ]
    assert len(skip_without_coredawg) == 6
    assert pair.solo_b == pytest.approx(sum(skip_without_coredawg) / 6)
    assert pair.solo_a is None  # CoreDawg never played without Skip
