"""Draft spatial-clustering assignment: invariants and determinism."""

import random

from radarvan.api_types import DraftPlayerRequest, MapPlayerStart
from radarvan.draft import ComputedDraft, compute_draft


def _positions(n: int) -> list[MapPlayerStart]:
    """n start positions arranged on a square so distances are meaningful."""
    coords = [(0.0, 0.0), (100.0, 0.0), (0.0, 100.0), (100.0, 100.0), (50.0, 50.0)]
    return [
        MapPlayerStart(player_number=i + 1, x=coords[i][0], y=coords[i][1])
        for i in range(n)
    ]


def _players(team_sizes: dict[int, int]) -> list[DraftPlayerRequest]:
    players = []
    for team, size in team_sizes.items():
        for j in range(size):
            players.append(DraftPlayerRequest(name=f"P{team}_{j}", team=team))
    return players


def test_every_player_gets_exactly_one_unique_position() -> None:
    random.seed(0)
    players = _players({1: 2, 2: 2})
    result = compute_draft(players, _positions(4))

    assert isinstance(result, ComputedDraft)
    assert len(result.assignments) == len(players)

    # Each input player appears exactly once.
    assert {a.player_name for a in result.assignments} == {p.name for p in players}

    # Positions are not double-assigned and come from the allowed pool.
    positions = [a.position_number for a in result.assignments]
    assert len(positions) == len(set(positions))
    assert set(positions) <= {1, 2, 3, 4}


def test_generals_in_allowed_range_and_not_overdrawn() -> None:
    random.seed(1)
    players = _players({1: 2, 2: 2})
    result = compute_draft(players, _positions(4))

    generals = [a.general for a in result.assignments]
    assert all(0 <= g < 12 for g in generals)
    # The pool is range(12) * 2 drawn without replacement, so no general can
    # be assigned more than twice.
    counts: dict[int, int] = {}
    for g in generals:
        counts[g] = counts.get(g, 0) + 1
    assert all(c <= 2 for c in counts.values())


def test_teams_preserved_when_no_skip() -> None:
    random.seed(2)
    players = _players({1: 2, 2: 2})
    result = compute_draft(players, _positions(4))

    team_by_name = {a.player_name: a.team for a in result.assignments}
    for p in players:
        assert team_by_name[p.name] == p.team


def test_deterministic_for_fixed_seed() -> None:
    players = _players({1: 2, 2: 2})
    positions = _positions(4)

    random.seed(42)
    first = compute_draft(players, positions)
    random.seed(42)
    second = compute_draft(players, positions)

    # randomized_at is wall-clock, so compare only the deterministic part.
    assert first.assignments == second.assignments


def test_uneven_teams_no_double_assigned_positions() -> None:
    random.seed(3)
    players = _players({1: 1, 2: 2})  # 3 players
    result = compute_draft(players, _positions(5))  # more positions than players

    assert len(result.assignments) == 3
    positions = [a.position_number for a in result.assignments]
    assert len(positions) == len(set(positions))
    assert set(positions) <= {1, 2, 3, 4, 5}


def test_teammates_cluster_near_each_other() -> None:
    # With two clearly separated team clusters available, teammates should be
    # placed adjacent (the centroid heuristic) rather than split across the map.
    random.seed(7)
    players = _players({1: 2, 2: 2})
    # Two corners close together (top) and two close together (bottom).
    positions = [
        MapPlayerStart(player_number=1, x=0.0, y=0.0),
        MapPlayerStart(player_number=2, x=10.0, y=0.0),
        MapPlayerStart(player_number=3, x=0.0, y=100.0),
        MapPlayerStart(player_number=4, x=10.0, y=100.0),
    ]
    result = compute_draft(players, positions)

    pos_by_team: dict[int, set[int]] = {}
    for a in result.assignments:
        pos_by_team.setdefault(a.team, set()).add(a.position_number)

    # Each team's two positions must be one of the two adjacent pairs.
    near_pairs = [{1, 2}, {3, 4}]
    for team_positions in pos_by_team.values():
        assert team_positions in near_pairs
