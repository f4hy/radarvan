"""Aggregate per-general statistics."""

from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict
from .common import General, WinLoss


class GeneralStatPlayerWL(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    player_name: str = Field(alias="playerName")
    win_loss: WinLoss | None = Field(default=None, alias="winLoss")


class GeneralStat(BaseModel):
    general: General
    stats: list[GeneralStatPlayerWL]
    total: WinLoss
    # Precomputed nightly (see computed_stats.recompute) since it
    # requires scanning every competitive match's kill events - too slow to
    # derive live in this otherwise-cheap route. 0 until the first recompute.
    value_destroyed: int = 0
    value_lost: int = 0


class GeneralStats(BaseModel):
    general_stats: list[GeneralStat]


class GeneralMatchupCell(BaseModel):
    """Actual 1v1 record between two generals - `a_wins`/`b_wins` are wins for
    whichever human piloted `general_a`/`general_b` respectively in those
    games, so `a_wins + b_wins` is the total games seen for this pair."""

    model_config = ConfigDict(populate_by_name=True)

    general_a: General = Field(alias="generalA")
    general_b: General = Field(alias="generalB")
    a_wins: int = Field(alias="aWins")
    b_wins: int = Field(alias="bWins")


class GeneralMatchups(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    cells: list[GeneralMatchupCell]
