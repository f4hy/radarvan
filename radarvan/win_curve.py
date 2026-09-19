"""The win-probability curve read as a story, from the eventual winner's side.

The curve is jumpy and snaps to ~100% on its last bucket, so each measure here
is windowed or banded rather than read point to point.
"""

from __future__ import annotations

from typing import NamedTuple

from .api_types import WinProbOverTime

# How long a stretch of the curve counts as one "swing".
SWING_WINDOW_MINUTES = 2.0

# Smaller rises than this are early-game noise (the model is still moving off
# the pre-game prior), not something that happened.
MIN_SWING = 0.25

# The first points are mostly the pre-game prior, before anything has
# happened, so an underdog climbing off a low start is not a comeback and
# crossing 50% there is not a lead changing hands.
SETTLING_MINUTES = 2.0

# A lead only changes hands once the curve has clearly left 50% on the other
# side, so jitter around even odds doesn't count as a lead change.
LEAD_BAND = 0.10

# The band of "either side could still win" for `contested_share`.
CONTESTED_LOW = 0.30
CONTESTED_HIGH = 0.70


class WinnerCurve(NamedTuple):
    """The curve re-expressed as the eventual winner's win probability."""

    minutes: list[float]
    probs: list[float]
    winners: list[str]
    losers: list[str]


class Swing(NamedTuple):
    """The winners' biggest rise inside one ``SWING_WINDOW_MINUTES`` window."""

    start_minute: float
    end_minute: float
    start_prob: float
    end_prob: float

    @property
    def rise(self) -> float:
        return self.end_prob - self.start_prob

    @property
    def flipped_lead(self) -> bool:
        """Started clearly behind and ended level or ahead."""
        return self.start_prob < 0.5 - LEAD_BAND and self.end_prob >= 0.5

    def contains(self, minute: float) -> bool:
        return self.start_minute < minute <= self.end_minute


def winner_curve(wpot: WinProbOverTime | None) -> WinnerCurve | None:
    if wpot is None or wpot.actual_winner is None or not wpot.points:
        return None
    winner_is_a = wpot.actual_winner == "team_a"
    return WinnerCurve(
        minutes=[p.at_minute for p in wpot.points],
        probs=[
            p.prob_team_a if winner_is_a else 1 - p.prob_team_a for p in wpot.points
        ],
        winners=wpot.team_a_players if winner_is_a else wpot.team_b_players,
        losers=wpot.team_b_players if winner_is_a else wpot.team_a_players,
    )


def biggest_swing(curve: WinnerCurve) -> Swing | None:
    """The winners' largest rise within a window, or None if none reached ``MIN_SWING``."""
    best: Swing | None = None
    for i, start in enumerate(curve.minutes):
        for j in range(i + 1, len(curve.minutes)):
            if curve.minutes[j] - start > SWING_WINDOW_MINUTES:
                break
            candidate = Swing(start, curve.minutes[j], curve.probs[i], curve.probs[j])
            if candidate.rise >= MIN_SWING and (
                best is None or candidate.rise > best.rise
            ):
                best = candidate
    return best


def _settled(curve: WinnerCurve) -> list[float]:
    return [
        prob
        for minute, prob in zip(curve.minutes, curve.probs, strict=True)
        if minute > SETTLING_MINUTES
    ]


def deepest_deficit(curve: WinnerCurve) -> float:
    """The winners' lowest win probability once settled; 0.5 if no point has."""
    return min(_settled(curve), default=0.5)


def lead_changes(curve: WinnerCurve) -> int:
    leader = 0
    changes = 0
    for prob in _settled(curve):
        if prob > 0.5 + LEAD_BAND:
            side = 1
        elif prob < 0.5 - LEAD_BAND:
            side = -1
        else:
            continue
        if leader and side != leader:
            changes += 1
        leader = side
    return changes


def contested_share(curve: WinnerCurve) -> float:
    inside = sum(CONTESTED_LOW <= prob <= CONTESTED_HIGH for prob in curve.probs)
    return inside / len(curve.probs)
