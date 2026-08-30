"""Match listing, lookup, and match details endpoints."""

from collections import Counter
from datetime import date
import structlog
from typing import Any

from fastapi import APIRouter, Depends, Query, Response

from .. import durations as durations_module
from .. import match_narrative
from ..api_types import (
    BuildOrder,
    DurationDistribution,
    MatchDetails,
    MatchInfo,
    MatchNarrative,
    Matches,
    PlayerName,
    Team,
)
from ..cache import details_from_id, sorted_deduped_matches
from ..db_utils import ReplayManager
from ..dependencies import cache_short, get_replay_manager
from ..matches import filter_matches
from ..queries import CompetitiveGames

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["matches"])


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
    player: PlayerName | None = None,
    map_name: str | None = None,
    game_format: str | None = None,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> dict[date, float]:
    """Every game night we have matches for, with how many were played.

    The three optional filters narrow which matches are counted, so a filtered
    request returns only the nights that still have one and a count of what
    survived. They are the same three that ``/api/matches/by_date`` takes, on
    purpose: the Matches page sends its filter set to both, which is what keeps
    a night's headline count equal to the number of matches it expands to.
    """
    replays = filter_matches(
        list(sorted_deduped_matches(replay_manager).values()),
        player=player,
        map_name=map_name,
        game_format=game_format,
    )
    dates = Counter(r.date for r in replays)
    return dict(sorted(dates.items(), reverse=True))


@router.get("/api/matches/by_date/{date}", dependencies=[Depends(cache_short)])
def get_matches_by_date(
    date: date,
    exclude_dev: bool = False,
    player: PlayerName | None = None,
    map_name: str | None = None,
    game_format: str | None = None,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> Matches:
    """Get all matches for a specific date.

    When exclude_dev is set, matches sourced from a "dev-" zulu build are omitted.
    The player/map/format filters match ``/api/dates`` - see the note there.
    """
    replays = sorted_deduped_matches(replay_manager)
    return Matches(
        matches=filter_matches(
            [
                r
                for r in replays.values()
                if r.date == date and not (exclude_dev and r.is_dev)
            ],
            player=player,
            map_name=map_name,
            game_format=game_format,
        )
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


@router.get("/api/match/{match_id}", dependencies=[Depends(cache_short)])
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
    return match


@router.get("/api/details/{match_id}", dependencies=[Depends(cache_short)])
def get_match_details(
    match_id: int,
    response: Response,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> MatchDetails:
    """Get details about a particular match.

    Result is cached in-process (see cache.details_from_id, invalidated on
    reparse/upload). Short browser hold only - a reparse or a WinnerOverride
    rewrites these details behind an unchanged URL. An unparsed match returns
    empty and is not cached, so it picks up data once processed.
    """
    details = details_from_id(match_id, replay_manager)
    if details is None:
        response.headers["Cache-Control"] = "no-cache"
        return empty_match_details(match_id)
    return details


@router.get("/api/build_orders/{match_id}", dependencies=[Depends(cache_short)])
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
    return details.build_orders


@router.get("/api/narrative/{match_id}", dependencies=[Depends(cache_short)])
def get_match_narrative(
    match_id: int,
    response: Response,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> MatchNarrative:
    """The match retold as an ordered list of beats.

    A projection of the cached ``MatchDetails`` (see ``match_narrative``), so
    it shares the durable, versioned details cache and runs no extra
    computation - the same arrangement as ``get_build_orders`` above. Entirely
    deterministic: no model call, identical on every request.

    A match that isn't in the corpus returns an empty narrative uncached; one
    whose replay hasn't been parsed yet returns the headline with no beats, and
    picks up the rest once details exist.
    """
    match = sorted_deduped_matches(replay_manager).get(match_id)
    if match is None:
        response.headers["Cache-Control"] = "no-cache"
        return MatchNarrative(match_id=match_id, headline="", beats=[])
    details = details_from_id(match_id, replay_manager)
    if details is None:
        response.headers["Cache-Control"] = "no-cache"
    return match_narrative.build_narrative(match, details)


@router.get("/api/duration_distribution/", dependencies=[Depends(cache_short)])
def get_duration_distribution(
    games: CompetitiveGames,
    bucket_minutes: float = Query(
        durations_module.DEFAULT_BUCKET_MINUTES,
        ge=0.5,
        le=30.0,
        description="Width of each histogram bar, in minutes",
    ),
    max_minutes: float = Query(
        durations_module.DEFAULT_MAX_MINUTES,
        ge=10.0,
        le=360.0,
        description="Games at or beyond this land in the overflow bar",
    ),
) -> DurationDistribution:
    """How long our games run: a histogram plus per-format order statistics.

    Computed over the competitive corpus, so it excludes comp-stomps and
    unfinished games - a disconnect at minute two is not a two-minute game, and
    a spike of them in the first bar would hide the real distribution. The
    ``game_format`` filter comes with the corpus dependency.
    """
    return durations_module.duration_distribution(games, bucket_minutes, max_minutes)
