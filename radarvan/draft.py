"""Draft randomization - spatial clustering that assigns players to map starting
positions and randomizes generals; backs ``POST /api/draft/randomize``."""

import random
from datetime import UTC, datetime
from typing import NamedTuple

from .api_types import DraftAssignment, DraftPlayerRequest, MapPlayerStart


class ComputedDraft(NamedTuple):
    assignments: list[DraftAssignment]
    randomized_at: datetime


def _sq_dist(a: MapPlayerStart, b: MapPlayerStart) -> float:
    return (a.x - b.x) ** 2 + (a.y - b.y) ** 2


def compute_draft(
    players: list[DraftPlayerRequest],
    positions: list[MapPlayerStart],
) -> ComputedDraft:
    teams = sorted({p.team for p in players})
    team_players = {t: [p for p in players if p.team == t] for t in teams}
    for group in team_players.values():
        random.shuffle(group)

    remaining = list(positions)
    random.shuffle(remaining)

    team_assigned: dict[int, list[MapPlayerStart]] = {t: [] for t in teams}

    max_size = max(len(v) for v in team_players.values())
    for round_idx in range(max_size):
        for team_idx, t in enumerate(teams):
            if round_idx >= len(team_players[t]) or not remaining:
                continue

            if round_idx == 0 and team_idx == 0:
                # First player of first team: random position
                pos = remaining.pop(0)
            elif round_idx == 0:
                # First player of each subsequent team: farthest from all assigned so far
                all_assigned = [p for plist in team_assigned.values() for p in plist]
                best = max(
                    range(len(remaining)),
                    key=lambda i: min(_sq_dist(remaining[i], a) for a in all_assigned),
                )
                pos = remaining.pop(best)
            else:
                # Subsequent players: closest position to own team's centroid
                assigned = team_assigned[t]
                cx = sum(p.x for p in assigned) / len(assigned)
                cy = sum(p.y for p in assigned) / len(assigned)

                def _dist_to_centroid(i: int, cx: float = cx, cy: float = cy) -> float:
                    return (remaining[i].x - cx) ** 2 + (remaining[i].y - cy) ** 2

                best = min(range(len(remaining)), key=_dist_to_centroid)
                pos = remaining.pop(best)

            team_assigned[t].append(pos)

    # Each general appears twice in the pool; draw without replacement.
    # This halves duplicate probability compared to pure random while
    # still allowing up to 2 players to share any given general.
    general_pool = list(range(12)) * 2
    random.shuffle(general_pool)

    assignments = []
    for t in teams:
        for player, pos in zip(team_players[t], team_assigned[t], strict=True):
            assignments.append(
                DraftAssignment(
                    player_name=player.name,
                    team=player.team,
                    position_number=pos.player_number,
                    general=general_pool.pop(),
                )
            )

    skip = next((a for a in assignments if a.player_name == "Skip"), None)
    if skip is not None and skip.team != teams[0]:
        # Swap Skip's team with the first team, whichever it is - hardcoding
        # teams[0] <-> teams[1] KeyErrors on any player of a third team (and
        # doesn't move Skip at all when he's on one).
        team_swap = {teams[0]: skip.team, skip.team: teams[0]}
        assignments = [
            a.model_copy(update={"team": team_swap.get(a.team, a.team)})
            for a in assignments
        ]

    return ComputedDraft(assignments=assignments, randomized_at=datetime.now(UTC))
