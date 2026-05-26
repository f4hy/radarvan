"""Player stats, ratings, skills, balance, partitioning endpoints."""

from collections import defaultdict
from datetime import date, timedelta
from enum import Enum

from pydantic import BaseModel

from fastapi import APIRouter, Depends, Query

from .. import (
    create_teams,
    matches,
    player_ids,
    player_rating,
    player_skill,
    player_stats,
)
from ..api_types import (
    HeadToHead,
    PlayerGameCount,
    PlayerRatings,
    PlayerRatingData,
    PlayerRatingDailyChange,
    PlayerSkill,
    PlayerStats,
    ShortPlayerRating,
)
from ..cache import competitive_matches, sorted_deduped_matches
from ..db_utils import ReplayManager
from ..dependencies import cache_short, get_replay_manager

router = APIRouter()


_TEAM_FORMATS = {"2v2", "3v3", "4v4"}


PlayerEnum = Enum(  # type: ignore[misc]
    "PlayerEnum", {v.upper(): v for v in player_ids.PLAYER_NAMES}, type=str
)


class SelectedPlayers(BaseModel):
    players: list[PlayerEnum] = []


@router.get("/api/playerstats", dependencies=[Depends(cache_short)])
def get_player_stats(
    game_format: str | None = Query(
        None, description="Filter by game format: 1v1, 2v2, 3v3, 4v4"
    ),
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> PlayerStats:
    """Get player stats."""
    all_games = sorted_deduped_matches(replay_manager)
    return player_stats.get_player_stats(
        list(all_games.values()), game_format=game_format
    )


@router.get("/api/player_game_counts/team/", dependencies=[Depends(cache_short)])
def get_player_team_game_counts(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> list[PlayerGameCount]:
    """Get player names with their total team game count, sorted by count descending."""
    all_games = sorted_deduped_matches(replay_manager)
    stats = player_stats.get_player_stats(list(all_games.values()))
    counts = [
        PlayerGameCount(
            name=stat.player_name,
            count=sum(stat.game_counts.get(fmt, 0) for fmt in _TEAM_FORMATS),
        )
        for stat in stats.player_stats
    ]
    return sorted(counts, key=lambda x: x.count, reverse=True)


@router.get("/api/player_game_counts/", dependencies=[Depends(cache_short)])
def get_player_game_counts(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> list[PlayerGameCount]:
    """Get all player names with their total game count, sorted by count descending."""
    all_matches = sorted_deduped_matches(replay_manager)
    counts: dict[str, int] = {}
    for game in all_matches.values():
        for player in game.players:
            name = player_ids.resolve_player_name(player.name, player.color)
            counts[name] = counts.get(name, 0) + 1
    return [
        PlayerGameCount(name=name, count=count)
        for name, count in sorted(counts.items(), key=lambda x: x[1], reverse=True)
    ]


@router.get("/api/player_ratings/", dependencies=[Depends(cache_short)])
def get_player_ratings(
    game_format: str | None = Query(
        None, description="Filter by game format: 2v2, 3v3, 4v4"
    ),
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> PlayerRatingData:
    games = competitive_matches(replay_manager)
    game_list = matches.filter_by_format(list(games.values()), game_format)

    ratings_and_counts = player_rating.compute_player_ratings(game_list)
    counts = ratings_and_counts.game_counts

    today = date.today()
    seven_days_ago = today - timedelta(days=7)
    fourteen_days_ago = today - timedelta(days=14)
    thirty_days_ago = today - timedelta(days=30)

    cutoffs = [(7, seven_days_ago), (14, fourteen_days_ago), (30, thirty_days_ago)]

    def convert(rating: player_rating.NamedRating) -> PlayerRatings:
        deltas: dict[int, float] = {7: 0.0, 14: 0.0, 30: 0.0}
        for c in ratings_and_counts.daily_changes.get(rating.name, []):
            for days, cutoff in cutoffs:
                if c.date >= cutoff:
                    deltas[days] += c.delta
        return PlayerRatings(
            name=rating.name,
            ordinal=rating.ordinal(),
            mu=rating.mu,
            sigma=rating.sigma,
            atdate=rating.at_date,
            game_count=counts.get(rating.name),
            recent_deltas={k: v for k, v in deltas.items() if v != 0},
            high_ordinal=ratings_and_counts.ordinal_high.get(rating.name),
            low_ordinal=ratings_and_counts.ordinal_low.get(rating.name),
        )

    def convert_short(rating: player_rating.NamedRating) -> ShortPlayerRating:
        return ShortPlayerRating(
            mu=rating.mu,
            sigma=rating.sigma,
            atdate=rating.at_date,
        )

    player_results: dict[str, list[bool]] = defaultdict(list)
    for game in sorted(game_list, key=lambda g: g.timestamp):
        for p in game.players:
            if p.team <= 0:
                continue
            player_results[player_ids.resolve_player_name(p.name, p.color)].append(
                p.won
            )
    rated_names = {r.name for r in ratings_and_counts.ratings}
    player_form = {
        name: results[-10:]
        for name, results in player_results.items()
        if name in rated_names
    }

    converted = [convert(r) for r in ratings_and_counts.ratings]
    over_time = {
        name: [convert_short(r) for r in ratings]
        for name, ratings in ratings_and_counts.over_time.items()
    }
    return PlayerRatingData(
        player_rating=converted,
        player_rating_overtime=over_time,
        player_form=player_form,
    )


@router.get("/api/player_skills/", dependencies=[Depends(cache_short)])
def get_player_skills(
    game_format: str | None = Query(
        None, description="Filter by game format: 1v1, 2v2, 3v3, 4v4"
    ),
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> list[PlayerSkill]:
    """Alternative skill estimate via Whole-History Rating (Coulom 2008).

    Each player's skill is a function of time (one rating per date played) with a
    Gaussian random-walk prior on changes; team Bradley-Terry likelihood for outcomes.
    Returns each player's rating at their most recent game, mean-centered across players.
    """
    games = competitive_matches(replay_manager)
    game_list = matches.filter_by_format(list(games.values()), game_format)
    skills = player_skill.compute_player_skills(game_list)
    return [
        PlayerSkill(name=s.name, skill=s.skill, game_count=s.game_count) for s in skills
    ]


@router.get("/api/player_ratings/daily_changes/", dependencies=[Depends(cache_short)])
def get_player_rating_daily_changes(
    for_date: date,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> list[PlayerRatingDailyChange]:
    """Return each player's ordinal rating change for the given date."""
    game_list = list(competitive_matches(replay_manager).values())
    ratings_and_counts = player_rating.compute_player_ratings(game_list)
    result = []
    for name, changes in ratings_and_counts.daily_changes.items():
        for change in changes:
            if change.date == for_date:
                result.append(PlayerRatingDailyChange(name=name, delta=change.delta))
                break
    return result


@router.get("/api/player_ratings/head_to_head/", dependencies=[Depends(cache_short)])
def get_head_to_head(
    game_format: str | None = Query(None),
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> dict[str, dict[str, HeadToHead]]:
    """Win/loss record for every rated player against every other rated player."""
    all_games = list(competitive_matches(replay_manager).values())
    game_list = matches.filter_by_format(all_games, game_format)

    # Use unfiltered games for rated_players so the cache key matches other endpoints.
    rated_players = {
        r.name for r in player_rating.compute_player_ratings(all_games).ratings
    }

    h2h: dict[str, dict[str, list[int]]] = defaultdict(
        lambda: defaultdict(lambda: [0, 0])
    )

    for game in game_list:
        teams: dict[int, list[tuple[str, bool]]] = defaultdict(list)
        for p in game.players:
            if p.team <= 0:
                continue
            name = player_ids.resolve_player_name(p.name, p.color)
            if name not in rated_players:
                continue
            teams[p.team].append((name, p.won))

        team_list = list(teams.values())
        if len(team_list) != 2:
            continue

        for name1, won1 in team_list[0]:
            for name2, _ in team_list[1]:
                if won1:
                    h2h[name1][name2][0] += 1
                    h2h[name2][name1][1] += 1
                else:
                    h2h[name1][name2][1] += 1
                    h2h[name2][name1][0] += 1

    return {
        name: {
            opp: HeadToHead(wins=wl[0], losses=wl[1]) for opp, wl in opponents.items()
        }
        for name, opponents in h2h.items()
        if name in rated_players
    }


@router.get("/api/balance_teams/")
def balance_teams(
    players: list[str] = Query(default=[]),
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> dict[str, float]:
    if len(players) < 4:
        return {}
    resolved_to_raw = {player_ids.resolve_player_name(n): n for n in players}
    games = competitive_matches(replay_manager)

    team_scores = create_teams.balance_teams(
        list(games.values()), player_list=set(players)
    )
    return {
        ",".join(resolved_to_raw.get(p, p) for p in team): score
        for team, score in team_scores.items()
    }


@router.get("/api/partition_teams/{team_size}")
def partition_teams(
    team_size: int = 2,
    players: SelectedPlayers = Query(default=SelectedPlayers(players=[])),
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> list[list[str]]:
    games = list(competitive_matches(replay_manager).values())
    teams = create_teams.create_balanced_teams(
        games, player_list={str(p.value) for p in players.players}, team_size=team_size
    )

    return teams
