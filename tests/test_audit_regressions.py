"""Regression tests for small correctness fixes across stats modules."""

from datetime import date

from radarvan.head_to_head import compute_head_to_head
from radarvan.superlatives import superlative_data_from_details
from radarvan.tournament import faction_stats

from corpus import TEAM_ONE, details, match, win_prob_over_time


def test_faction_stats_least_played_can_be_an_unplayed_general() -> None:
    stats = {
        s.stat_name: s
        for s in faction_stats([match(1, day=5), match(2, day=6)], date(2026, 1, 7))
    }
    assert stats["Least played general"].value == 0
    assert stats["General with fewest wins"].value == 0


def test_head_to_head_with_oneself_is_empty() -> None:
    player = TEAM_ONE[0]
    result = compute_head_to_head([match(1, day=5)], player, player)
    assert result.teammate_games == 0
    assert result.games == []


def test_comeback_ignores_the_pregame_prior() -> None:
    probs = [0.05, 0.3, 0.6, 0.8, 0.9, 0.95, 1.0]
    data = superlative_data_from_details(
        details(1, win_prob_over_time=win_prob_over_time(probs))
    )
    assert data.winner_min_win_prob is not None
    assert data.winner_min_win_prob > 0.5
