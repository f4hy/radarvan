"""Per-player network and PC stats for one match, parsed from client logs."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class NetstatSample(BaseModel):
    """One ~10 s window from a player's own log."""

    model_config = ConfigDict(populate_by_name=True)

    frame: int
    fps: int
    client_ms_avg: float = Field(alias="clientMsAvg")
    client_ms_max: int = Field(alias="clientMsMax")
    logic_ms_avg: float = Field(alias="logicMsAvg")
    logic_ms_max: int = Field(alias="logicMsMax")
    objects: int


class PingSample(BaseModel):
    """Median and worst link ping from one player's PC, at one `GO routes` line."""

    model_config = ConfigDict(populate_by_name=True)

    seconds: int
    median_ms: float = Field(alias="medianMs")
    max_ms: int = Field(alias="maxMs")


class Freeze(BaseModel):
    """The game stopped for `waited_ms` waiting on the players in `slots`."""

    model_config = ConfigDict(populate_by_name=True)

    frame: int
    waited_ms: int = Field(alias="waitedMs")
    slots: list[int]


class PlayerNetstats(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    slot: int
    name: str
    team: int | None = None
    samples: list[NetstatSample]
    pings: list[PingSample]
    client_ms_avg: float | None = Field(default=None, alias="clientMsAvg")
    logic_ms_avg: float | None = Field(default=None, alias="logicMsAvg")
    peak_objects: int | None = Field(default=None, alias="peakObjects")
    median_ping_ms: float | None = Field(default=None, alias="medianPingMs")
    min_fps: int | None = Field(default=None, alias="minFps")
    freezes_caused: int = Field(alias="freezesCaused")
    freeze_ms_caused: int = Field(alias="freezeMsCaused")


class MatchNetstats(BaseModel):
    """Everything the clients logged about one match, keyed by the match seed.

    `freezes` is one player's view (`freezes_view_slot`, the log that lists
    every peer); each client logs only the waits it saw itself.
    """

    model_config = ConfigDict(populate_by_name=True)

    seed: int
    frames: int | None = None
    desync: bool | None = None
    players: list[PlayerNetstats]
    freezes: list[Freeze]
    freezes_view_slot: int | None = Field(default=None, alias="freezesViewSlot")
