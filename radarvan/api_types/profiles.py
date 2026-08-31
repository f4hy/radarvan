"""The player profile page: computed badges, object usage, and per-general history."""

from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict
from datetime import date
from typing import Literal
from .common import General, TwoDecimal
from .details import ObjectSummary


class FavoriteObject(BaseModel):
    """A peer-normalized signature (or avoided) object for a player.

    Rates are per-game on the general the object was scored against; ``score``
    is the smoothed ratio player_rate/peer_rate (>1 = builds it more than
    peers playing the same general).
    """

    model_config = ConfigDict(populate_by_name=True)

    name: str
    general: General
    per_game: TwoDecimal = Field(alias="perGame")
    peer_per_game: TwoDecimal = Field(alias="peerPerGame")
    score: TwoDecimal
    games_on_general: int = Field(alias="gamesOnGeneral")
    total_count: int = Field(alias="totalCount")


class ObjectUsageStat(BaseModel):
    """One object's per-game usage rate for a player against the peer
    distribution - every other profiled player who played the same general.

    Unlike ``FavoriteObject`` (top signature picks only), this covers every
    unit/building/upgrade the player has enough games to compare, so ``z_score``
    can be small or negative - it's a browsable reference, not a highlight reel.
    ``peer_stddev_per_game`` is the population stddev across those peers;
    ``z_score`` is None when it's 0 (every peer had the identical rate).
    """

    model_config = ConfigDict(populate_by_name=True)

    name: str
    general: General
    category: Literal["units", "buildings", "upgrades"]
    per_game: TwoDecimal = Field(alias="perGame")
    peer_mean_per_game: TwoDecimal = Field(alias="peerMeanPerGame")
    peer_median_per_game: TwoDecimal = Field(alias="peerMedianPerGame")
    peer_stddev_per_game: TwoDecimal = Field(alias="peerStddevPerGame")
    z_score: TwoDecimal | None = Field(None, alias="zScore")
    games_on_general: int = Field(alias="gamesOnGeneral")
    peer_count: int = Field(alias="peerCount")


class UnitDamageStat(BaseModel):
    """A player's own highest per-game value-destroyed rate for one unit on
    one general - their own best, not peer-normalized (see FavoriteObject /
    PlayerProfileComputed.signature_damage_dealer for the peer-relative
    pick). "Value destroyed" is build cost of everything killed with this
    unit - the damage-dealt proxy, since replays don't carry raw HP.
    """

    model_config = ConfigDict(populate_by_name=True)

    name: str
    general: General
    per_game: TwoDecimal = Field(alias="perGame")
    total_value_destroyed: int = Field(alias="totalValueDestroyed")
    kill_count: int = Field(alias="killCount")
    games_on_general: int = Field(alias="gamesOnGeneral")


class ProfileBadge(BaseModel):
    """A top-3 behavioral standout among profiled players for one stat."""

    model_config = ConfigDict(populate_by_name=True)

    key: str
    label: str
    description: str
    value: TwoDecimal
    rank: int
    tier: Literal["gold", "silver", "bronze"]
    total_players: int = Field(alias="totalPlayers")


class GeneralWinRatePoint(BaseModel):
    """One point in a player's running win-rate-over-time series for a general.

    ``wins``/``losses`` are cumulative as of this game (not just this game's
    result), so plotting ``win_rate`` against ``game_number`` traces how the
    player's record on this general evolved.
    """

    model_config = ConfigDict(populate_by_name=True)

    date: date
    game_number: int = Field(alias="gameNumber")
    wins: int
    losses: int
    win_rate: float = Field(alias="winRate")


class GeneralWinRateSeries(BaseModel):
    general: General
    points: list[GeneralWinRatePoint]


class GeneralProfileStat(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    general: General
    games: int
    wins: int
    losses: int
    win_rate: float = Field(alias="winRate")


class MapProfileStat(BaseModel):
    map: str
    games: int
    wins: int
    losses: int


class TeammateProfileStat(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    games_together: int = Field(alias="gamesTogether")
    wins_together: int = Field(alias="winsTogether")
    # Pair synergy (log-odds) when the pair passes the synergy model's
    # min-games gate; None when the teammate was picked by games played.
    synergy: float | None = None


class OpponentProfileStat(BaseModel):
    """The profiled player's record against one opponent (wins = subject's wins)."""

    name: str
    wins: int
    losses: int


class PlayerProfileComputed(BaseModel):
    """MatchDetails-derived deep stats for one player.

    Computed as a batch across all profiled players (percentiles are relative
    to that population) and persisted per player; see radarvan.player_profile.
    """

    model_config = ConfigDict(populate_by_name=True)

    favorite_unit: FavoriteObject | None = Field(None, alias="favoriteUnit")
    favorite_building: FavoriteObject | None = Field(None, alias="favoriteBuilding")
    favorite_upgrade: FavoriteObject | None = Field(None, alias="favoriteUpgrade")
    favorite_power: FavoriteObject | None = Field(None, alias="favoritePower")
    # Objects peers build regularly on a shared general that this player avoids.
    aversions: list[FavoriteObject] = Field(default_factory=list)
    avg_apm: float | None = Field(None, alias="avgApm")
    apm_percentile: float | None = Field(None, alias="apmPercentile")
    first_blood_rate: float | None = Field(None, alias="firstBloodRate")
    first_blood_percentile: float | None = Field(None, alias="firstBloodPercentile")
    avg_time_to_rank_5: float | None = Field(None, alias="avgTimeToRank5")
    rank_5_percentile: float | None = Field(None, alias="rank5Percentile")
    superweapons_built_per_game: float | None = Field(
        None, alias="superweaponsBuiltPerGame"
    )
    superweapon_percentile: float | None = Field(None, alias="superweaponPercentile")
    badges: list[ProfileBadge] = Field(default_factory=list)
    # Every unit/building/upgrade with enough games to compare - see
    # ObjectUsageStat; a browsable reference, not just the favorites above.
    object_usage: list[ObjectUsageStat] = Field(
        default_factory=list, alias="objectUsage"
    )
    # The unit this player has dealt the most value-destroyed with, per game
    # (their own top rate - not peer-normalized; see UnitDamageStat).
    top_damage_dealer: UnitDamageStat | None = Field(None, alias="topDamageDealer")
    # The unit this player deals more damage with than peers of the same
    # general, peer-normalized like favorite_unit/etc above.
    signature_damage_dealer: FavoriteObject | None = Field(
        None, alias="signatureDamageDealer"
    )
    # Every unit this player has ever killed with, summed across all games and
    # generals (Count = kills, TotalSpent = value destroyed) - a browsable
    # reference, not filtered to a signature/outlier like the two picks above.
    damage_by_unit: dict[str, ObjectSummary] = Field(
        default_factory=dict, alias="damageByUnit"
    )
    games_analyzed: int = Field(alias="gamesAnalyzed")
    computed_at: date = Field(alias="computedAt")


class PlayerProfile(BaseModel):
    """Full profile for one player: live MatchInfo-derived stats plus the
    persisted deep stats (None until the batch recompute has run)."""

    model_config = ConfigDict(populate_by_name=True)

    player: str
    games: int
    wins: int
    losses: int
    generals: list[GeneralProfileStat]
    general_win_rate_over_time: list[GeneralWinRateSeries] = Field(
        default_factory=list, alias="generalWinRateOverTime"
    )
    most_played_general: GeneralProfileStat | None = Field(
        None, alias="mostPlayedGeneral"
    )
    best_general: GeneralProfileStat | None = Field(None, alias="bestGeneral")
    favorite_map: MapProfileStat | None = Field(None, alias="favoriteMap")
    best_map: MapProfileStat | None = Field(None, alias="bestMap")
    favorite_teammate: TeammateProfileStat | None = Field(
        None, alias="favoriteTeammate"
    )
    nemesis: OpponentProfileStat | None = None
    favorite_victim: OpponentProfileStat | None = Field(None, alias="favoriteVictim")
    avg_win_duration_minutes: float | None = Field(None, alias="avgWinDurationMinutes")
    avg_loss_duration_minutes: float | None = Field(
        None, alias="avgLossDurationMinutes"
    )
    computed: PlayerProfileComputed | None = None
