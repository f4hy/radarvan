"""Aggregate per-general statistics."""

# See radarvan/api_types/__init__.py for why this package is split by context.
# Needed so forward/self references resolve under Python < 3.14 (PEP 649 defers
# by default on 3.14+); required for the ml/ 3.13 training venv.
from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict
from .common import General, WinLoss


class GeneralStatPlayerWL(BaseModel):
    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    player_name: str = Field(alias="playerName")
    win_loss: WinLoss | None = Field(default=None, alias="winLoss")


class GeneralStat(BaseModel):
    general: General
    stats: list[GeneralStatPlayerWL]
    total: WinLoss
    # Precomputed nightly (see routes/superlatives._do_recompute) since it
    # requires scanning every competitive match's kill events - too slow to
    # derive live in this otherwise-cheap route. 0 until the first recompute.
    value_destroyed: int = 0
    value_lost: int = 0


class GeneralStats(BaseModel):
    general_stats: list[GeneralStat]
