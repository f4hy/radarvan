"""Match listing, lookup, and match details endpoints."""

from collections import Counter
from datetime import date
import structlog
from typing import Any

from fastapi import APIRouter, Depends, Response

from ..api_types import BuildOrder, MatchDetails, MatchInfo, Matches, Team
from ..cache import details_from_id, sorted_deduped_matches
from ..db_utils import ReplayManager
from ..dependencies import cache_short, get_replay_manager

logger = structlog.get_logger(__name__)

router = APIRouter()


def empty_match_details(match_id: int) -> MatchDetails:
    return MatchDetails(
        match_id=match_id,
        costs=[],
        apms=[],
        upgrade_events={},
        money_values={},
        money_collected_values={},
        stats_data={},
        player_summary=[],
    )


@router.get("/api/dates/", dependencies=[Depends(cache_short)])
def get_dates(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> dict[date, float]:
    replays = sorted_deduped_matches(replay_manager)
    dates = Counter(r.date for r in replays.values())
    return dict(sorted(dates.items(), reverse=True))


@router.get("/api/matches/by_date/{date}", dependencies=[Depends(cache_short)])
def get_matches_by_date(
    date: date,
    exclude_dev: bool = False,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> Matches:
    """Get all matches for a specific date.

    When exclude_dev is set, matches sourced from a "dev-" zulu build are omitted.
    """
    replays = sorted_deduped_matches(replay_manager)
    return Matches(
        matches=[
            r
            for r in replays.values()
            if r.date == date and not (exclude_dev and r.is_dev)
        ]
    )


@router.get("/api/team_games_without_winner/", dependencies=[Depends(cache_short)])
def get_team_games_without_winner(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> list[dict[str, Any]]:
    """Return match IDs and dates for team games with no winner (winning_team=0)."""
    all_matches = sorted_deduped_matches(replay_manager)
    return [
        {"match_id": m.id, "date": m.date}
        for m in all_matches.values()
        if m.composition is not None
        and m.composition.is_team_game
        and m.composition.num_teams == 2
        and m.composition.num_humans > 2
        and m.winning_team == Team.NONE
        and (
            m.incomplete == ""
            or m.incomplete is None
            or "no team" in m.incomplete.lower()
        )
    ]


@router.get("/api/match/{match_id}")
def get_match_by_id(
    match_id: int,
    response: Response,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> MatchInfo | None:
    """Get a single match by its ID."""
    match = sorted_deduped_matches(replay_manager).get(match_id)
    if match is None:
        response.headers["Cache-Control"] = "no-cache"
        return None
    response.headers["Cache-Control"] = "private, max-age=3600"
    return match


@router.get("/api/details/{match_id}")
def get_match_details(
    match_id: int,
    response: Response,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> MatchDetails:
    """Get details about a particular match.

    Result is cached in-process (see cache.details_from_id, invalidated on
    reparse/upload). Existing details are immutable until reparse, so we also
    let the browser cache them; an unparsed match returns empty and is not
    cached so it picks up data once processed.
    """
    details = details_from_id(match_id, replay_manager)
    if details is None:
        response.headers["Cache-Control"] = "no-cache"
        return empty_match_details(match_id)
    response.headers["Cache-Control"] = "private, max-age=3600"
    return details


@router.get("/api/build_orders/{match_id}")
def get_build_orders(
    match_id: int,
    response: Response,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> dict[str, BuildOrder]:
    """Per-player build orders for a match (the same data the match details page shows).

    Keyed by player name; each value has the player's first-10 buildings, units,
    and upgrades in chronological order. Projected from the cached MatchDetails
    (see cache.details_from_id), so it shares the durable, versioned details
    cache and runs no extra computation. An unparsed match returns {} uncached
    so it picks up data once processed.
    """
    details = details_from_id(match_id, replay_manager)
    if details is None:
        response.headers["Cache-Control"] = "no-cache"
        return {}
    response.headers["Cache-Control"] = "private, max-age=3600"
    return details.build_orders
