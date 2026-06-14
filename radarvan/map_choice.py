"""Weighted-random map selection for the 'choose map' draw.

The pick is authoritative on the backend (not the animated frontend). A map is
eligible only if it has at least one vote and no vetoes; among eligible maps the
draw is weighted by vote count.
"""

import random

from .api_types import ChooseMapCandidate, ChooseMapResult


def choose_map(
    player_count: int,
    tally: dict[str, tuple[int, int]],
    *,
    rng: random.Random | None = None,
) -> ChooseMapResult:
    """Pick a map weighted by votes; any veto removes a map from the pool.

    `tally` is {map_name: (votes, vetoes)} (only maps with votes/vetoes).
    """
    chooser = rng or random.Random()  # noqa: S311 - game draw, not crypto

    candidates: list[ChooseMapCandidate] = []
    for map_name, (votes, vetoes) in tally.items():
        eligible = votes > 0 and vetoes == 0
        candidates.append(
            ChooseMapCandidate(
                map_name=map_name,
                votes=votes,
                vetoes=vetoes,
                weight=votes if eligible else 0,
                eligible=eligible,
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
