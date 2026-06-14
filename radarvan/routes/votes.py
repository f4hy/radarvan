"""Map voting: per-player-count votes and vetoes.

Like the auth routes, these are cookie/identity-driven and deliberately not
behind the X-API-Key dependency — the frontend calls them same-origin so the
session cookie identifies the voter. Reads are open; casting requires login.
"""

import threading
from datetime import UTC, datetime

import structlog
from cachetools import LRUCache, cached
from fastapi import APIRouter, Depends, HTTPException

from .. import map_choice
from ..api_types import (
    ChooseMapRequest,
    ChooseMapResult,
    MapVoteOption,
    MapVotePage,
    SetMapVoteRequest,
)
from ..cache import latest_match_ts, maps_by_player_count, sorted_deduped_matches
from ..db import User
from ..db_utils import ReplayManager
from ..dependencies import (
    get_current_user,
    get_map_vote_repo,
    get_replay_manager,
    get_user_repo,
    require_current_user,
)
from ..replay_files import map_basename
from ..repositories import MapVoteRepo, UserRepo, VoteLimitExceeded
from ..repositories.maps import normalize_map_name
from ..repositories.votes import VETO_LIMIT, VOTE_LIMIT

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/map_vote", tags=["map_vote"])


def _norm(map_name: str) -> str:
    """Normalize a map name/path to a key that joins match history to MapData.

    Match history stores a map_path (e.g. ``maps/foo/foo.map``); MapData stores
    a canonical name. Strip the path, the ``.map`` suffix, whitespace, and case.
    """
    base = map_basename(map_name).removesuffix(".map")
    return normalize_map_name(base)


_play_stats_lock = threading.Lock()


@cached(cache=LRUCache(maxsize=2), key=latest_match_ts, lock=_play_stats_lock)
def _map_play_stats(
    replay_manager: ReplayManager,
) -> dict[str, tuple[int, datetime]]:
    """{normalized map -> (total games, last-played timestamp)} across all games.

    Cached on the latest-match timestamp (same key as the match caches), so it
    only recomputes when new matches land — not on every vote read/write.
    """
    stats: dict[str, tuple[int, datetime]] = {}
    for match in sorted_deduped_matches(replay_manager).values():
        key = _norm(match.map)
        count, last = stats.get(key, (0, match.timestamp))
        stats[key] = (count + 1, max(last, match.timestamp))
    return stats


def _build_page(
    player_count: int,
    replay_manager: ReplayManager,
    vote_repo: MapVoteRepo,
    user: User | None,
) -> MapVotePage:
    map_names = maps_by_player_count(replay_manager).get(player_count, [])
    play_stats = _map_play_stats(replay_manager)
    choices = vote_repo.get_choices(user.id, player_count) if user is not None else {}
    now = datetime.now(UTC)

    options: list[MapVoteOption] = []
    for name in map_names:
        count, last = play_stats.get(_norm(name), (0, None))
        days = (now - last).days if last is not None else None
        options.append(
            MapVoteOption(
                map_name=name,
                game_count=count,
                last_played=last,
                days_since_last_played=days,
                my_choice=choices.get(name),
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
    """Player counts (map capacities) that have at least one known map."""
    grouped = maps_by_player_count(replay_manager)
    return sorted(count for count, maps in grouped.items() if count > 0 and maps)


@router.get("/players")
def voting_players(
    user_repo: UserRepo = Depends(get_user_repo),
) -> list[str]:
    """In-game names with an account — the selectable participants for a draw."""
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
    map_names = maps_by_player_count(replay_manager).get(player_count, [])
    if req.map_name not in map_names:
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
    vote_repo: MapVoteRepo = Depends(get_map_vote_repo),
    user_repo: UserRepo = Depends(get_user_repo),
) -> ChooseMapResult:
    """Run the authoritative weighted-random draw for this player count.

    Only the votes of the players in ``req.players`` are counted, so the draw
    reflects who's actually playing. Returns the chosen map plus every
    voted/vetoed map (with tallies) for the frontend's reveal + spin.
    """
    # req.players are alias-resolved at validation (PlayerName annotated type).
    user_ids = user_repo.ids_for_player_names(req.players)
    tally = vote_repo.tally(player_count, user_ids)
    return map_choice.choose_map(player_count, tally)
