"""Tests for the 9-16 entrant double-elimination bracket topology.

The bracket size is always fixed at 16 (0-7 byes for 16-9 entrants) — these
tests parametrize over the full supported range and assert the loss-
accounting invariant (every match produces exactly one loss; a double-elim
bracket for N entrants needs exactly 2*(N-1) losses to reach a champion, or
2*(N-1)+1 with a grand-final reset) holds for every one of them.
"""

import pytest

from radarvan import bracket

ALL_PLAYER_COUNTS = list(range(bracket.MIN_PLAYERS, bracket.MAX_PLAYERS + 1))


def _seed_names(num_players: int) -> dict[int, str]:
    return {i: f"P{i}" for i in range(1, num_players + 1)}


def _play_all(num_players: int, force_reset: bool = False) -> bracket.BracketResult:
    seed_to_name = _seed_names(num_players)
    states: dict[str, bracket.MatchState] = {}
    result = bracket.resolve_bracket(seed_to_name, states)
    for _ in range(200):
        ready = [m for m in result.matches if m.status == "ready"]
        if not ready:
            break
        for m in ready:
            # Force the losers-bracket entrant to win GF-1 (forcing a reset)
            # when requested; everywhere else "player_a" always wins — an
            # arbitrary but deterministic strategy.
            if force_reset and m.match_id == "GF-1":
                score_a, score_b = 0, 2
            else:
                score_a, score_b = 2, 0
            states[m.match_id] = bracket.MatchState(
                best_of=3, score_a=score_a, score_b=score_b
            )
        result = bracket.resolve_bracket(seed_to_name, states)
    else:
        raise AssertionError(f"bracket did not converge for N={num_players}")
    return result


@pytest.mark.parametrize("num_players", ALL_PLAYER_COUNTS)
def test_build_topology_match_counts(num_players: int) -> None:
    topology = bracket.build_topology(num_players)
    byes = bracket.MAX_PLAYERS - num_players
    # 2*(N-1) always-played matches + GF-2, which only applies on a reset.
    assert len(topology.matches) == 2 * (num_players - 1) + 1
    assert len({m.match_id for m in topology.matches}) == len(topology.matches)
    assert len(topology.bye_seeds) == byes


@pytest.mark.parametrize("num_players", ALL_PLAYER_COUNTS)
def test_full_run_no_reset(num_players: int) -> None:
    result = _play_all(num_players)
    completed = [m for m in result.matches if m.status == "completed"]
    not_applicable = [m for m in result.matches if m.status == "not_applicable"]
    assert len(completed) == 2 * (num_players - 1)
    assert len(not_applicable) == 1  # GF-2 never needed
    assert result.needs_reset is False
    assert result.champion is not None
    assert result.runner_up is not None
    assert result.champion != result.runner_up

    gf1 = next(m for m in result.matches if m.match_id == "GF-1")
    assert result.champion == gf1.winner
    assert result.runner_up == gf1.loser


@pytest.mark.parametrize("num_players", ALL_PLAYER_COUNTS)
def test_full_run_with_bracket_reset(num_players: int) -> None:
    result = _play_all(num_players, force_reset=True)
    completed = [m for m in result.matches if m.status == "completed"]
    assert len(completed) == 2 * (num_players - 1) + 1
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


def test_losers_round1_pairs_mirror_not_adjacent() -> None:
    """LB round 1 must pair the first WB1 dropper against the last (and so on
    inward), not adjacent droppers - otherwise two players who just met in
    the same WB1 "half" would immediately rematch in the losers bracket.
    Matches the pairing shape of standard double-elim bracket generators
    (e.g. for 16 players: LB1 pairs WB1 losers (1,8), (2,7), (3,6), (4,5))."""
    topology = bracket.build_topology(16)
    lb1 = sorted(
        (m for m in topology.matches if m.bracket == "L" and m.round_number == 1),
        key=lambda m: m.match_id,
    )
    pairs = [
        (m.slot_a.match_id, m.slot_b.match_id)  # type: ignore[union-attr]
        for m in lb1
    ]
    assert pairs == [
        ("WB1-1", "WB1-8"),
        ("WB1-2", "WB1-7"),
        ("WB1-3", "WB1-6"),
        ("WB1-4", "WB1-5"),
    ]


def _source_key(src: bracket.Source) -> tuple[str, str] | tuple[str, int]:
    if isinstance(src, bracket.Seed):
        return ("seed", src.seed)
    if isinstance(src, bracket.WinnerOf):
        return ("winner", src.match_id)
    return ("loser", src.match_id)


@pytest.mark.parametrize("num_players", ALL_PLAYER_COUNTS)
def test_no_immediate_rematch(num_players: int) -> None:
    """No match's two slots may both be reachable from the same earlier
    match one hop apart - i.e. a player who just won or lost match X must
    not be able to face the other player from X again in their very next
    match. This is a purely structural (topology-only) check: for slot P
    directly sourced from X (winner or loser of X) and slot Q sourced from
    some match Z, Q risks an immediate rematch with P if Z's own two slots
    include the complementary role of X (X's winner if P is X's loser, or
    vice versa) - meaning Z could literally be "X's other finisher vs.
    someone else", and if that someone else loses/wins Z, they land right
    back across from P. The Grand Final is exempt: the WB champion facing
    whoever climbs out of the entire losers bracket (even the person they
    already beat in the WB final) is the intended design, not a bug - it's
    exactly why the Grand Final Reset (GF-2) exists."""
    topology = bracket.build_topology(num_players)
    by_id = {m.match_id: m for m in topology.matches}

    for m in topology.matches:
        if m.bracket == "GF":
            continue
        for near, far in ((m.slot_a, m.slot_b), (m.slot_b, m.slot_a)):
            near_kind, near_key = _source_key(near)
            if near_kind not in ("winner", "loser"):
                continue
            x_match_id = near_key
            far_kind, far_key = _source_key(far)
            if far_kind not in ("winner", "loser"):
                continue
            assert far_key != x_match_id, (
                f"{m.match_id} pairs both slots directly off {x_match_id} "
                f"(n={num_players})"
            )
            z = by_id.get(far_key)
            if z is None or z.bracket == "GF":
                continue
            complement = "winner" if near_kind == "loser" else "loser"
            z_slot_keys = {_source_key(z.slot_a), _source_key(z.slot_b)}
            assert (complement, x_match_id) not in z_slot_keys, (
                f"{m.match_id} risks an immediate rematch: one slot is off "
                f"{x_match_id}, the other is off {z.match_id} which itself "
                f"consumes the {complement} of {x_match_id} (n={num_players})"
            )


@pytest.mark.parametrize(
    "num_players,expected_lb1_games",
    # Losers Round 1 pairs up every depth-1 dropper (see the module
    # docstring): the real WB1 losers, plus any WB Round 2 match that was
    # itself bye-vs-bye (both slots raw seeds, no WB1 dependency - equally
    # "immediately available" as WB1). A WB2 match against a WB1 winner is
    # depth 2 and doesn't arrive until Losers Round 2. Round 1's game count
    # is floor(depth-1 dropper count / 2) - one dropper carries through
    # unplayed if that count is odd.
    [(9, 2), (10, 2), (11, 2), (12, 2), (13, 2), (14, 3), (15, 3), (16, 4)],
)
def test_losers_round1_game_count(num_players: int, expected_lb1_games: int) -> None:
    topology = bracket.build_topology(num_players)
    lb1 = [m for m in topology.matches if m.bracket == "L" and m.round_number == 1]
    assert len(lb1) == expected_lb1_games


def test_losers_round1_pairs_wb1_against_bye_only_wb2() -> None:
    """With only 2 real WB1 matches (10 players, 6 byes), the two real WB1
    droppers must NOT be forced to play each other in Losers Round 1 just
    because they're the only two real droppers around. Nor should they wait
    for a WB2 match that depends on a WB1 winner (seed1 vs Winner(WB1-1),
    seed2 vs Winner(WB1-2)) - those can't even be played yet. Each WB1 loser
    should instead face the loser of a same-depth, bye-vs-bye WB2 match
    (seed4 v seed5, seed3 v seed6) - the shape confirmed against a real
    Challonge-generated 10-player bracket."""
    topology = bracket.build_topology(10)
    lb1 = {
        m.match_id: m
        for m in topology.matches
        if m.bracket == "L" and m.round_number == 1
    }
    assert len(lb1) == 2
    for m in lb1.values():
        sources = {m.slot_a.match_id, m.slot_b.match_id}  # type: ignore[union-attr]
        assert sources == {"WB1-1", "WB2-4"} or sources == {"WB1-2", "WB2-2"}, (
            f"{m.match_id} pairs {sources} - each WB1 loser must face a "
            "bye-vs-bye WB2 loser (WB2-2 or WB2-4), not the other WB1 "
            "loser or a WB1-dependent WB2 match (WB2-1, WB2-3)"
        )


def test_n12_matches_previously_hand_verified_shape() -> None:
    """Regression check: the old fixed-12 topology (byes=4) is a special
    case of the general algorithm and must produce the same shape."""
    topology = bracket.build_topology(12)
    assert sorted(topology.bye_seeds) == [1, 2, 3, 4]
    lb_matches = [m for m in topology.matches if m.bracket == "L"]
    assert len(lb_matches) == 10


def test_pending_bracket_before_any_scores() -> None:
    result = bracket.resolve_bracket(_seed_names(12), {})
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


def test_build_topology_rejects_out_of_range_player_counts() -> None:
    with pytest.raises(ValueError):
        bracket.build_topology(8)
    with pytest.raises(ValueError):
        bracket.build_topology(17)


def test_is_valid_match_id() -> None:
    assert bracket.is_valid_match_id("WB1-1", 12)
    assert bracket.is_valid_match_id("GF-2", 12)
    assert not bracket.is_valid_match_id("LB7-1", 12)  # N=12 only needs 6 LB rounds
    assert bracket.is_valid_match_id("WB1-4", 12)
    # N=9 has only one real WB1 match (the 8v9 pair) — no "WB1-2".
    assert bracket.is_valid_match_id("WB1-1", 9)
    assert not bracket.is_valid_match_id("WB1-2", 9)


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
