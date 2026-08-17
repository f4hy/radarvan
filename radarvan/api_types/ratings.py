"""Skill ratings, synergy, and rating-derived series."""

# See radarvan/api_types/__init__.py for why this package is split by context.
# Needed so forward/self references resolve under Python < 3.14 (PEP 649 defers
# by default on 3.14+); required for the ml/ 3.13 training venv.
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
    """Whether a pair of players over- or under-performs their combined ratings.

    ``synergy`` is the extra log-odds the pair's team gets purely because the two
    are paired, beyond what their individual ratings predict (positive = chemistry,
    negative = anti-synergy). ``win_prob_delta`` expresses the same effect as a
    win-probability shift at an even (50/50) matchup. See
    ``SYNERGY_METHODOLOGY.md``.
    """

    model_config = _FROM_ATTRIBUTES

    player_a: str
    player_b: str
    synergy: float
    win_prob_delta: float
    games_together: int
    wins_together: int
    expected_wins: float
    std_error: float
    z_score: float
    games_apart: int
    main_a: float
    main_b: float
    adjusted_expected_wins: float


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
