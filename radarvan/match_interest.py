"""A hand-weighted score for how worth retelling a match is, with its reasons.

Not learned - there is no label for "interesting". Needs the win-probability
curve, so a match without one scores None rather than zero.
"""

from __future__ import annotations

from typing import NamedTuple

from . import win_curve
from .api_types import MatchDetails, MatchInfo
from .match_narrative import is_base_superweapon

WEIGHT_LEAD_CHANGES = 0.25
WEIGHT_COMEBACK = 0.25
WEIGHT_CONTESTED = 0.20
WEIGHT_SWING = 0.15
WEIGHT_SPECTACLE = 0.15

# Lead changes / comeback depth / contested time at which the signal saturates.
FULL_LEAD_CHANGES = 3
FULL_COMEBACK_DEPTH = 0.4
FULL_CONTESTED_SHARE = 0.5
FULL_SWING_EXTRA = 0.5

# A short game is a stomp or a quit, however dramatic its curve; a game this
# long has had room for a story.
FULL_LENGTH_MINUTES = 15.0
MIN_LENGTH_FACTOR = 0.25

# Where the score becomes worth acting on: the free match-of-the-night card,
# and the billed LLM blurb.
MIN_MATCH_OF_THE_NIGHT_SCORE = 0.4
MIN_INTEREST_FOR_BLURB = 0.5

# A signal must be at least this strong to be quoted as a reason.
REASON_MIN_SIGNAL = 0.5
MAX_REASONS = 3


class Interest(NamedTuple):
    score: float
    reasons: list[str]


class ScoredMatch(NamedTuple):
    match: MatchInfo
    details: MatchDetails
    curve: win_curve.WinnerCurve
    interest: Interest


class _Signal(NamedTuple):
    weight: float
    strength: float
    reason: str


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def match_interest(match: MatchInfo, details: MatchDetails) -> Interest | None:
    curve = win_curve.winner_curve(details.win_prob_over_time)
    return None if curve is None else _score(match, details, curve)


def _score(
    match: MatchInfo, details: MatchDetails, curve: win_curve.WinnerCurve
) -> Interest:
    changes = win_curve.lead_changes(curve)
    deepest = win_curve.deepest_deficit(curve)
    swing = win_curve.biggest_swing(curve)
    swing_rise = swing.rise if swing is not None else 0.0
    launches = sum(
        is_base_superweapon(event.event_name)
        for event in details.timeline_events
        if event.event_type == "superweapon_activated"
    )
    hunted = len(details.time_to_hunted)

    signals = [
        _Signal(
            WEIGHT_LEAD_CHANGES,
            _clamp(changes / FULL_LEAD_CHANGES),
            f"the lead changed hands {changes} times",
        ),
        _Signal(
            WEIGHT_COMEBACK,
            _clamp((0.5 - deepest) / FULL_COMEBACK_DEPTH),
            f"they were down to {deepest * 100:.0f}% to win before taking it",
        ),
        _Signal(
            WEIGHT_CONTESTED,
            _clamp(win_curve.contested_share(curve) / FULL_CONTESTED_SHARE),
            "it stayed close for most of the game",
        ),
        _Signal(
            WEIGHT_SWING,
            _clamp((swing_rise - win_curve.MIN_SWING) / FULL_SWING_EXTRA),
            f"a swing of {swing_rise * 100:.0f} points in "
            f"{win_curve.SWING_WINDOW_MINUTES:.0f} minutes",
        ),
        _Signal(
            WEIGHT_SPECTACLE,
            _clamp(0.5 * launches + 0.25 * hunted),
            _spectacle_reason(launches, hunted),
        ),
    ]
    length_factor = max(
        MIN_LENGTH_FACTOR, _clamp(match.duration_minutes / FULL_LENGTH_MINUTES)
    )
    score = length_factor * sum(s.weight * s.strength for s in signals)
    quoted = sorted(
        (s for s in signals if s.strength >= REASON_MIN_SIGNAL),
        key=lambda s: s.weight * s.strength,
        reverse=True,
    )
    return Interest(score=score, reasons=[s.reason for s in quoted[:MAX_REASONS]])


def rank(
    matches: list[MatchInfo], details_by_id: dict[int, MatchDetails]
) -> list[ScoredMatch]:
    """The matches that can be scored, best first; ties keep their input order."""
    scored = []
    for match in matches:
        details = details_by_id.get(match.id)
        curve = win_curve.winner_curve(details.win_prob_over_time) if details else None
        if details is not None and curve is not None:
            scored.append(
                ScoredMatch(match, details, curve, _score(match, details, curve))
            )
    return sorted(scored, key=lambda s: s.interest.score, reverse=True)


def _spectacle_reason(launches: int, hunted: int) -> str:
    parts = []
    if launches:
        parts.append(f"{launches} superweapon launch{'es' if launches > 1 else ''}")
    if hunted:
        parts.append(f"{hunted} player{'s' if hunted > 1 else ''} went hunted")
    return " and ".join(parts)
