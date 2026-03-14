import math
import random
from datetime import datetime, UTC

from .api_types import DraftAssignment, DraftPlayerRequest, MapPlayerStart


def compute_draft(
    players: list[DraftPlayerRequest],
    positions: list[MapPlayerStart],
) -> tuple[list[DraftAssignment], datetime]:
    shuffled = list(positions)
    random.shuffle(shuffled)
    teams = sorted({p.team for p in players})
    team_players = {t: [p for p in players if p.team == t] for t in teams}

    remaining = list(shuffled)
    cluster_map: dict[int, list[MapPlayerStart]] = {}
    for t in teams:
        size = len(team_players[t])
        cluster = [remaining.pop(0)]
        while len(cluster) < size and remaining:
            cx = sum(p.x for p in cluster) / len(cluster)
            cy = sum(p.y for p in cluster) / len(cluster)
            best = min(
                range(len(remaining)),
                key=lambda i: math.sqrt(
                    (remaining[i].x - cx) ** 2 + (remaining[i].y - cy) ** 2
                ),
            )
            cluster.append(remaining.pop(best))
        random.shuffle(cluster)
        cluster_map[t] = cluster

    assignments = []
    for t in teams:
        for player, pos in zip(team_players[t], cluster_map[t]):
            assignments.append(
                DraftAssignment(
                    player_name=player.name,
                    team=player.team,
                    position_number=pos.player_number,
                    general=random.randint(0, 11),  # noqa: S311
                )
            )
    return assignments, datetime.now(UTC)
