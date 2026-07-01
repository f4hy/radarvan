"""Tests for the fixed 12-entrant double-elimination bracket topology."""

import pytest

from radarvan import bracket


def _seed_names() -> dict[int, str]:
    return {i: f"P{i}" for i in range(1, 13)}


def test_bracket_topology_has_23_match_defs() -> None:
    # 22 always-played matches + GF-2, which only applies on a bracket reset.
    assert len(bracket.TOPOLOGY) == 23
    assert len({m.match_id for m in bracket.TOPOLOGY}) == 23


def test_pending_bracket_before_any_scores() -> None:
    result = bracket.resolve_bracket(_seed_names(), {})
    ready_ids = {m.match_id for m in result.matches if m.status == "ready"}
    # Only the 4 real winners-round-1 matches are immediately playable; seeds
    # 1-4 bye straight through, so WB2 stays pending until WB1 completes.
    assert ready_ids == {"WB1-1", "WB1-2", "WB1-3", "WB1-4"}
    assert sorted(result.bye_advances) == [
        (1, "P1"),
        (2, "P2"),
        (3, "P3"),
        (4, "P4"),
    ]
    assert result.champion is None
    assert result.needs_reset is False


def test_full_run_no_reset_completes_in_22_matches() -> None:
    seed_to_name = _seed_names()
    states: dict[str, bracket.MatchState] = {}
    result = bracket.resolve_bracket(seed_to_name, states)
    for _ in range(100):
        ready = [m for m in result.matches if m.status == "ready"]
        if not ready:
            break
        for m in ready:
            # "player_a" always wins, an arbitrary but deterministic strategy.
            states[m.match_id] = bracket.MatchState(best_of=3, score_a=2, score_b=0)
        result = bracket.resolve_bracket(seed_to_name, states)
    else:
        raise AssertionError("bracket did not converge")

    completed = [m for m in result.matches if m.status == "completed"]
    not_applicable = [m for m in result.matches if m.status == "not_applicable"]
    assert len(completed) == 22
    assert len(not_applicable) == 1  # GF-2 never needed
    assert result.needs_reset is False
    assert result.champion is not None
    assert result.runner_up is not None
    assert result.champion != result.runner_up

    gf1 = next(m for m in result.matches if m.match_id == "GF-1")
    assert result.champion == gf1.winner
    assert result.runner_up == gf1.loser


def test_full_run_with_bracket_reset_completes_in_23_matches() -> None:
    seed_to_name = _seed_names()
    states: dict[str, bracket.MatchState] = {}
    result = bracket.resolve_bracket(seed_to_name, states)
    for _ in range(100):
        ready = [m for m in result.matches if m.status == "ready"]
        if not ready:
            break
        for m in ready:
            # Force the losers-bracket entrant to win GF-1 so a reset is
            # needed; everywhere else "player_a" wins (arbitrary, deterministic).
            if m.match_id == "GF-1":
                score_a, score_b = 0, 2
            else:
                score_a, score_b = 2, 0
            states[m.match_id] = bracket.MatchState(
                best_of=3, score_a=score_a, score_b=score_b
            )
        result = bracket.resolve_bracket(seed_to_name, states)
    else:
        raise AssertionError("bracket did not converge")

    completed = [m for m in result.matches if m.status == "completed"]
    assert len(completed) == 23
    assert result.needs_reset is True

    gf1 = next(m for m in result.matches if m.match_id == "GF-1")
    gf2 = next(m for m in result.matches if m.match_id == "GF-2")
    assert gf2.status == "completed"
    assert result.champion == gf2.winner
    assert result.runner_up == gf2.loser
    # GF-2 is a rematch of the exact same two players as GF-1.
    assert gf2.player_a == gf1.player_a
    assert gf2.player_b == gf1.player_b
    # The losers-bracket entrant (player_b) won GF-1, forcing this reset.
    assert gf1.winner == gf1.player_b


def test_validate_score_accepts_valid_results() -> None:
    bracket.validate_score(3, 2, 0)
    bracket.validate_score(3, 2, 1)
    bracket.validate_score(5, 3, 2)
    bracket.validate_score(7, 4, 3)
    bracket.validate_score(9, 5, 4)


def test_validate_score_rejects_bad_best_of() -> None:
    with pytest.raises(ValueError):
        bracket.validate_score(4, 2, 1)


def test_validate_score_rejects_wrong_winning_margin() -> None:
    with pytest.raises(ValueError):
        bracket.validate_score(3, 3, 0)  # too many wins for best of 3
    with pytest.raises(ValueError):
        bracket.validate_score(3, 1, 0)  # not enough wins yet


def test_validate_score_rejects_both_reaching_threshold() -> None:
    with pytest.raises(ValueError):
        bracket.validate_score(3, 2, 2)
