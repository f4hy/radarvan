"""Weighted-random map draw: eligibility, veto removal, vote weighting."""

import random
from collections import Counter

from radarvan.map_choice import choose_map


def test_vetoed_maps_are_excluded() -> None:
    tally = {
        "voted": (3, 0),
        "vetoed": (5, 1),  # has a veto -> out, despite more votes
        "novotes": (0, 0),  # no votes -> out
    }
    result = choose_map(2, tally, rng=random.Random(1))
    by_name = {c.map_name: c for c in result.candidates}
    assert by_name["voted"].eligible is True
    assert by_name["vetoed"].eligible is False
    assert by_name["novotes"].eligible is False
    # Only "voted" is eligible, so it must be chosen.
    assert result.chosen_map == "voted"


def test_no_eligible_maps_returns_none() -> None:
    result = choose_map(2, {"a": (0, 0), "b": (1, 2)}, rng=random.Random(1))
    assert result.chosen_map is None


def test_selection_is_weighted_by_votes() -> None:
    # "heavy" has 9x the votes of "light"; over many draws it dominates.
    tally = {"heavy": (9, 0), "light": (1, 0)}
    rng = random.Random(42)
    picks = Counter(choose_map(2, tally, rng=rng).chosen_map for _ in range(1000))
    assert picks["heavy"] > picks["light"]
    assert picks["heavy"] > 800  # ~900 expected


def test_candidates_sorted_by_votes_desc() -> None:
    tally = {"a": (1, 0), "b": (5, 0), "c": (3, 0)}
    result = choose_map(2, tally, rng=random.Random(1))
    assert [c.map_name for c in result.candidates] == ["b", "c", "a"]
