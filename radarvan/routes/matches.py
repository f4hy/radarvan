"""Match listing, lookup, and match details endpoints."""

from collections import Counter
from datetime import date
import structlog
from typing import Any

from fastapi import APIRouter, Depends, Response

from ..api_types import MatchDetails, MatchInfo, Matches, Team
from ..cache import details_from_id, sorted_deduped_matches
from ..db_utils import ReplayManager
from ..dependencies import get_replay_manager

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


@router.get("/api/dates/")
def get_dates(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> dict[date, float]:
    replays = sorted_deduped_matches(replay_manager)
    dates = Counter(r.date for r in replays.values())
    return dict(sorted(dates.items(), reverse=True))


@router.get("/api/matches/{match_count}")
def get_matches(
    match_count: int,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> Matches:
    """Get listing of matches, up to a return count limit for paging."""
    replays = sorted_deduped_matches(replay_manager)
    return Matches(matches=replays.values())


@router.get("/api/matches/by_date/{date}")
def get_matches_by_date(
    date: date,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> Matches:
    """Get all matches for a specific date."""
    replays = sorted_deduped_matches(replay_manager)
    return Matches(matches=[r for r in replays.values() if r.date == date])


@router.get("/api/team_games_without_winner/")
def get_team_games_without_winner(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> list[dict[str, Any]]:
    """Return match IDs and dates for team games with no winner (winning_team=0)."""
    all_matches = sorted_deduped_matches(replay_manager)
    games_with_no_winner = [
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
    return games_with_no_winner


@router.get("/api/match/{match_id}")
def get_match_by_id(
    match_id: int,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> MatchInfo | None:
    """Get a single match by its ID."""
    return sorted_deduped_matches(replay_manager).get(match_id)


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
    response.headers["Cache-Control"] = "public, max-age=3600"
    return details
