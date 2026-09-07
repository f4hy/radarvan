"""Wire types for the opening book: early build-order archetypes per general."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from .common import General


class Opening(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    buildings: list[str]
    game_count: int = Field(alias="gameCount")
    win_count: int = Field(alias="winCount")
    win_rate: float = Field(alias="winRate")


class GeneralOpeningBook(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    general: General
    total_games: int = Field(alias="totalGames")
    openings: list[Opening]
    # Games whose opening was too rare to name on its own (below min_games),
    # rolled up here rather than shown as dozens of one-off rows.
    other_game_count: int = Field(alias="otherGameCount")
    other_win_count: int = Field(alias="otherWinCount")


class OpeningBook(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    computed_at: date = Field(alias="computedAt")
    min_games: int = Field(alias="minGames")
    generals: list[GeneralOpeningBook]
