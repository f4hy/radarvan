"""Top-level MatchDetails orchestration.

Builds the wire-shape `MatchDetails` returned by `/api/details/{match_id}` by
pulling together the per-concern extractors:

- APM / APM-over-time → `radarvan.apm`
- time-series + first-blood → `radarvan.stats_extraction`
- per-player build order → `radarvan.build_order`
- timeline markers → `radarvan.timeline_events`
- generals-power picks & activations → `radarvan.powers`
- rank-5 / search-and-destroy timings → `radarvan.stats_extraction`

Also owns the body-stream upgrade extraction (`events_from_replay`),
per-player kill/loss aggregation, and the DB-bound loaders.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections import defaultdict

from .api_types import (
    AcademyStats,
    KillEventOutput,
    MapEventOutput,
    MatchDetails,
    ObjectSummary as APIObjectSummary,
    PlayerSummary as APIPlayerSummary,
    UpgradeEvent,
    Upgrades,
)
from .apm import apm_over_time, apms_from_replay
from .build_order import build_order_from_replay
from .cncstats_model.zhreplay import EnhancedReplayV2
from .db_utils import DatabaseManager, ReplayManager
from .replay_helpers import clean_object_name
from .stats_extraction import (
    milestone_timings_from_replay,
    stats_data_from_replay,
)
from .powers import powers_from_replay
from .timeline_events import timeline_events_from_replay
from .game_composition import MatchRoster
from .utils import minutes_per_step
import structlog

logger = structlog.get_logger(__name__)


# Bump this when the *logic* of match_details_from_replay (or any extractor it
# calls) changes the output WITHOUT changing the MatchDetails schema - e.g.
# extracting more data into an existing field, or fixing a computation. Schema
# changes (new/renamed/retyped fields) are caught automatically by the
# model_json_schema hash below, so you do NOT need to bump this for those.
# v2: APM no longer explodes for players with a near-zero active window
# (apm.py:_MIN_ACTIVE_MINUTES) - invalidates rows cached with the old garbage.
# v3: apm_over_time now uses 10s windows (was 1-min) scaled to an APM rate.
# v4: body-path APM no longer counts periodic "Checksum" engine heartbeats as
# player actions (the _NON_ACTIONS exclusion had a typo, "Chunksum").
# v5: money/money_earned/money_spent time series drop rows identical to the
# previous kept row (stats_extraction._drop_redundant_consecutive) - same
# data, fewer wire entries.
# v6: player_summary excludes spectators. The old `s.team == Team.OBSERVER`
# test only caught the few whose summary team was -1, so cached rows carry
# observer entries with empty stats.
# v7: timeline_events emits hunted / unhunted markers and MatchDetails gained
# time_to_hunted (cncstats statsVersion 3 added stats.huntedEvents).
_DETAILS_LOGIC_VERSION = 7


def _compute_details_version() -> str:
    """Stable id for the current MatchDetails *definition* + derivation logic.

    The schema hash auto-invalidates persisted rows whenever the MatchDetails
    shape changes; the logic-version prefix lets us force-invalidate on
    behavior changes that don't touch the shape. Computed once at import - the
    schema is fixed for the life of the process.
    """
    schema_json = json.dumps(MatchDetails.model_json_schema(), sort_keys=True)
    schema_hash = hashlib.sha256(schema_json.encode()).hexdigest()[:12]
    return f"{_DETAILS_LOGIC_VERSION}-{schema_hash}"


DETAILS_VERSION = _compute_details_version()


def events_from_replay(replay: EnhancedReplayV2) -> dict[str, Upgrades]:
    scale = minutes_per_step(replay)
    player_index_to_name: dict[int, str] = {
        i: p.name for i, p in enumerate(replay.header.metadata.players)
    }

    upgrades: dict[str, list[UpgradeEvent]] = {
        name: [] for name in player_index_to_name.values()
    }
    for chunk in replay.body:
        if not chunk.order_name.startswith("BuildUpgrade"):
            continue
        if not chunk.details:
            continue
        details = chunk.details if isinstance(chunk.details, dict) else {}
        detail_name = details.get("Name") or details.get("name") or ""
        detail_cost = details.get("Cost") or details.get("cost") or 0
        event = UpgradeEvent(
            player_name=chunk.player_name,
            timecode=chunk.time_code,
            upgrade_name=detail_name.removeprefix("Upgrade_"),
            cost=detail_cost or 0,
            at_minute=chunk.time_code * scale,
        )
        # setdefault, not [..]: the body's player names come from the order
        # stream, and a name the header never listed would otherwise raise a
        # KeyError that takes the whole MatchDetails computation down.
        upgrades.setdefault(chunk.player_name, []).append(event)

    return {name: Upgrades(upgrades=values) for name, values in upgrades.items()}


def _to_obj_map(
    by_player: dict[str, dict[str, list[int]]],
) -> dict[str, dict[str, APIObjectSummary]]:
    return {
        name: {
            u: APIObjectSummary(Count=d[0], TotalSpent=d[1]) for u, d in units.items()
        }
        for name, units in by_player.items()
    }


def api_player_summaries(
    replay: EnhancedReplayV2,
    units_destroyed: dict[str, dict[str, APIObjectSummary]] | None = None,
    buildings_destroyed: dict[str, dict[str, APIObjectSummary]] | None = None,
    units_lost: dict[str, dict[str, APIObjectSummary]] | None = None,
    buildings_lost: dict[str, dict[str, APIObjectSummary]] | None = None,
) -> list[APIPlayerSummary]:
    color_map = {p.name: p.color for p in replay.header.metadata.players}
    # Classify from the header, the same authority every other observer check
    # uses - the summary's own team field carries 0 for most spectators, so a
    # Team.OBSERVER test here silently let them through. Matched by name
    # because summary order is not header order (see CLAUDE.md); spectator
    # header slots always carry a name, unlike AI slots.
    observer_names = {
        s.name
        for s in MatchRoster.from_header_players(
            replay.header.metadata.players
        ).observers
        if s.name
    }
    player_summaries: list[APIPlayerSummary] = []
    for s in replay.summary:
        if s.name in observer_names:
            continue
        color = (color_map.get(s.name, "") or "black").lower().replace("color", "")
        academy = (
            AcademyStats.model_validate(s.academy.model_dump())
            if s.academy is not None
            else None
        )
        player_summaries.append(
            APIPlayerSummary(
                Name=s.name,
                Side=s.side,
                Team=s.team,
                Win=s.win,
                Color=color,
                UnitsCreated={
                    k: APIObjectSummary(Count=v.count, TotalSpent=v.total_spent)
                    for k, v in s.units_created.items()
                },
                BuildingsBuilt={
                    k: APIObjectSummary(Count=v.count, TotalSpent=v.total_spent)
                    for k, v in s.buildings_built.items()
                },
                UpgradesBuilt={
                    k: APIObjectSummary(Count=v.count, TotalSpent=v.total_spent)
                    for k, v in s.upgrades_built.items()
                },
                PowersUsed=s.powers_used,
                UnitsDestroyed=(units_destroyed or {}).get(s.name, {}),
                BuildingsDestroyed=(buildings_destroyed or {}).get(s.name, {}),
                UnitsLost=(units_lost or {}).get(s.name, {}),
                BuildingsLost=(buildings_lost or {}).get(s.name, {}),
                Academy=academy,
            )
        )
    return player_summaries


def load_match_details(
    match_id: int, replay_manager: ReplayManager
) -> MatchDetails | None:
    """Resolve MatchDetails for one match through the durable, versioned DB cache.

    On a cache hit at the current DETAILS_VERSION we return the small persisted
    projection without re-reading or re-validating the multi-MB S3 replay. On a
    miss we recompute from the S3 JSON and write the result back, so every
    caller (the /api/details + /api/build_orders endpoints via
    `cache.details_from_id`, and the superlatives / bulk loaders here) shares
    one warm cache. Returns None if the match isn't found.
    """
    from . import replay_files

    cached = replay_manager.get_cached_details(match_id, DETAILS_VERSION)
    if cached is not None:
        return cached
    rep = replay_manager.get_replay_json_by_match_id(match_id)
    if rep is None:
        return None
    replay = replay_files.parse_replay(rep.replay_file_url, replay_manager)
    details = match_details_from_replay(replay)
    if details is not None:
        replay_manager.save_cached_details(match_id, details, DETAILS_VERSION)
    return details


def load_match_details_threadsafe(
    match_id: int, db_manager: DatabaseManager
) -> MatchDetails | None:
    """Load match details with a fresh session - safe to call from any thread."""
    from .db_utils import ReplayManager as _ReplayManager

    try:
        with db_manager.get_session() as session:
            return load_match_details(match_id, _ReplayManager(session))
    except Exception:
        logger.exception("failed to load match details", match_id=match_id)
        return None


async def load_many_match_details(
    match_ids: list[int], db_manager: DatabaseManager, max_concurrent: int = 20
) -> list[MatchDetails]:
    """Load match details for many matches in parallel with bounded concurrency."""
    semaphore = asyncio.Semaphore(max_concurrent)

    async def _bounded(match_id: int) -> MatchDetails | None:
        async with semaphore:
            return await asyncio.to_thread(
                load_match_details_threadsafe, match_id, db_manager
            )

    results = await asyncio.gather(*[_bounded(mid) for mid in match_ids])
    return [r for r in results if r is not None]


def load_kill_data_batch_threadsafe(
    match_ids: list[int], db_manager: DatabaseManager
) -> dict[int, tuple[list[KillEventOutput], list[APIPlayerSummary]]]:
    """Load kill_events + player_summary for many matches in one DB round trip.

    Far cheaper than load_many_match_details when a caller only needs those
    two fields across many matches (e.g. head_to_head's
    value_destroyed_by_match, which can span hundreds of matches for a
    long-running matchup): skips validating build_orders/apm_over_time/
    timeline_events/stats_data/etc., and - more importantly, since the DB here
    is a remote RDS instance - batches into a single query instead of one
    round trip per match. Matches with no cached details row are silently
    omitted rather than falling back to a full per-match recompute.
    """
    from .db_utils import ReplayManager as _ReplayManager

    try:
        with db_manager.get_session() as session:
            rm = _ReplayManager(session)
            rows = rm.get_cached_kill_data_rows(match_ids, DETAILS_VERSION)
    except Exception:
        logger.exception("failed to load kill data batch", match_count=len(match_ids))
        return {}

    result: dict[int, tuple[list[KillEventOutput], list[APIPlayerSummary]]] = {}
    for match_id, (raw_kill_events, raw_player_summary) in rows.items():
        result[match_id] = (
            [KillEventOutput.model_validate(k) for k in raw_kill_events],
            [APIPlayerSummary.model_validate(p) for p in raw_player_summary],
        )
    return result


async def load_many_kill_data(
    match_ids: list[int], db_manager: DatabaseManager
) -> dict[int, tuple[list[KillEventOutput], list[APIPlayerSummary]]]:
    """Async wrapper around load_kill_data_batch_threadsafe (one query, run
    off the event loop)."""
    return await asyncio.to_thread(
        load_kill_data_batch_threadsafe, match_ids, db_manager
    )


def match_details_from_replay(replay: EnhancedReplayV2) -> MatchDetails | None:
    apms = apms_from_replay(replay)
    stats_data = stats_data_from_replay(replay)
    if stats_data:
        first_blood = (
            stats_data.first_blood.model_dump() if stats_data.first_blood else None
        )
        building_first_blood = (
            stats_data.building_first_blood.model_dump()
            if stats_data.building_first_blood
            else None
        )
    else:
        first_blood = None
        building_first_blood = None
    upgrades = events_from_replay(replay)
    name_by_idx: dict[int, str] = {}
    player_money_spent: dict[str, int] = {}
    player_money_collected: dict[str, int] = {}
    for p in replay.summary:
        name_by_idx[p.index] = p.name
        player_money_spent[p.name] = p.money_spent
        player_money_collected[p.name] = p.money_earned
    scale = minutes_per_step(replay)
    unit_cost: dict[str, int] = {}
    for bev in replay.stats.build_events if replay.stats else []:
        if bev.object not in unit_cost and bev.cost > 0:
            unit_cost[bev.object] = bev.cost

    kill_events: list[KillEventOutput] = []
    ud_by_player: dict[str, dict[str, list[int]]] = defaultdict(
        lambda: defaultdict(lambda: [0, 0])
    )
    bd_by_player: dict[str, dict[str, list[int]]] = defaultdict(
        lambda: defaultdict(lambda: [0, 0])
    )
    ul_by_player: dict[str, dict[str, list[int]]] = defaultdict(
        lambda: defaultdict(lambda: [0, 0])
    )
    bl_by_player: dict[str, dict[str, list[int]]] = defaultdict(
        lambda: defaultdict(lambda: [0, 0])
    )
    for kev in replay.stats.kill_events if replay.stats else []:
        killer_name = name_by_idx.get(kev.killer_player, "unk")
        victim_name = name_by_idx.get(kev.victim_player, "unk")
        cost = unit_cost.get(kev.victim, 0)
        kill_events.append(
            KillEventOutput(
                at_minute=kev.frame * scale,
                killer_player=killer_name,
                victim_player=victim_name,
                x=kev.x,
                y=kev.y,
                killer=kev.killer,
                victim=kev.victim,
                damage_type=kev.damage_type,
                value=cost,
            )
        )
        is_bldg = kev.victim_type == "structure"
        if killer_name != "unk":
            dest = bd_by_player if is_bldg else ud_by_player
            dest[killer_name][kev.victim][0] += 1
            dest[killer_name][kev.victim][1] += cost
        if victim_name != "unk":
            lost = bl_by_player if is_bldg else ul_by_player
            lost[victim_name][kev.victim][0] += 1
            lost[victim_name][kev.victim][1] += cost

    # Map-positioned events for the replay-playback view: structures appearing
    # (builds) and changing hands (captures). Units are intentionally excluded -
    # they would flood the map and we only want the base-development picture.
    map_events: list[MapEventOutput] = []
    if replay.stats:
        for bev in replay.stats.build_events:
            if bev.object_type != "structure":
                continue
            pname = name_by_idx.get(bev.player)
            if pname is None:
                continue
            map_events.append(
                MapEventOutput(
                    at_minute=bev.frame * scale,
                    x=bev.x,
                    y=bev.y,
                    player_name=pname,
                    kind="build",
                    name=clean_object_name(bev.object),
                )
            )
        for cev in replay.stats.capture_events:
            pname = name_by_idx.get(cev.new_owner)
            if pname is None:
                continue
            map_events.append(
                MapEventOutput(
                    at_minute=cev.frame * scale,
                    x=cev.x,
                    y=cev.y,
                    player_name=pname,
                    kind="capture",
                    name=clean_object_name(cev.object),
                )
            )
    map_events.sort(key=lambda e: e.at_minute)

    milestones = milestone_timings_from_replay(replay, name_by_idx)
    build_orders = build_order_from_replay(replay, name_by_idx, upgrades)
    timeline_events = timeline_events_from_replay(replay, upgrades, name_by_idx)

    hdr = replay.header
    return MatchDetails(
        match_id=replay.replay_id,
        game_version=hdr.version,
        map_name=hdr.metadata.map_path,
        costs=[],
        apms=apms,
        upgrade_events=upgrades,
        stats_data=stats_data.stats_data.model_dump() if stats_data else {},
        income_by_source=stats_data.income_by_source if stats_data else {},
        player_money_spent=player_money_spent,
        player_money_collected=player_money_collected,
        first_blood=first_blood,
        building_first_blood=building_first_blood,
        player_summary=api_player_summaries(
            replay,
            units_destroyed=_to_obj_map(ud_by_player),
            buildings_destroyed=_to_obj_map(bd_by_player),
            units_lost=_to_obj_map(ul_by_player),
            buildings_lost=_to_obj_map(bl_by_player),
        ),
        kill_events=kill_events,
        map_events=map_events,
        time_to_rank_5=milestones.time_to_rank_5,
        time_to_search_destroy=milestones.time_to_search_destroy,
        time_to_hunted=milestones.time_to_hunted,
        build_orders=build_orders,
        apm_over_time=apm_over_time(replay),
        timeline_events=timeline_events,
        powers=powers_from_replay(replay),
    )
