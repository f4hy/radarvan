"""Enums, scalar aliases, and the primitives every other wire module builds on."""

# See radarvan/api_types/__init__.py for why this package is split by context.
# Needed so forward/self references resolve under Python < 3.14 (PEP 649 defers
# by default on 3.14+); required for the ml/ 3.13 training venv.
from __future__ import annotations

from pydantic import (
    AfterValidator,
    BaseModel,
    Field,
    ConfigDict,
    PlainSerializer,
)
from enum import IntEnum
from typing import Annotated
from ..player_ids import resolve_player_name


_FROM_ATTRIBUTES: ConfigDict = ConfigDict(from_attributes=True)
# Classes with field aliases must use an inline ConfigDict so the pydantic mypy plugin
# can statically resolve populate_by_name=True.


def _resolve_player_name(name: str) -> str:
    # Single-arg wrapper so pydantic's AfterValidator doesn't try to pass its
    # second positional (ValidationInfo) as resolve_player_name's `color`.
    return resolve_player_name(name)


# Type for any request field carrying a player name: alias→canonical resolution
# happens automatically at request validation, so endpoints can't forget it.
# Wire/OpenAPI type stays a plain string. See CLAUDE.md (player name resolution).
PlayerName = Annotated[str, AfterValidator(_resolve_player_name)]


# Match-clock position in minutes: chart precision only needs ~0.2s resolution,
# but the raw values carry full float noise (e.g. 1.2437749753490064) that
# balloons MatchDetails' wire size for no visual benefit. Rounding here (rather
# than at each extractor) covers every current and future minute-valued field,
# including as dict keys - pydantic-core serializes a dict key through its
# annotated type's serializer same as any value. Validation is untouched
# (PlainSerializer only affects output), so round-tripping cached JSON back
# through model_validate still works.
Minute = Annotated[
    float,
    PlainSerializer(lambda v: round(v, 3), return_type=float, when_used="json"),
]


# Per-minute action-rate value (APM). One decimal is well past the precision
# the source data supports and plenty for the chart.
Rate = Annotated[
    float,
    PlainSerializer(lambda v: round(v, 1), return_type=float, when_used="json"),
]


# A rate whose interesting range is 0..1: a pick rate, or activations per minute
# of a power fired a handful of times a game. `Rate` above is calibrated for APM
# (values in the hundreds), and its single decimal collapses everything here to
# 0.0 or 0.1 - which is how "18 uses" ended up rendering next to "0.00 / min".
SmallRate = Annotated[
    float,
    PlainSerializer(lambda v: round(v, 4), return_type=float, when_used="json"),
]


# Generic two-decimal-place float: per-game rates and percentiles (player
# profile badges) don't need more precision than that on the wire.
TwoDecimal = Annotated[
    float,
    PlainSerializer(lambda v: round(v, 2), return_type=float, when_used="json"),
]


class General(IntEnum):
    USA = 0
    AIR = 1
    LASER = 2
    SUPER = 3
    CHINA = 4
    NUKE = 5
    TANK = 6
    INFANTRY = 7
    GLA = 8
    TOXIN = 9
    STEALTH = 10
    DEMO = 11
    UNRECOGNIZED = -1


class Faction(IntEnum):
    ANYUSA = 0
    ANYCHINA = 1
    ANYGLA = 2
    UNRECOGNIZED = -1


class Team(IntEnum):
    NONE = 0
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    OBSERVER = -1


class WinLoss(BaseModel):
    wins: int
    losses: int


class DateMessage(BaseModel):
    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    year: int = Field(alias="Year")
    month: int = Field(alias="Month")
    day: int = Field(alias="Day")


class SaveResponse(BaseModel):
    success: bool = False
