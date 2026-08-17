"""Map geometry, map statistics, uploads, and the map registry ops shapes."""

# See radarvan/api_types/__init__.py for why this package is split by context.
# Needed so forward/self references resolve under Python < 3.14 (PEP 649 defers
# by default on 3.14+); required for the ml/ 3.13 training venv.
from __future__ import annotations

from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    field_validator,
)
from .common import (
    DateMessage,
    General,
    PlayerName,
    Team,
)


class MapPlayerWL(BaseModel):
    player: str
    wins: int
    losses: int


class MapGeneralWL(BaseModel):
    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    general: General
    wins: int
    losses: int
    win_rate_delta: float = Field(default=0.0, alias="winRateDelta")


class MapData(BaseModel):
    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    map_name: str = Field(alias="mapName")
    total_games: int = Field(alias="totalGames")
    player_stats: list[MapPlayerWL] = Field(alias="playerStats")
    general_stats: list[MapGeneralWL] = Field(alias="generalStats")


class MapStatsResponse(BaseModel):
    maps: list[MapData]


class MapPlayerRecords(BaseModel):
    """One map, and how everyone who played it did on it.

    ``map_key`` is ``replay_files.map_key`` - the normalized join key a
    caller can match against its own map list; ``map_name`` is the raw
    basename as stored on the match, for display when nothing matches.
    ``total_games`` counts games, not player-results, so it isn't the sum of
    the per-player records.
    """

    map_key: str
    map_name: str
    total_games: int
    players: list[MapPlayerWL]


class MapStat(BaseModel):
    map: str = ""
    team: Team = Team.NONE
    wins: int = 0


class MapResult(BaseModel):
    map: str = ""
    date: DateMessage | None = None
    winner: Team = Team.NONE


class MapResults(BaseModel):
    results: list[MapResult]


class MapStats(BaseModel):
    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    map_stats: list[MapStat] = Field(alias="mapStats")
    over_time: dict[str, MapResults] = Field(alias="overTime")


class MapExtent(BaseModel):
    width: float
    height: float
    grid_width: float
    grid_height: float
    border_size: float


class MapPoint(BaseModel):
    name: str
    x: float
    y: float
    # Supply objects only: available cash (INI default or script override) and
    # whether a start-of-game script overrode the INI default. mapparse emits
    # these as omitempty, so non-supply points (tech/waypoints/garrison) never
    # carry them - 0/False are indistinguishable from "not applicable" here.
    amount: int = 0
    overridden: bool = False


class MapPlayerStart(BaseModel):
    player_number: int
    x: float
    y: float


class MapDataPayload(BaseModel):
    extent: MapExtent
    player_starts: list[MapPlayerStart]
    # mapparse's `supply`/`tech`/`garrison` JSON tags lack `omitempty`, so an
    # empty category serializes as an explicit `null` (a nil Go slice), not a
    # missing key or `[]` - default to empty instead of requiring the key, and
    # normalize below since a `list[...] = []` field still rejects an explicit
    # `null` for the key. `waypoints` does have `omitempty` upstream (key is
    # actually omitted when empty), so its default alone is enough.
    supply: list[MapPoint] = []
    tech: list[MapPoint] = []
    garrison: list[MapPoint] = []
    waypoints: list[MapPoint] = []

    @field_validator("supply", "tech", "garrison", mode="before")
    @classmethod
    def _null_to_empty(cls, v: list[MapPoint] | None) -> list[MapPoint]:
        return v if v is not None else []


class MapsByPlayerCount(BaseModel):
    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    player_count: int = Field(alias="playerCount")
    maps: list[str]


class MapMatchCount(BaseModel):
    model_config = ConfigDict(populate_by_name=True, slots=True)  # type: ignore[typeddict-unknown-key]

    map: str
    match_count: int = Field(alias="matchCount")


class MissingMapInfo(BaseModel):
    map_name: str
    sample_match_id: int
    map_crc_hex: str | None = None


class FetchMissingMapResult(BaseModel):
    map_name: str
    base_name: str | None = None
    tga_s3_uri: str | None = None
    webp_s3_uri: str | None = None
    map_s3_uri: str | None = None
    map_data_saved: bool = False
    error: str | None = None


class MapRenderPlayer(BaseModel):
    name: str
    general: General
    team: int
    position_number: int


class MapRenderRequest(BaseModel):
    map_name: str
    players: list[MapRenderPlayer]


class MapSummaryPlayer(BaseModel):
    name: PlayerName
    general: General
    team: int = 0


class MapSummaryRequest(BaseModel):
    map_name: str
    players: list[MapSummaryPlayer]


class MapSummaryRanking(BaseModel):
    name: str
    wins: int
    losses: int


class MapSummaryTeamH2H(BaseModel):
    team1: list[str]
    team2: list[str]
    team1_wins: int
    team2_wins: int


class MapSummaryPlayerGeneralRecord(BaseModel):
    name: str
    general: General
    wins: int
    losses: int


class MapSummaryDuration(BaseModel):
    avg_minutes: float
    shortest_minutes: float
    longest_minutes: float


class MapSummaryPlayerForm(BaseModel):
    name: str
    map_form: str
    general_form: str


class MapSummaryResponse(BaseModel):
    map_name: str
    total_games: int
    best_general: MapSummaryRanking | None = None
    best_player: MapSummaryRanking | None = None
    team_h2h: MapSummaryTeamH2H | None = None
    team_general_h2h: MapSummaryTeamH2H | None = None
    team_h2h_overall: MapSummaryTeamH2H | None = None
    team_general_h2h_overall: MapSummaryTeamH2H | None = None
    player_general_records: list[MapSummaryPlayerGeneralRecord] = Field(
        default_factory=list
    )
    player_general_overall: list[MapSummaryPlayerGeneralRecord] = Field(
        default_factory=list
    )
    duration: MapSummaryDuration | None = None
    recent_form: list[MapSummaryPlayerForm] = Field(default_factory=list)


class ChooseMapRequest(BaseModel):
    # In-game names of the players in this game; only their votes count.
    # PlayerName auto-resolves aliases (e.g. "skp" -> "Skip") at validation.
    players: list[PlayerName] = Field(default_factory=list)


class ChooseMapCandidate(BaseModel):
    map_name: str
    votes: int
    vetoes: int
    # Selection weight (net score if eligible, else 0).
    weight: int
    # In the draw pool: net score (votes - penalties) is positive.
    eligible: bool
    # Played within the recency window, so docked RECENT_PLAY_PENALTY votes.
    recently_played: bool = False


class ChooseMapResult(BaseModel):
    player_count: int
    # The backend's authoritative weighted-random pick (None if no eligible map).
    chosen_map: str | None = None
    # The chosen map's CRC (uppercase hex), if we can resolve one (stored,
    # from a replay, or computed from the hosted .map bytes); None otherwise.
    chosen_map_crc: str | None = None
    # Every map with at least one vote or veto, for the reveal animation,
    # ordered by votes desc then name.
    candidates: list[ChooseMapCandidate] = Field(default_factory=list)


class MapUploadItem(BaseModel):
    base_name: str
    # WebP data URL of the converted .tga - set in preview, omitted on commit.
    image: str | None = None
    # Number of player start positions (from parsed geometry), if available.
    player_count: int | None = None
    # True if a map with this name already has assets in S3.
    already_exists: bool = False
    # True once the assets have actually been saved (commit response).
    saved: bool = False
    # The computed map CRC (uppercase hex), available in preview and commit.
    crc: str | None = None
    # True once the map was registered with cncstats (commit only).
    pushed_to_cncstats: bool = False


class MapUploadResponse(BaseModel):
    committed: bool
    maps: list[MapUploadItem] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class BackfillMapCrcsResponse(BaseModel):
    processed: int
    resolved: int
    # (map_name, crc) per row touched; crc is None when no match could supply it.
    results: list[tuple[str, str | None]] = Field(default_factory=list)


class PushMapResult(BaseModel):
    map_name: str
    crc: str | None = None
    # True if we POSTed it to cncstats this run.
    pushed: bool = False
    # True if cncstats already had it (/map_exists), so we skipped the push.
    already_present: bool = False
    error: str | None = None


class PushMapsResponse(BaseModel):
    requested: int
    pushed: int
    # Maps cncstats already had, so we skipped the push.
    already_present: int = 0
    results: list[PushMapResult] = Field(default_factory=list)


class ReparseMapResult(BaseModel):
    map_name: str
    # True when this map had no MapData row at all (fetched fresh from
    # cncstats), False when it was an existing row reparsed from its
    # already-hosted `.map` bytes.
    was_missing: bool = False
    ok: bool = True
    error: str | None = None


class ReparseMapsResponse(BaseModel):
    updated: int
    # Maps left needing work after this run (missing + stale combined) - call
    # again with the same max_to_update until this hits 0.
    remaining: int
    results: list[ReparseMapResult] = Field(default_factory=list)


class MapReparseStatus(BaseModel):
    total_maps: int
    stale_maps: int
    # Maps referenced by matches with no MapData row at all.
    missing_maps: int
    mapparse_available: bool
    # SHA-256 of the currently-installed mapparse binary, or None if it's not
    # reachable. Stale rows are those whose stored hash doesn't match this.
    current_mapparse_hash: str | None = None
