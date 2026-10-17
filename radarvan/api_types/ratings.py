"""Skill ratings, synergy, and rating-derived series."""

from __future__ import annotations

from pydantic import BaseModel, Field
from datetime import date
from .common import _FROM_ATTRIBUTES


class PlayerRatings(BaseModel):
    model_config = _FROM_ATTRIBUTES

    name: str
    ordinal: float
    mu: float
    sigma: float
    game_count: int
    atdate: date | None = None
    recent_deltas: dict[int, float] = Field(default_factory=dict)
    high_ordinal: float | None = None
    low_ordinal: float | None = None


class ShortPlayerRating(BaseModel):
    model_config = _FROM_ATTRIBUTES

    mu: float
    sigma: float
    atdate: date | None = None


class PlayerRatingData(BaseModel):
    model_config = _FROM_ATTRIBUTES

    player_rating: list[PlayerRatings]
    player_rating_overtime: dict[str, list[ShortPlayerRating]] = {}
    player_form: dict[str, list[bool]] = {}


class PlayerSkill(BaseModel):
    model_config = _FROM_ATTRIBUTES

    name: str
    skill: float
    game_count: int


class PlayerSynergy(BaseModel):
    """A pair's wins together minus the rating model's pregame expectation.

    ``solo_a``/``solo_b`` are each player's per-game excess without the other.
    See ``SYNERGY_METHODOLOGY.md``.
    """

    model_config = _FROM_ATTRIBUTES

    player_a: str
    player_b: str
    games_together: int
    wins_together: int
    expected_wins: float
    excess_wins: float
    win_rate_delta: float
    z_score: float
    solo_a: float | None
    solo_b: float | None


class PlayerRatingDailyChange(BaseModel):
    model_config = _FROM_ATTRIBUTES

    name: str
    delta: float


class RatingUpset(BaseModel):
    """A game where the rating model's favored team lost.

    Win probabilities are the model's pre-game prediction for each team using the
    converged ratings; ``surprise`` is the favorite's edge over the actual winner.
    """

    model_config = _FROM_ATTRIBUTES

    match_id: int
    atdate: date
    favored_team: int
    favored_players: list[str]
    favored_win_prob: float
    winning_team: int
    winner_players: list[str]
    winner_win_prob: float
    surprise: float
