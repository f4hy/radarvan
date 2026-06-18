"""Weighted-random map selection for the 'choose map' draw.

The pick is authoritative on the backend (not the animated frontend). A map's
score is ``votes - VETO_VOTE_PENALTY * vetoes``, minus RECENT_PLAY_PENALTY if it
was played within the recency window (to discourage repeats). A map stays in the
draw only with a net-positive score (score <= 0 is a hard veto), and the draw is
weighted by that net score.
"""

import random

from .api_types import ChooseMapCandidate, ChooseMapResult

# Each veto subtracts this many votes from a map's score.
VETO_VOTE_PENALTY = 3
# A map played within the recency window is docked this many votes.
RECENT_PLAY_PENALTY = 8


def choose_map(
    player_count: int,
    tally: dict[str, tuple[int, int]],
    *,
    recent_maps: set[str] | None = None,
    rng: random.Random | None = None,
) -> ChooseMapResult:
    """Pick a map weighted by net score (votes - 3*vetoes); net <= 0 is vetoed.

    `tally` is {map_name: (votes, vetoes)} (only maps with votes/vetoes).
    `recent_maps` are map names played within the recency window; each is docked
    RECENT_PLAY_PENALTY votes so freshly-played maps are unlikely to repeat.
    """
    chooser = rng or random.Random()  # noqa: S311 - game draw, not crypto
    recent = recent_maps or set()

    candidates: list[ChooseMapCandidate] = []
    for map_name, (votes, vetoes) in tally.items():
        recently_played = map_name in recent
        net = votes - VETO_VOTE_PENALTY * vetoes
        if recently_played:
            net -= RECENT_PLAY_PENALTY
        eligible = net > 0
        candidates.append(
            ChooseMapCandidate(
                map_name=map_name,
                votes=votes,
                vetoes=vetoes,
                weight=net if eligible else 0,
                eligible=eligible,
                recently_played=recently_played,
            )
        )
    candidates.sort(key=lambda c: (-c.votes, c.map_name))

    pool = [c for c in candidates if c.eligible]
    chosen = (
        chooser.choices([c.map_name for c in pool], weights=[c.weight for c in pool])[0]
        if pool
        else None
    )
    return ChooseMapResult(
        player_count=player_count, chosen_map=chosen, candidates=candidates
    )
