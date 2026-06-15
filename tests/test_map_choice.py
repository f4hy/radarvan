"""Weighted-random map draw: eligibility, veto removal, vote weighting."""

import random
from collections import Counter

from radarvan.map_choice import choose_map


def test_veto_is_minus_three_votes_with_hard_veto_at_zero() -> None:
    tally = {
        "survives": (5, 1),  # net 5 - 3 = 2 > 0 -> stays, despite a veto
        "boundary": (3, 1),  # net 0 -> hard vetoed
        "buried": (2, 1),  # net -1 -> hard vetoed
        "novotes": (0, 0),  # net 0 -> out
    }
    result = choose_map(2, tally, rng=random.Random(1))
    by_name = {c.map_name: c for c in result.candidates}
    assert by_name["survives"].eligible is True
    assert by_name["survives"].weight == 2  # weighted by net score
    assert by_name["boundary"].eligible is False
    assert by_name["buried"].eligible is False
    assert by_name["novotes"].eligible is False
    # Only "survives" is net-positive, so it must be chosen.
    assert result.chosen_map == "survives"


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
