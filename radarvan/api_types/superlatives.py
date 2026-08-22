"""Per-game superlative awards derived from match details."""

# See radarvan/api_types/__init__.py for why this package is split by context.
# Needed so forward/self references resolve under Python < 3.14 (PEP 649 defers
# by default on 3.14+); required for the ml/ 3.13 training venv.
from __future__ import annotations

from pydantic import BaseModel, Field
from .common import Minute
from .details import APM, FirstBlood


class SuperlativePlayerSummary(BaseModel):
    name: str
    color: str
    won: bool
    money_spent: int
    units_created_count: int
    buildings_built_count: int
    # Sum of build cost of everything this player destroyed/lost (units +
    # buildings) in the match - the value-destroyed proxy since replays don't
    # carry raw HP damage. See match_details.py's ud_by_player/bd_by_player.
    value_destroyed: int = 0
    value_lost: int = 0


class SuperweaponLaunch(BaseModel):
    """A player's first base-superweapon launch in one match."""

    weapon: str
    at_minute: Minute


class SuperlativeData(BaseModel):
    match_id: int
    first_blood: FirstBlood | None = None
    building_first_blood: FirstBlood | None = None
    apms: list[APM]
    player_summary: list[SuperlativePlayerSummary]
    upgrade_counts: dict[str, int]
    total_units_killed: int
    total_buildings_killed: int
    total_xp: int
    match_money_spent: int
    player_money_collected: dict[str, int]
    player_xp_final: dict[str, int] = Field(default_factory=dict)
    time_to_rank_5: dict[str, Minute] = Field(default_factory=dict)
    time_to_search_destroy: dict[str, Minute] = Field(default_factory=dict)
    time_to_hunted: dict[str, Minute] = Field(default_factory=dict)
    # Base-superweapon launches per player (the three big base-bound powers
    # only - the timeline also tags EMP/anthrax/gunship "superweapon_activated",
    # and those are generals-panel powers, not superweapons).
    superweapon_launches: dict[str, int] = Field(default_factory=dict)
    # Each player's first base-superweapon launch in the match.
    first_superweapon: dict[str, SuperweaponLaunch] = Field(default_factory=dict)
    # Tech-building captures (oil derricks, hospitals, artillery platforms, …)
    # per player.
    tech_captures: dict[str, int] = Field(default_factory=dict)
