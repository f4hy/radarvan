"""Per-player profile computation: peer-normalized favorites, aversions,
behavioral percentiles, and the live MatchInfo-derived profile parts.

The interesting question is never "what does this player build most" (that is
always workers) but "what does this player build more than everyone else
playing the same general". For each (player, general, object) we compare the
player's per-game build rate against the pooled rate of every *other* player
on the same general, with Bayesian shrinkage toward the pooled rate so rare
objects and small samples collapse to a neutral score instead of exploding.

Two halves, split by data source:

- ``compute_all_profiles`` needs full ``MatchDetails`` (the per-object count
  dicts in ``player_summary``); it runs as a batch across every profiled
  player because percentiles are relative to that population, and its result
  is persisted per player (see ``repositories.profiles``).
- ``compute_live_profile`` needs only ``list[MatchInfo]`` and is cheap enough
  to run per request from ``cache.competitive_matches``.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import statistics
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal, NamedTuple

import structlog

from .api_types import (
    AcademyStats,
    FavoriteObject,
    General,
    GeneralProfileStat,
    GeneralWinRatePoint,
    GeneralWinRateSeries,
    MapProfileStat,
    MatchDetails,
    MatchInfo,
    ObjectUsageStat,
    OpponentProfileStat,
    PlayerProfile,
    PlayerProfileComputed,
    ProfileBadge,
    TeammateProfileStat,
)
from .build_order import is_economy_unit
from .db_utils import DatabaseManager
from .player_ids import CPU_NAME_MAPPING, resolve_player_name
from .player_synergy import PairSynergy
from .replay_files import map_basename
from .replay_helpers import clean_object_name
from .superlatives import EXCLUDED_PLAYERS
from .timeline_events import clean_power_name

logger = structlog.get_logger(__name__)


# Bump when the profile *logic* changes without changing the
# PlayerProfileComputed schema (scoring constants, new exclusions, ...).
# Schema changes are caught automatically by the model_json_schema hash below.
# v2: favorites require a minimum per-game rate (rare novelty objects with a
# zero peer rate were winning on ratio alone), scores are capped at 100, and
# aversions are deduped by object name across generals.
# v3: cross-faction objects are excluded from favorites and aversions - any
# side can build another faction's units after capturing an enemy production
# building, and those rare capture plays produced nonsense results ("avoids
# Quad Cannons" as China, who can't normally build them).
# v4: (reverted in v5) powers were faction-filtered via usage dominance.
# v5: (reverted in v6) powers skipped faction filtering entirely.
# v6: powers require a *dominant* faction (>=90% of all uses) matching the
# player's faction, and powers with no dominant faction are excluded from
# favorites and aversions altogether. Name checks can't classify powers
# (ability names carry the unit name), and neutral powers used by every
# faction (GPSScrambler is a per-player habit across all generals in this
# community) make no sense framed per-general.
# v7: favorites/aversions peer baselines are restricted to other ACTIVE
# (>= min_profile_games) players only - an occasional guest's rate on a
# rarely-played general was setting the peer bar for regulars.
# v8: units/buildings misclassified by cncstats (same raw object name
# appearing under both dicts, e.g. a vehicle occasionally logged as a
# building) are reconciled to their dominant category before aggregation -
# see _reconcile_unit_building_split.
# v9: objects that never cost anything (e.g. GLA Stealth's free "Hole"
# tunnel-network exit points, logged with TotalSpent always 0) are dropped
# entirely from favorites/aversions - see _drop_zero_cost_objects.
# v10: (superseded by v11) badge percentile cutoff lowered 90 -> 70.
# v11: academy badges are rank-based medals (gold/silver/bronze for the top
# 3 players per stat) instead of a percentile threshold - a fixed medal
# count reads more clearly than a percentile cutoff with a dozen-ish players.
# v12: units/buildings/upgrades whose raw name has no faction word (e.g.
# "Comanche", a USA unit whose name doesn't say "America") fall back to
# usage-dominance classification, same mechanism powers already used -
# renamed _power_faction_map -> _usage_faction_map, dominance threshold
# lowered 90% -> 65% (empirically still cleanly separates faction-locked
# objects from genuinely shared ones; see _FACTION_DOMINANCE_THRESHOLD).
# v13: dropped the "Promotion Chaser" (generals_points_spent) badge - already
# captured in spirit by the Avg Time to Rank 5 tendency stat. Badge
# descriptions reworded to a direct superlative ("Builds the most X") instead
# of "more than nearly anyone else" phrasing.
# v14: general-flavor-prefixed raw names (Lazr_, Infa_, Tank_, ...) are merged
# into their canonical form before aggregation - a minority of a player's
# builds mistagged with another general's flavor prefix were fragmenting off
# a common unit and, with zero peers under that exact key, spuriously winning
# as a "100% unique" favorite (e.g. Modus's ordinary Missile Defenders showing
# "peers never build this" because 27 of 751 were Lazr_-tagged). See
# _merge_general_flavor_variants.
# v15: added object_usage - every unit/building/upgrade a player has enough
# games to compare, z-scored against the other profiled players who played
# the same general (mean/stddev over the raw per-player rate distribution,
# not the smoothed favorite/aversion ratio). See _object_usage_rates.
# v16: object_usage also reports the peer median per-game rate, labeled
# directly on the usage chart (the mean/stddev band alone doesn't give
# readers a concrete number to anchor on).
_PROFILE_LOGIC_VERSION = 16


def _compute_profile_version() -> str:
    schema_json = json.dumps(PlayerProfileComputed.model_json_schema(), sort_keys=True)
    schema_hash = hashlib.sha256(schema_json.encode()).hexdigest()[:12]
    return f"{_PROFILE_LOGIC_VERSION}-{schema_hash}"


PROFILE_VERSION = _compute_profile_version()

# Resolved names never profiled nor used as peer baselines.
_NON_HUMAN_PLAYERS: frozenset[str] = (
    frozenset(CPU_NAME_MAPPING.values()) | EXCLUDED_PLAYERS
)

# Deep stats need enough games for peer-normalized rates to mean anything.
DEFAULT_MIN_PROFILE_GAMES = 60

# APM samples shorter than this are unreliable (matches superlatives' rule).
_MIN_APM_MINUTES = 1.0

# Minimum matches carrying a given optional signal (academy block, APM sample)
# before that signal contributes percentiles/badges for a player.
_MIN_SIGNAL_GAMES = 10

# Academy-stat badges are medals: the top 3 players by per-game rate for each
# stat get gold/silver/bronze, not everyone above some percentile line.
_MEDAL_TIERS: tuple[Literal["gold", "silver", "bronze"], ...] = (
    "gold",
    "silver",
    "bronze",
)


class _BadgeMeta(NamedTuple):
    label: str
    description: str


_ACADEMY_BADGES: dict[str, _BadgeMeta] = {
    "cleared_garrisoned_buildings": _BadgeMeta(
        "Building Clearer",
        "Clears the most enemy-garrisoned buildings.",
    ),
    "control_groups_used": _BadgeMeta(
        "Control Group Pro",
        "Relies on control groups (Ctrl+number) the most.",
    ),
    "double_click_attack_move_orders_given": _BadgeMeta(
        "Attack-Move Spammer",
        "Issues the most double-click attack-move orders.",
    ),
    "firestorms_created": _BadgeMeta(
        "Firestarter",
        "Sets off the most Inferno Cannon firestorms.",
    ),
    "gatherers_built": _BadgeMeta(
        "Economy Builder",
        "Builds the most resource-gathering units per game.",
    ),
    "guard_ability_used_count": _BadgeMeta(
        "Guard Duty",
        "Uses the Guard ability the most.",
    ),
    "heroes_built": _BadgeMeta(
        "Hero Collector",
        "Builds the most hero units (Jarmen Kell, Colonel Burton, Black Lotus...).",
    ),
    "mines_cleared": _BadgeMeta(
        "Minesweeper",
        "Clears the most enemy mines.",
    ),
    "peons_built": _BadgeMeta(
        "Peon Factory",
        "Builds the most worker units.",
    ),
    "salvage_collected": _BadgeMeta(
        "Scrap Scavenger",
        "Collects the most battlefield salvage.",
    ),
    "secondary_income_units_built": _BadgeMeta(
        "Side Hustler",
        "Builds the most secondary income units (black markets, hackers...).",
    ),
    "special_powers_used": _BadgeMeta(
        "Power User",
        "Fires off the most generals powers.",
    ),
    "structures_captured": _BadgeMeta(
        "Capture Artist",
        "Captures the most enemy and neutral structures.",
    ),
    "structures_garrisoned": _BadgeMeta(
        "Garrison Commander",
        "Garrisons the most buildings with troops.",
    ),
    "supply_centers_built": _BadgeMeta(
        "Expansionist",
        "Builds the most supply centers per game.",
    ),
    "upgrades_purchased": _BadgeMeta(
        "Tech Enthusiast",
        "Purchases the most upgrades.",
    ),
    "vehicles_disguised": _BadgeMeta(
        "Master of Disguise",
        "Disguises the most vehicles.",
    ),
}


class ObjectCategory(StrEnum):
    UNITS = "units"
    BUILDINGS = "buildings"
    UPGRADES = "upgrades"
    POWERS = "powers"


@dataclass(frozen=True, slots=True)
class PlayerMatchProjection:
    """One player's contribution to one match, reduced from MatchDetails.

    Object dicts are keyed by RAW replay names (``Lazr_AmericaInfantryRanger``);
    they are only cleaned for display when a favorite/aversion is reported.
    Raw names are consistent within a general, which is the only grouping the
    scorer uses.
    """

    name: str  # canonical (alias + color resolved)
    general: General
    won: bool
    units: dict[str, int]
    buildings: dict[str, int]
    upgrades: dict[str, int]
    powers: dict[str, int]
    # Total money spent per raw object name, paired with units/buildings/
    # upgrades above (same keys) - used only to detect objects that never
    # cost anything (see _drop_zero_cost_objects). Powers have no cost field.
    unit_spent: dict[str, int]
    building_spent: dict[str, int]
    upgrade_spent: dict[str, int]
    apm: float | None
    got_first_blood: bool
    time_to_rank_5: float | None
    academy: AcademyStats | None
    superweapons_built: int

    def category_counts(self, category: ObjectCategory) -> dict[str, int]:
        return {
            ObjectCategory.UNITS: self.units,
            ObjectCategory.BUILDINGS: self.buildings,
            ObjectCategory.UPGRADES: self.upgrades,
            ObjectCategory.POWERS: self.powers,
        }[category]


@dataclass(frozen=True, slots=True)
class ProfileMatchData:
    match_id: int
    players: list[PlayerMatchProjection]


def profile_data_from_details(
    details: MatchDetails, info: MatchInfo
) -> ProfileMatchData:
    """Reduce one match's MatchDetails to the per-player projection.

    ``details.player_summary`` and ``info.players`` come from the same replay,
    so they share raw names; ``info`` supplies general/team/color (and the
    color-aware alias resolution), ``details`` supplies the object counts.
    Observers, CPUs, and excluded players are dropped here so they can never
    become profile subjects or peer baselines.
    """
    by_raw_name: dict[str, tuple[str, General, bool]] = {}
    for p in info.players:
        if p.team <= 0 or p.general == General.UNRECOGNIZED:
            continue
        resolved = resolve_player_name(p.name, p.color)
        if resolved in _NON_HUMAN_PLAYERS or p.Type == "C":
            continue
        by_raw_name[p.name] = (resolved, p.general, p.won)

    apm_by_raw = {
        a.player_name: a.apm
        for a in details.apms
        if a.apm > 0 and a.minutes >= _MIN_APM_MINUTES
    }
    sw_built: dict[str, int] = defaultdict(int)
    for ev in details.timeline_events:
        if ev.event_type == "superweapon_built":
            sw_built[ev.player_name] += 1
    first_blood_attacker = details.first_blood.attacker if details.first_blood else None

    projections: list[PlayerMatchProjection] = []
    for ps in details.player_summary:
        resolved_info = by_raw_name.get(ps.Name)
        if resolved_info is None:
            continue
        resolved, general, won = resolved_info
        projections.append(
            PlayerMatchProjection(
                name=resolved,
                general=general,
                won=won,
                units={k: v.Count for k, v in ps.UnitsCreated.items()},
                buildings={k: v.Count for k, v in ps.BuildingsBuilt.items()},
                upgrades={k: v.Count for k, v in ps.UpgradesBuilt.items()},
                powers=dict(ps.PowersUsed),
                unit_spent={k: v.TotalSpent for k, v in ps.UnitsCreated.items()},
                building_spent={k: v.TotalSpent for k, v in ps.BuildingsBuilt.items()},
                upgrade_spent={k: v.TotalSpent for k, v in ps.UpgradesBuilt.items()},
                apm=apm_by_raw.get(ps.Name),
                got_first_blood=ps.Name == first_blood_attacker,
                time_to_rank_5=details.time_to_rank_5.get(ps.Name),
                academy=ps.Academy,
                superweapons_built=sw_built.get(ps.Name, 0),
            )
        )
    return ProfileMatchData(match_id=details.match_id, players=projections)


async def load_many_profile_data(
    games: list[MatchInfo],
    db_manager: DatabaseManager,
    max_concurrent: int = 2,
    chunk_size: int = 10,
) -> list[ProfileMatchData]:
    """Load profile projections for many matches with bounded concurrency.

    Each match is loaded as full MatchDetails (through the durable details
    cache), immediately reduced to ProfileMatchData, and the details discarded
    to keep peak memory low - same shape as load_many_superlative_data.
    """
    # Imported here to break a cycle: match_details imports api_types which
    # this module also feeds; the DB-bound loader is the only coupling point.
    from .match_details import load_match_details_threadsafe

    semaphore = asyncio.Semaphore(max_concurrent)

    async def _bounded(info: MatchInfo) -> ProfileMatchData | None:
        async with semaphore:
            details = await asyncio.to_thread(
                load_match_details_threadsafe, info.id, db_manager
            )
        if details is None:
            return None
        return profile_data_from_details(details, info)

    all_results: list[ProfileMatchData] = []
    for i in range(0, len(games), chunk_size):
        chunk = games[i : i + chunk_size]
        chunk_results = await asyncio.gather(*[_bounded(info) for info in chunk])
        all_results.extend(r for r in chunk_results if r is not None)
    return all_results


# ---------------------------------------------------------------------------
# Peer-normalized favorites / aversions
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CategoryAggregate:
    """Cross-match totals for one object category.

    counts: (player, general, raw object) -> total built
    games:  (player, general) -> matches played
    """

    counts: dict[tuple[str, General, str], int]
    games: dict[tuple[str, General], int]


def aggregate_category(
    data: list[ProfileMatchData], category: ObjectCategory
) -> CategoryAggregate:
    counts: dict[tuple[str, General, str], int] = defaultdict(int)
    games: dict[tuple[str, General], int] = defaultdict(int)
    for match in data:
        for proj in match.players:
            games[(proj.name, proj.general)] += 1
            for obj, count in proj.category_counts(category).items():
                counts[(proj.name, proj.general, obj)] += count
    return CategoryAggregate(counts=dict(counts), games=dict(games))


# Ratios beyond this are all "way more than anyone else"; the exact number is
# noise (it blows up when the peer rate is ~0), so displayed scores cap here.
_MAX_SCORE = 100.0

# Bayesian shrinkage strength for _smoothed_rates: how many "pseudo-games" of
# the pooled rate to blend in, shared default for compute_favorites and
# compute_aversions.
_DEFAULT_PSEUDO_GAMES = 5.0


@dataclass(frozen=True, slots=True)
class ScoredObject:
    object_name: str  # cleaned, display-ready
    general: General
    score: float
    player_rate: float  # raw per-game evidence
    peer_rate: float
    player_games: int
    peer_games: int
    total_count: int

    def to_wire(self) -> FavoriteObject:
        # Rounding happens at the wire type (api_types.TwoDecimal), not here.
        return FavoriteObject(
            name=self.object_name,
            general=self.general,
            per_game=self.player_rate,
            peer_per_game=self.peer_rate,
            score=self.score,
            games_on_general=self.player_games,
            total_count=self.total_count,
        )


def _smoothed_rates(
    c_p: int, n_p: int, c_q: int, n_q: int, pseudo_games: float
) -> tuple[float, float]:
    """Per-game rates shrunk toward the pooled rate by ``pseudo_games``.

    The pooled prior keeps both denominators positive whenever anyone built
    the object at all, so ratios are always finite; objects with little total
    evidence shrink toward score 1.0 (neutral) instead of dominating.
    """
    r0 = (c_p + c_q) / (n_p + n_q)
    player = (c_p + pseudo_games * r0) / (n_p + pseudo_games)
    peer = (c_q + pseudo_games * r0) / (n_q + pseudo_games)
    return player, peer


_CATEGORY_CLEANERS: dict[ObjectCategory, Callable[[str], str]] = {
    ObjectCategory.UNITS: clean_object_name,
    ObjectCategory.BUILDINGS: clean_object_name,
    ObjectCategory.UPGRADES: clean_object_name,
    ObjectCategory.POWERS: clean_power_name,
}

_FACTION_WORDS = ("America", "China", "GLA")

_GENERAL_FACTION: dict[General, str] = {
    General.USA: "America",
    General.AIR: "America",
    General.LASER: "America",
    General.SUPER: "America",
    General.CHINA: "China",
    General.NUKE: "China",
    General.TANK: "China",
    General.INFANTRY: "China",
    General.GLA: "GLA",
    General.TOXIN: "GLA",
    General.STEALTH: "GLA",
    General.DEMO: "GLA",
}


def _object_faction(raw: str) -> str | None:
    """Faction word embedded in a raw replay object name, if any.

    Raw names carry zero or more ``Token_`` prefixes before the faction word
    (``GLAVehicleQuadCannon``, ``Lazr_AmericaInfantryRanger``,
    ``SupW_Upgrade_AmericaAdvancedControlRods``). Neutral names like
    ``Upgrade_InfantryCaptureBuilding`` have no faction word - return None.
    """
    name = raw
    while True:
        for faction in _FACTION_WORDS:
            if name.startswith(faction):
                return faction
        if "_" not in name:
            return None
        name = name.split("_", 1)[1]


# An object belongs to a faction when at least this share of all its uses
# come from that faction's generals. Empirically chosen: in this dataset,
# genuinely faction-locked objects cluster at ~86%+ dominance even accounting
# for capture-play/gifting noise (one raw Comanche upgrade name sits at the
# low end, 70%), while genuinely shared/neutral mechanics (GPSScrambler,
# InfantryCaptureBuilding) never exceed ~55% for any single faction - 0.65
# sits cleanly in the gap between the two clusters.
_FACTION_DOMINANCE_THRESHOLD = 0.65


def _usage_faction_map(agg: CategoryAggregate) -> dict[str, str]:
    """Dominant faction per object, derived from who actually uses it.

    Ground truth for faction ownership: cross-faction use exists (captured
    enemy production, allied unit gifting, or - as this community's data
    shows for a handful of upgrades - an internal ability name that doesn't
    match which faction actually uses it) but is a minority share, so a
    faction-owned object's own faction dominates its total count. Objects
    with no dominant faction are genuinely shared (e.g. GPSScrambler is a
    per-player habit used on every general) and get no entry.
    """
    totals: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for (_, general, obj), count in agg.counts.items():
        faction = _GENERAL_FACTION.get(general)
        if faction is not None:
            totals[obj][faction] += count
    result: dict[str, str] = {}
    for obj, by_faction in totals.items():
        total = sum(by_faction.values())
        faction, top = max(by_faction.items(), key=lambda kv: kv[1])
        if total > 0 and top / total >= _FACTION_DOMINANCE_THRESHOLD:
            result[obj] = faction
    return result


def _is_foreign_faction(
    obj: str,
    general: General,
    category: ObjectCategory,
    usage_factions: dict[str, str],
) -> bool:
    """True when the object doesn't belong to the general's own faction.

    Cross-faction objects only reach a player through captured enemy
    production buildings or allied unit gifts - rare plays that must not
    drive favorites ("favorite unit: Scorpion" as China) or aversions
    ("avoids Quad Cannons" as a general who can't normally build them).

    Units/buildings/upgrades are classified by the faction word in their raw
    name when present (exact signal). Powers always rely on usage dominance
    (``usage_factions``, from :func:`_usage_faction_map`): their raw names
    carry the owning unit/ability name, never a faction word. Units/
    buildings/upgrades whose name has no faction word - e.g. "Comanche",
    a USA unit whose name doesn't contain "America" - also fall back to
    dominance. Either way, an object with no dominant faction is neutral -
    used across generals - and a per-general framing for it is meaningless,
    so it's excluded from consideration entirely, not attributed to anyone.
    """
    faction = _GENERAL_FACTION.get(general)
    if faction is None:
        return False
    if category != ObjectCategory.POWERS:
        obj_faction = _object_faction(obj)
        if obj_faction is not None:
            return obj_faction != faction
    # No dominant faction (None) compares unequal to any real faction, so an
    # undetermined object is excluded, same as an actively-mismatched one -
    # it isn't specific to this general either way.
    dominant = usage_factions.get(obj)
    return dominant != faction


def _peer_totals(
    agg: CategoryAggregate,
) -> tuple[dict[tuple[General, str], int], dict[General, int]]:
    """Total counts per (general, object) and total games per general."""
    count_by_go: dict[tuple[General, str], int] = defaultdict(int)
    games_by_general: dict[General, int] = defaultdict(int)
    for (_, general, obj), count in agg.counts.items():
        count_by_go[(general, obj)] += count
    for (_, general), n in agg.games.items():
        games_by_general[general] += n
    return dict(count_by_go), dict(games_by_general)


# A favorite must be something the player builds regularly, not a novelty:
# without a rate floor, an object nobody else ever builds wins on ratio alone
# even at a handful of total builds. Per-game floors per category (powers and
# upgrades are naturally lower-frequency than units).
_MIN_FAVORITE_RATE: dict[ObjectCategory, float] = {
    ObjectCategory.UNITS: 0.4,
    ObjectCategory.BUILDINGS: 0.2,
    ObjectCategory.UPGRADES: 0.25,
    ObjectCategory.POWERS: 0.15,
}


def compute_favorites(
    agg: CategoryAggregate,
    category: ObjectCategory,
    *,
    min_games: int = 10,
    min_count: int = 5,
    min_peer_games: int = 20,
    pseudo_games: float = _DEFAULT_PSEUDO_GAMES,
    min_score: float = 1.25,
    min_rate: float | None = None,
    peer_totals: tuple[dict[tuple[General, str], int], dict[General, int]]
    | None = None,
    usage_factions: dict[str, str] | None = None,
) -> dict[str, ScoredObject]:
    """Each player's signature object: highest peer-normalized build rate.

    Only (player, general) pairs with ``min_games`` games qualify, peers must
    have ``min_peer_games`` on the same general, and the player must have
    built the object ``min_count`` times total at ``min_rate``+ per game.
    Economy units (workers, dozers, supply trucks) are excluded from UNITS -
    every game has them. ``peer_totals``/``usage_factions`` let a caller that
    already computed them for this ``agg`` (e.g. to share with
    compute_aversions) pass them in instead of paying for another scan.
    """
    if min_rate is None:
        min_rate = _MIN_FAVORITE_RATE[category]
    count_by_go, games_by_general = peer_totals or _peer_totals(agg)
    cleaner = _CATEGORY_CLEANERS[category]
    usage_factions = (
        usage_factions if usage_factions is not None else _usage_faction_map(agg)
    )
    best: dict[str, ScoredObject] = {}
    for (player, general, obj), c_p in agg.counts.items():
        if c_p < min_count:
            continue
        n_p = agg.games[(player, general)]
        if n_p < min_games or c_p / n_p < min_rate:
            continue
        n_q = games_by_general[general] - n_p
        if n_q < min_peer_games:
            continue
        if _is_foreign_faction(obj, general, category, usage_factions):
            continue
        cleaned = cleaner(obj)
        if category == ObjectCategory.UNITS and is_economy_unit(cleaned):
            continue
        c_q = count_by_go[(general, obj)] - c_p
        player_s, peer_s = _smoothed_rates(c_p, n_p, c_q, n_q, pseudo_games)
        score = min(player_s / peer_s, _MAX_SCORE)
        if score < min_score:
            continue
        candidate = ScoredObject(
            object_name=cleaned,
            general=general,
            score=score,
            player_rate=c_p / n_p,
            peer_rate=c_q / n_q,
            player_games=n_p,
            peer_games=n_q,
            total_count=c_p,
        )
        current = best.get(player)
        if current is None or (score, c_p) > (current.score, current.total_count):
            best[player] = candidate
    return best


def _objects_by_general(
    agg: CategoryAggregate,
    category: ObjectCategory,
    usage_factions: dict[str, str],
) -> dict[General, set[str]]:
    """Every object anyone built per general, excluding foreign-faction/
    captured-play objects (see ``_is_foreign_faction``) - so a player's zero
    count for a real object is visible instead of the object being silently
    absent. Shared by ``compute_aversions`` (peers regularly build it, the
    player avoids it) and ``_object_usage_rates`` (the full per-player rate
    distribution).
    """
    objects_by_general: dict[General, set[str]] = defaultdict(set)
    for _, general, obj in agg.counts:
        if not _is_foreign_faction(obj, general, category, usage_factions):
            objects_by_general[general].add(obj)
    return objects_by_general


def compute_aversions(
    agg: CategoryAggregate,
    category: ObjectCategory,
    *,
    min_games: int = 10,
    min_peer_games: int = 30,
    min_peer_rate: float = 0.5,
    pseudo_games: float = _DEFAULT_PSEUDO_GAMES,
    max_ratio: float = 0.5,
    peer_totals: tuple[dict[tuple[General, str], int], dict[General, int]]
    | None = None,
    usage_factions: dict[str, str] | None = None,
) -> dict[str, list[ScoredObject]]:
    """Objects peers build regularly on a shared general that a player avoids.

    Candidates: peers average at least ``min_peer_rate`` builds/game over
    ``min_peer_games`` games, while the player (with ``min_games`` on the
    general) builds under ``max_ratio`` of the peer rate. ``score`` is the
    inverted smoothed ratio (higher = stronger avoidance). Returns ALL
    qualifying items per player, sorted by score; the caller trims.
    ``peer_totals``/``usage_factions`` let a caller that already computed
    them for this ``agg`` (e.g. to share with compute_favorites) pass them in
    instead of paying for another scan.
    """
    count_by_go, games_by_general = peer_totals or _peer_totals(agg)
    cleaner = _CATEGORY_CLEANERS[category]
    usage_factions = (
        usage_factions if usage_factions is not None else _usage_faction_map(agg)
    )
    objects_by_general = _objects_by_general(agg, category, usage_factions)

    result: dict[str, list[ScoredObject]] = defaultdict(list)
    for (player, general), n_p in agg.games.items():
        if n_p < min_games:
            continue
        n_q = games_by_general[general] - n_p
        if n_q < min_peer_games:
            continue
        for obj in objects_by_general[general]:
            c_p = agg.counts.get((player, general, obj), 0)
            c_q = count_by_go[(general, obj)] - c_p
            peer_rate = c_q / n_q
            if peer_rate < min_peer_rate:
                continue
            player_rate = c_p / n_p
            if player_rate >= max_ratio * peer_rate:
                continue
            player_s, peer_s = _smoothed_rates(c_p, n_p, c_q, n_q, pseudo_games)
            result[player].append(
                ScoredObject(
                    object_name=cleaner(obj),
                    general=general,
                    score=min(peer_s / player_s, _MAX_SCORE),
                    player_rate=player_rate,
                    peer_rate=peer_rate,
                    player_games=n_p,
                    peer_games=n_q,
                    total_count=c_p,
                )
            )
    return {
        player: sorted(items, key=lambda s: s.score, reverse=True)
        for player, items in result.items()
    }


# A player needs this many games on a general before their rate for any
# object on it is trusted enough to report - same floor compute_favorites/
# compute_aversions use for the subject side.
_MIN_USAGE_GAMES = 10
# Need at least this many *other* profiled players' rates to call a mean/
# stddev meaningful - below this a "population" is just noise.
_MIN_USAGE_PEERS = 3


def _object_usage_rates(
    agg: CategoryAggregate,
    category: ObjectCategory,
    usage_factions: dict[str, str],
) -> dict[tuple[General, str], dict[str, float]]:
    """Every profiled player's per-game rate for every (general, object) pair
    anyone built on that general - 0 for players who never built it, so a
    non-builder is part of the distribution instead of silently absent, kept
    here as the raw per-player spread rather than collapsed into one pooled
    peer rate (see ``_objects_by_general``).
    """
    objects_by_general = _objects_by_general(agg, category, usage_factions)

    result: dict[tuple[General, str], dict[str, float]] = defaultdict(dict)
    for (player, general), n_p in agg.games.items():
        for obj in objects_by_general[general]:
            result[(general, obj)][player] = (
                agg.counts.get((player, general, obj), 0) / n_p
            )
    return dict(result)


def _player_object_usage(
    name: str,
    usage_rates: dict[ObjectCategory, dict[tuple[General, str], dict[str, float]]],
    games_by_player_general: dict[tuple[str, General], int],
) -> list[ObjectUsageStat]:
    """Every unit/building/upgrade ``name`` has enough games to compare,
    z-scored against the other profiled players who played the same general.
    A browsable reference (see ObjectUsageStat) - unlike favorites/aversions,
    nothing here is filtered for being a signature or an outlier.
    """
    stats: list[ObjectUsageStat] = []
    for category, by_key in usage_rates.items():
        cleaner = _CATEGORY_CLEANERS[category]
        for (general, obj), rates in by_key.items():
            if games_by_player_general.get((name, general), 0) < _MIN_USAGE_GAMES:
                continue
            player_rate = rates.get(name)
            if player_rate is None:
                continue
            peer_rates = [rate for p, rate in rates.items() if p != name]
            if len(peer_rates) < _MIN_USAGE_PEERS:
                continue
            peer_mean = statistics.mean(peer_rates)
            peer_median = statistics.median(peer_rates)
            peer_stddev = statistics.pstdev(peer_rates)
            z_score = (
                (player_rate - peer_mean) / peer_stddev if peer_stddev > 0 else None
            )
            stats.append(
                ObjectUsageStat(
                    name=cleaner(obj),
                    general=general,
                    category=category.value,
                    per_game=player_rate,
                    peer_mean_per_game=peer_mean,
                    peer_median_per_game=peer_median,
                    peer_stddev_per_game=peer_stddev,
                    z_score=z_score,
                    games_on_general=games_by_player_general[(name, general)],
                    peer_count=len(peer_rates),
                )
            )
    return stats


# ---------------------------------------------------------------------------
# Percentiles / badges
# ---------------------------------------------------------------------------


def _percentile(
    values: list[float], mine: float, higher_is_better: bool = True
) -> float:
    """Percent of the population this value beats (100 = best, 0 = worst)."""
    if len(values) <= 1:
        return 100.0
    if higher_is_better:
        beaten = sum(1 for v in values if v < mine)
    else:
        beaten = sum(1 for v in values if v > mine)
    return round(100.0 * beaten / (len(values) - 1), 1)


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _map_projections(
    data: list[ProfileMatchData],
    fix: Callable[[PlayerMatchProjection], PlayerMatchProjection],
) -> list[ProfileMatchData]:
    """Rebuild every match's player list through `fix`, preserving match_id."""
    return [
        ProfileMatchData(
            match_id=match.match_id, players=[fix(p) for p in match.players]
        )
        for match in data
    ]


# The 9 non-base generals each get a short "flavor" prefix cncstats attaches
# to some of that general's builds (Lazr_ = Laser General, Infa_ = Infantry
# General, ...) - purely cosmetic, never a different underlying object. It's
# redundant with the (player, general) grouping every scorer already uses,
# and appears inconsistently: a handful of a player's builds can carry a
# flavor tag that doesn't match their attributed general for that match (see
# _merge_general_flavor_variants). A closed, verified set - "Upgrade_" is a
# different kind of marker (object type, not general) and is left alone.
_GENERAL_FLAVOR_PREFIXES = (
    "AirF_",
    "Lazr_",
    "SupW_",
    "Infa_",
    "Tank_",
    "Nuke_",
    "Chem_",
    "Demo_",
    "Slth_",
)


def _canonical_object_name(name: str) -> str:
    for prefix in _GENERAL_FLAVOR_PREFIXES:
        if name.startswith(prefix):
            return name[len(prefix) :]
    return name


def _merge_by_canonical_name(counts: dict[str, int]) -> dict[str, int]:
    if not any(_canonical_object_name(k) != k for k in counts):
        return counts
    merged: dict[str, int] = defaultdict(int)
    for name, count in counts.items():
        merged[_canonical_object_name(name)] += count
    return dict(merged)


def _merge_general_flavor_variants(
    data: list[ProfileMatchData],
) -> list[ProfileMatchData]:
    """Collapse general-flavor-prefixed raw names into their canonical form.

    Without this, a player whose declared general is (say) USA but who has a
    handful of builds mistagged "Lazr_AmericaInfantryMissileDefender" (Laser
    General's flavor) ends up with that object split into two raw-name
    buckets: the common "AmericaInfantryMissileDefender" (scores normally)
    and the rare flavor-tagged variant, which - since literally no peer ever
    used that exact prefixed key - looks like a 100%-unique favorite despite
    being a small fraction of the player's actual usage of an ordinary unit.
    Run first, before the other reconciliation passes, so they see fully
    pooled counts/spend per canonical object.
    """

    def fix(proj: PlayerMatchProjection) -> PlayerMatchProjection:
        units = _merge_by_canonical_name(proj.units)
        buildings = _merge_by_canonical_name(proj.buildings)
        upgrades = _merge_by_canonical_name(proj.upgrades)
        powers = _merge_by_canonical_name(proj.powers)
        if (
            units is proj.units
            and buildings is proj.buildings
            and upgrades is proj.upgrades
            and powers is proj.powers
        ):
            return proj
        return replace(
            proj,
            units=units,
            unit_spent=_merge_by_canonical_name(proj.unit_spent),
            buildings=buildings,
            building_spent=_merge_by_canonical_name(proj.building_spent),
            upgrades=upgrades,
            upgrade_spent=_merge_by_canonical_name(proj.upgrade_spent),
            powers=powers,
        )

    return _map_projections(data, fix)


def _reconcile_unit_building_split(
    data: list[ProfileMatchData],
) -> list[ProfileMatchData]:
    """Fix cncstats' occasional unit/building misclassification.

    cncstats' per-player summary puts a small number of raw object names in
    the wrong dict some of the time - e.g. ``ChinaVehicleListeningOutpost``
    (a vehicle) shows up under ``BuildingsBuilt`` for a minority of its
    occurrences, which without this fix can make it a player's spurious
    "favorite building" (their real favorite unit, undercounted). For every
    object name seen in both dicts anywhere in the data, all its counts move
    to whichever dict holds the majority of its total builds. Objects that
    only ever appear in one dict are untouched (the common case).
    """
    unit_totals: dict[str, int] = defaultdict(int)
    building_totals: dict[str, int] = defaultdict(int)
    for match in data:
        for proj in match.players:
            for obj, count in proj.units.items():
                unit_totals[obj] += count
            for obj, count in proj.buildings.items():
                building_totals[obj] += count
    ambiguous = set(unit_totals) & set(building_totals)
    if not ambiguous:
        return data
    belongs_in_units = {
        obj for obj in ambiguous if unit_totals[obj] >= building_totals[obj]
    }

    def fix(proj: PlayerMatchProjection) -> PlayerMatchProjection:
        touched = ambiguous & (proj.units.keys() | proj.buildings.keys())
        if not touched:
            return proj
        units = dict(proj.units)
        buildings = dict(proj.buildings)
        unit_spent = dict(proj.unit_spent)
        building_spent = dict(proj.building_spent)
        for obj in touched:
            if obj in belongs_in_units:
                moved_count = buildings.pop(obj, 0)
                moved_spent = building_spent.pop(obj, 0)
                if moved_count:
                    units[obj] = units.get(obj, 0) + moved_count
                    unit_spent[obj] = unit_spent.get(obj, 0) + moved_spent
            else:
                moved_count = units.pop(obj, 0)
                moved_spent = unit_spent.pop(obj, 0)
                if moved_count:
                    buildings[obj] = buildings.get(obj, 0) + moved_count
                    building_spent[obj] = building_spent.get(obj, 0) + moved_spent
        return replace(
            proj,
            units=units,
            buildings=buildings,
            unit_spent=unit_spent,
            building_spent=building_spent,
        )

    return _map_projections(data, fix)


def _free_objects(
    data: list[ProfileMatchData],
    counts_of: Callable[[PlayerMatchProjection], dict[str, int]],
    spent_of: Callable[[PlayerMatchProjection], dict[str, int]],
) -> set[str]:
    """Raw object names with builds recorded but zero total spend across all of them."""
    total_count: dict[str, int] = defaultdict(int)
    total_spent: dict[str, int] = defaultdict(int)
    for match in data:
        for proj in match.players:
            for obj, count in counts_of(proj).items():
                total_count[obj] += count
            for obj, spent in spent_of(proj).items():
                total_spent[obj] += spent
    return {
        obj
        for obj, count in total_count.items()
        if count > 0 and total_spent.get(obj, 0) == 0
    }


def _without(d: dict[str, int], drop: set[str]) -> dict[str, int]:
    return {k: v for k, v in d.items() if k not in drop} if d.keys() & drop else d


def _drop_zero_cost_objects(data: list[ProfileMatchData]) -> list[ProfileMatchData]:
    """Drop objects that never cost anything, across every occurrence.

    Some raw cncstats object names are free, automatically-spawned artifacts
    rather than something the player chose to build - e.g. GLA Stealth's
    "Hole" tunnel-network exit points are logged with TotalSpent always 0,
    distinct from the real (paid) Tunnel Network building - and would
    otherwise surface as a spurious favorite/aversion. Units, buildings, and
    upgrades are checked independently; powers have no cost field and are
    unaffected. Run after :func:`_reconcile_unit_building_split` so counts
    and their paired spend have already settled into one category.
    """
    free_units = _free_objects(data, lambda p: p.units, lambda p: p.unit_spent)
    free_buildings = _free_objects(
        data, lambda p: p.buildings, lambda p: p.building_spent
    )
    free_upgrades = _free_objects(data, lambda p: p.upgrades, lambda p: p.upgrade_spent)
    if not (free_units or free_buildings or free_upgrades):
        return data

    def fix(proj: PlayerMatchProjection) -> PlayerMatchProjection:
        units = _without(proj.units, free_units)
        buildings = _without(proj.buildings, free_buildings)
        upgrades = _without(proj.upgrades, free_upgrades)
        if (
            units is proj.units
            and buildings is proj.buildings
            and upgrades is proj.upgrades
        ):
            return proj
        return replace(
            proj,
            units=units,
            unit_spent=_without(proj.unit_spent, free_units),
            buildings=buildings,
            building_spent=_without(proj.building_spent, free_buildings),
            upgrades=upgrades,
            upgrade_spent=_without(proj.upgrade_spent, free_upgrades),
        )

    return _map_projections(data, fix)


def _compute_academy_badges(
    academy_means: dict[str, dict[str, float]],
) -> dict[str, list[ProfileBadge]]:
    """Top-3 medal badges per academy stat: gold/silver/bronze by rank.

    Ranked by per-game rate among players who ever posted a nonzero rate for
    that stat; ties break alphabetically by name for determinism. A stat with
    fewer than 3 such players awards fewer medals (no bronze if only two
    people ever did the thing at all).
    """
    badges_by_player: dict[str, list[ProfileBadge]] = defaultdict(list)
    for field, meta in _ACADEMY_BADGES.items():
        candidates = sorted(
            ((name, m[field]) for name, m in academy_means.items() if m[field] > 0),
            key=lambda nv: (-nv[1], nv[0]),
        )
        for rank, (name, value) in enumerate(candidates[:3], start=1):
            badges_by_player[name].append(
                ProfileBadge(
                    key=field,
                    label=meta.label,
                    description=meta.description,
                    value=value,
                    rank=rank,
                    tier=_MEDAL_TIERS[rank - 1],
                    total_players=len(candidates),
                )
            )
    return dict(badges_by_player)


def compute_all_profiles(
    data: list[ProfileMatchData],
    *,
    min_profile_games: int = DEFAULT_MIN_PROFILE_GAMES,
) -> dict[str, PlayerProfileComputed]:
    """Batch-compute the persisted deep stats for every profiled player.

    Must always run over the full population: percentiles are relative to the
    other profiled players, so per-player recomputation would skew them.
    Favorites/aversions/percentiles all compare a player only against other
    *active* players (>= ``min_profile_games``) - an occasional guest's
    lopsided rate on a rarely-played general shouldn't set the peer bar a
    regular is judged against.
    """
    data = _merge_general_flavor_variants(data)
    data = _reconcile_unit_building_split(data)
    data = _drop_zero_cost_objects(data)
    projections_by_player: dict[str, list[PlayerMatchProjection]] = defaultdict(list)
    for match in data:
        for proj in match.players:
            projections_by_player[proj.name].append(proj)
    profiled = {
        name
        for name, projs in projections_by_player.items()
        if len(projs) >= min_profile_games
    }
    if not profiled:
        return {}

    active_data = [
        ProfileMatchData(
            match_id=match.match_id,
            players=[p for p in match.players if p.name in profiled],
        )
        for match in data
    ]
    favorites: dict[ObjectCategory, dict[str, ScoredObject]] = {}
    aversions: dict[ObjectCategory, dict[str, list[ScoredObject]]] = {}
    usage_rates: dict[ObjectCategory, dict[tuple[General, str], dict[str, float]]] = {}
    games_by_player_general: dict[tuple[str, General], int] = {}
    for category in ObjectCategory:
        agg = aggregate_category(active_data, category)
        # Games played per (player, general) don't depend on category (every
        # aggregate_category call counts the same match appearances), so this
        # only needs capturing once.
        if not games_by_player_general:
            games_by_player_general = agg.games
        # Shared between favorites/aversions below so each is computed once
        # per category rather than once per caller.
        peer_totals = _peer_totals(agg)
        usage_factions = _usage_faction_map(agg)
        min_count = 3 if category == ObjectCategory.POWERS else 5
        favorites[category] = compute_favorites(
            agg,
            category,
            min_count=min_count,
            peer_totals=peer_totals,
            usage_factions=usage_factions,
        )
        aversions[category] = compute_aversions(
            agg, category, peer_totals=peer_totals, usage_factions=usage_factions
        )
        # The full unit/building/upgrade breakdown - powers excluded (their
        # names are ability-based and read poorly outside a favorite/aversion
        # framing where clean_power_name already resolves that ambiguity).
        if category != ObjectCategory.POWERS:
            usage_rates[category] = _object_usage_rates(agg, category, usage_factions)

    # Per-player means for every percentile-ranked signal.
    apm_means: dict[str, float] = {}
    fb_rates: dict[str, float] = {}
    rank5_means: dict[str, float] = {}
    sw_built_rates: dict[str, float] = {}
    academy_means: dict[str, dict[str, float]] = {}
    for name in profiled:
        projs = projections_by_player[name]
        apms = [p.apm for p in projs if p.apm is not None]
        if len(apms) >= _MIN_SIGNAL_GAMES:
            apm_means[name] = sum(apms) / len(apms)
        fb_rates[name] = sum(1 for p in projs if p.got_first_blood) / len(projs)
        rank5s = [p.time_to_rank_5 for p in projs if p.time_to_rank_5 is not None]
        if len(rank5s) >= _MIN_SIGNAL_GAMES:
            rank5_means[name] = sum(rank5s) / len(rank5s)
        sw_built_rates[name] = sum(p.superweapons_built for p in projs) / len(projs)
        academies = [p.academy for p in projs if p.academy is not None]
        if len(academies) >= _MIN_SIGNAL_GAMES:
            academy_means[name] = {
                field: sum(getattr(a, field) for a in academies) / len(academies)
                for field in AcademyStats.model_fields
            }

    academy_badges = _compute_academy_badges(academy_means)
    computed_at = datetime.now(UTC).date()
    result: dict[str, PlayerProfileComputed] = {}
    for name in profiled:
        # The same object can qualify on several generals (e.g. a shared
        # faction unit); keep only the strongest instance per object name.
        best_by_object: dict[str, ScoredObject] = {}
        for category in ObjectCategory:
            for item in aversions[category].get(name, []):
                current = best_by_object.get(item.object_name)
                if current is None or item.score > current.score:
                    best_by_object[item.object_name] = item
        top_aversions = sorted(
            best_by_object.values(), key=lambda s: s.score, reverse=True
        )[:3]

        badges = sorted(academy_badges.get(name, []), key=lambda b: b.rank)

        my_apm = apm_means.get(name)
        my_rank5 = rank5_means.get(name)
        result[name] = PlayerProfileComputed(
            favorite_unit=_wire_or_none(favorites[ObjectCategory.UNITS].get(name)),
            favorite_building=_wire_or_none(
                favorites[ObjectCategory.BUILDINGS].get(name)
            ),
            favorite_upgrade=_wire_or_none(
                favorites[ObjectCategory.UPGRADES].get(name)
            ),
            favorite_power=_wire_or_none(favorites[ObjectCategory.POWERS].get(name)),
            aversions=[s.to_wire() for s in top_aversions],
            avg_apm=round(my_apm, 1) if my_apm is not None else None,
            apm_percentile=(
                _percentile(list(apm_means.values()), my_apm)
                if my_apm is not None
                else None
            ),
            first_blood_rate=round(fb_rates[name], 3),
            first_blood_percentile=_percentile(list(fb_rates.values()), fb_rates[name]),
            avg_time_to_rank_5=round(my_rank5, 2) if my_rank5 is not None else None,
            rank_5_percentile=(
                _percentile(
                    list(rank5_means.values()), my_rank5, higher_is_better=False
                )
                if my_rank5 is not None
                else None
            ),
            superweapons_built_per_game=round(sw_built_rates[name], 2),
            superweapon_percentile=_percentile(
                list(sw_built_rates.values()), sw_built_rates[name]
            ),
            badges=badges,
            object_usage=_player_object_usage(
                name, usage_rates, games_by_player_general
            ),
            games_analyzed=len(projections_by_player[name]),
            computed_at=computed_at,
        )
    return result


def _wire_or_none(scored: ScoredObject | None) -> FavoriteObject | None:
    return scored.to_wire() if scored is not None else None


# ---------------------------------------------------------------------------
# Live (MatchInfo-only) profile parts
# ---------------------------------------------------------------------------

_MIN_BEST_GENERAL_GAMES = 10
_MIN_BEST_MAP_GAMES = 5
_MIN_OPPONENT_MEETINGS = 10
_MIN_TEAMMATE_GAMES = 5


def compute_live_profile(
    games: list[MatchInfo],
    player: str,
    synergy_pairs: list[PairSynergy] | None = None,
) -> PlayerProfile:
    """The cheap MatchInfo-derived profile: W/L, generals, maps, people, tempo.

    ``player`` must already be canonical (the route's PlayerName type resolves
    aliases). ``computed`` is left None; the route attaches the persisted deep
    stats. ``synergy_pairs`` (from player_synergy.compute_player_synergy)
    picks the favorite teammate; without a qualifying pair we fall back to
    most games together.
    """
    wins = 0
    losses = 0
    general_wl: dict[General, list[int]] = defaultdict(lambda: [0, 0])
    map_wl: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    opponent_wl: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    teammate_games: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    win_durations: list[float] = []
    loss_durations: list[float] = []
    general_win_rate_points: dict[General, list[GeneralWinRatePoint]] = defaultdict(
        list
    )

    # Chronological order so the per-general running series below traces the
    # record as it actually evolved; every other aggregate here is
    # order-independent so sorting doesn't change them.
    for game in sorted(games, key=lambda g: g.timestamp):
        me = None
        for p in game.players:
            if p.team <= 0:
                continue
            if resolve_player_name(p.name, p.color) == player:
                me = p
                break
        # is_real matches the Player Stats page's W/L rule, so the profile
        # record and per-general numbers agree with that page.
        if me is None or not me.is_real():
            continue

        wins += me.won
        losses += not me.won
        wl = general_wl[me.general]
        wl[0 if me.won else 1] += 1
        total_on_general = wl[0] + wl[1]
        general_win_rate_points[me.general].append(
            GeneralWinRatePoint(
                date=game.date,
                game_number=total_on_general,
                wins=wl[0],
                losses=wl[1],
                win_rate=round(wl[0] / total_on_general, 3),
            )
        )
        map_name = map_basename(game.map)
        mwl = map_wl[map_name]
        mwl[0 if me.won else 1] += 1
        (win_durations if me.won else loss_durations).append(game.duration_minutes)

        for p in game.players:
            if p.team <= 0 or p is me:
                continue
            other = resolve_player_name(p.name, p.color)
            if other == player or other in _NON_HUMAN_PLAYERS or p.Type == "C":
                continue
            if p.team == me.team:
                tg = teammate_games[other]
                tg[0] += 1
                tg[1] += me.won
            else:
                owl = opponent_wl[other]
                owl[0 if me.won else 1] += 1

    def general_stat(general: General, wl: list[int]) -> GeneralProfileStat:
        total = wl[0] + wl[1]
        return GeneralProfileStat(
            general=general,
            games=total,
            wins=wl[0],
            losses=wl[1],
            win_rate=round(wl[0] / total, 3) if total else 0.0,
        )

    generals = sorted(
        (general_stat(g, wl) for g, wl in general_wl.items()),
        key=lambda s: s.games,
        reverse=True,
    )
    most_played_general = generals[0] if generals else None
    general_win_rate_over_time = sorted(
        (
            GeneralWinRateSeries(general=g, points=points)
            for g, points in general_win_rate_points.items()
        ),
        key=lambda s: len(s.points),
        reverse=True,
    )
    eligible_generals = [g for g in generals if g.games >= _MIN_BEST_GENERAL_GAMES]
    best_general = (
        max(eligible_generals, key=lambda s: (s.win_rate, s.games))
        if eligible_generals
        else None
    )

    def map_stat(name: str, wl: list[int]) -> MapProfileStat:
        return MapProfileStat(map=name, games=wl[0] + wl[1], wins=wl[0], losses=wl[1])

    maps = [map_stat(name, wl) for name, wl in map_wl.items()]
    favorite_map = max(maps, key=lambda m: m.games) if maps else None
    eligible_maps = [m for m in maps if m.games >= _MIN_BEST_MAP_GAMES]
    best_map = (
        max(eligible_maps, key=lambda m: (m.wins / m.games, m.games))
        if eligible_maps
        else None
    )

    def opponent_stat(name: str, wl: list[int]) -> OpponentProfileStat:
        return OpponentProfileStat(name=name, wins=wl[0], losses=wl[1])

    frequent_opponents = [
        opponent_stat(name, wl)
        for name, wl in opponent_wl.items()
        if wl[0] + wl[1] >= _MIN_OPPONENT_MEETINGS
    ]
    nemesis = (
        min(
            frequent_opponents,
            key=lambda o: (o.wins / (o.wins + o.losses), -(o.wins + o.losses)),
        )
        if frequent_opponents
        else None
    )
    favorite_victim = (
        max(
            frequent_opponents,
            key=lambda o: (o.wins / (o.wins + o.losses), o.wins + o.losses),
        )
        if frequent_opponents
        else None
    )

    favorite_teammate = _pick_favorite_teammate(player, teammate_games, synergy_pairs)

    return PlayerProfile(
        player=player,
        games=wins + losses,
        wins=wins,
        losses=losses,
        generals=generals,
        general_win_rate_over_time=general_win_rate_over_time,
        most_played_general=most_played_general,
        best_general=best_general,
        favorite_map=favorite_map,
        best_map=best_map,
        favorite_teammate=favorite_teammate,
        nemesis=nemesis,
        favorite_victim=favorite_victim,
        avg_win_duration_minutes=_round_or_none(_mean(win_durations)),
        avg_loss_duration_minutes=_round_or_none(_mean(loss_durations)),
        computed=None,
    )


def _round_or_none(value: float | None) -> float | None:
    return round(value, 1) if value is not None else None


def _pick_favorite_teammate(
    player: str,
    teammate_games: dict[str, list[int]],  # name -> [games together, wins together]
    synergy_pairs: list[PairSynergy] | None,
) -> TeammateProfileStat | None:
    """Best-synergy teammate when the synergy model has a qualifying pair,
    otherwise the most frequent teammate."""
    if synergy_pairs:
        mine = [p for p in synergy_pairs if player in (p.player_a, p.player_b)]
        if mine:
            best = max(mine, key=lambda p: p.synergy)
            other = best.player_b if best.player_a == player else best.player_a
            counts = teammate_games.get(
                other, [best.games_together, best.wins_together]
            )
            return TeammateProfileStat(
                name=other,
                games_together=counts[0],
                wins_together=counts[1],
                synergy=round(best.synergy, 3),
            )
    frequent = {
        name: counts
        for name, counts in teammate_games.items()
        if counts[0] >= _MIN_TEAMMATE_GAMES
    }
    if not frequent:
        return None
    name, counts = max(frequent.items(), key=lambda kv: (kv[1][0], kv[1][1]))
    return TeammateProfileStat(
        name=name, games_together=counts[0], wins_together=counts[1], synergy=None
    )
