"""Map voting: per-player-count votes and vetoes.

Like the auth routes, these are cookie/identity-driven and deliberately not
behind the X-API-Key dependency - the frontend calls them same-origin so the
session cookie identifies the voter. Reads are open; casting requires login.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import structlog
from fastapi import APIRouter, Depends, HTTPException

from .. import map_choice
from .. import missing_maps
from ..api_types import (
    ChooseMapRequest,
    ChooseMapResult,
    MapVoteOption,
    MapVotePage,
    SetMapVoteRequest,
)
from ..cache import maps_by_player_count, sorted_deduped_matches
from ..derived import CORPUS, derived
from ..db import User
from ..db_utils import ReplayManager
from ..dependencies import (
    get_current_user,
    get_map_vote_repo,
    get_replay_manager,
    get_user_repo,
    require_current_user,
)
from ..replay_files import map_basename, map_key
from ..repositories import MapVoteRepo, UserRepo, VoteLimitExceeded
from ..repositories.votes import VETO_LIMIT, VOTE_LIMIT

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/map_vote", tags=["map_vote"])


@dataclass
class _MapAgg:
    """Per-map aggregate backing the voting list."""

    display_name: str
    game_count: int = 0
    last_played: datetime | None = None
    # Player counts this map is associated with: distinct real-player counts seen
    # in games on it, plus its MapData start-position count when geometry exists.
    counts: set[int] = field(default_factory=set)


@derived(on=CORPUS, maxsize=1)
def _match_map_index(replay_manager: ReplayManager) -> dict[str, _MapAgg]:
    """{normalized map -> aggregate} over every map in match history.

    The voting list is sourced from games we've actually played (not just maps
    with parsed MapData geometry), so a played map appears even if its geometry
    was never fetched. Keyed on CORPUS.
    """
    index: dict[str, _MapAgg] = {}
    for match in sorted_deduped_matches(replay_manager).values():
        key = map_key(match.map)
        agg = index.get(key)
        if agg is None:
            agg = _MapAgg(display_name=map_basename(match.map).removesuffix(".map"))
            index[key] = agg
        agg.game_count += 1
        if agg.last_played is None or match.timestamp > agg.last_played:
            agg.last_played = match.timestamp
        real_players = len(match.roster().participants)
        if real_players > 0:
            agg.counts.add(real_players)
    return index


def _merged_maps(replay_manager: ReplayManager) -> dict[str, _MapAgg]:
    """Played maps merged with MapData capacities.

    Match history is the source of truth for which maps appear; MapData adds the
    authoritative start-position count and canonical name when geometry exists.
    Returns fresh copies so the cached match index is never mutated.
    """
    merged: dict[str, _MapAgg] = {
        key: _MapAgg(agg.display_name, agg.game_count, agg.last_played, set(agg.counts))
        for key, agg in _match_map_index(replay_manager).items()
    }
    for start_count, names in maps_by_player_count(replay_manager).items():
        for name in names:
            key = map_key(name)
            agg = merged.get(key)
            if agg is None:
                agg = _MapAgg(display_name=name)
                merged[key] = agg
            else:
                # Prefer the canonical MapData name for display/votes/image lookup.
                agg.display_name = name
            if start_count > 0:
                agg.counts.add(start_count)
    return merged


# Maps played within this window are penalized in the draw (RECENT_PLAY_PENALTY).
_RECENT_PLAY_WINDOW = timedelta(hours=24)


def _recently_played_maps(replay_manager: ReplayManager) -> set[str]:
    """Display names of maps last played within the recency window.

    Keyed to match the draw tally (vote map names == the page's display names).
    """
    cutoff = datetime.now(UTC) - _RECENT_PLAY_WINDOW
    return {
        agg.display_name
        for agg in _merged_maps(replay_manager).values()
        if agg.last_played is not None and agg.last_played >= cutoff
    }


def _build_page(
    player_count: int,
    replay_manager: ReplayManager,
    vote_repo: MapVoteRepo,
    user: User | None,
) -> MapVotePage:
    choices = vote_repo.get_choices(user.id, player_count) if user is not None else {}
    now = datetime.now(UTC)

    options: list[MapVoteOption] = []
    for agg in _merged_maps(replay_manager).values():
        if player_count not in agg.counts:
            continue
        last = agg.last_played
        days = (now - last).days if last is not None else None
        options.append(
            MapVoteOption(
                map_name=agg.display_name,
                game_count=agg.game_count,
                last_played=last,
                days_since_last_played=days,
                my_choice=choices.get(agg.display_name),
            )
        )
    options.sort(key=lambda o: (-o.game_count, o.map_name))

    return MapVotePage(
        player_count=player_count,
        logged_in=user is not None,
        vote_limit=VOTE_LIMIT,
        veto_limit=VETO_LIMIT,
        votes_used=sum(1 for c in choices.values() if c == "vote"),
        vetoes_used=sum(1 for c in choices.values() if c == "veto"),
        maps=options,
    )


@router.get("/player_counts")
def player_counts(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> list[int]:
    """Player counts we have maps for (real players seen in games + MapData capacities)."""
    counts: set[int] = set()
    for agg in _merged_maps(replay_manager).values():
        counts |= agg.counts
    return sorted(c for c in counts if c > 0)


@router.get("/players")
def voting_players(
    user_repo: UserRepo = Depends(get_user_repo),
) -> list[str]:
    """In-game names with an account - the selectable participants for a draw."""
    return user_repo.list_claimed_player_names()


@router.get("/{player_count}", response_model=MapVotePage)
def get_vote_page(
    player_count: int,
    replay_manager: ReplayManager = Depends(get_replay_manager),
    vote_repo: MapVoteRepo = Depends(get_map_vote_repo),
    user: User | None = Depends(get_current_user),
) -> MapVotePage:
    """Maps for a player count (ordered by total games) plus the viewer's picks."""
    return _build_page(player_count, replay_manager, vote_repo, user)


@router.post("/{player_count}", response_model=MapVotePage)
def set_vote(
    player_count: int,
    req: SetMapVoteRequest,
    replay_manager: ReplayManager = Depends(get_replay_manager),
    vote_repo: MapVoteRepo = Depends(get_map_vote_repo),
    user: User = Depends(require_current_user),
) -> MapVotePage:
    """Cast/clear a vote or veto for a map (requires login)."""
    valid_maps = {
        agg.display_name
        for agg in _merged_maps(replay_manager).values()
        if player_count in agg.counts
    }
    if req.map_name not in valid_maps:
        raise HTTPException(status_code=400, detail="Unknown map for this player count")
    try:
        vote_repo.set_choice(user.id, player_count, req.map_name, req.choice)
    except VoteLimitExceeded as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return _build_page(player_count, replay_manager, vote_repo, user)


@router.post("/{player_count}/choose", response_model=ChooseMapResult)
def choose_map(
    player_count: int,
    req: ChooseMapRequest,
    replay_manager: ReplayManager = Depends(get_replay_manager),
    vote_repo: MapVoteRepo = Depends(get_map_vote_repo),
    user_repo: UserRepo = Depends(get_user_repo),
) -> ChooseMapResult:
    """Run the authoritative weighted-random draw for this player count.

    Only the votes of the players in ``req.players`` are counted, so the draw
    reflects who's actually playing. Returns the chosen map (with its CRC, when
    stored) plus every voted/vetoed map (with tallies) for the reveal + spin.
    """
    # req.players are alias-resolved at validation (PlayerName annotated type).
    user_ids = user_repo.ids_for_player_names(req.players)
    tally = vote_repo.tally(player_count, user_ids)
    recent = _recently_played_maps(replay_manager)
    result = map_choice.choose_map(player_count, tally, recent_maps=recent)
    if result.chosen_map is not None:
        # Stored CRC if we have it, else derive from a replay or the hosted map file.
        crc = missing_maps.crc_for_map(result.chosen_map, replay_manager)
        if crc is not None:
            result = result.model_copy(update={"chosen_map_crc": crc})
    return result
