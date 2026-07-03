"""Player stats, ratings, skills, balance, partitioning endpoints."""

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from enum import Enum

from pydantic import BaseModel

from fastapi import APIRouter, Depends, Query

from .. import (
    create_teams,
    head_to_head,
    matches,
    player_ids,
    player_rating,
    player_skill,
    player_stats,
    player_synergy,
)
from ..api_types import (
    HeadToHead,
    HeadToHeadDetail,
    PlayerGameCount,
    PlayerName,
    PlayerRatings,
    PlayerRatingData,
    PlayerRatingDailyChange,
    PlayerSkill,
    PlayerStats,
    PlayerSynergy,
    RatingUpset,
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
    months_back: int | None = Query(
        None,
        ge=1,
        description="Only use matches from the last N months to compute ratings",
    ),
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> PlayerRatingData:
    games = competitive_matches(replay_manager)
    game_list = matches.filter_by_format(list(games.values()), game_format)
    game_list = matches.filter_by_months_back(game_list, months_back)

    ratings_and_counts = player_rating.compute_player_ratings(game_list)
    counts = ratings_and_counts.game_counts

    today = datetime.now(UTC).date()
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


@router.get("/api/player_ratings/upsets/", dependencies=[Depends(cache_short)])
def get_rating_upsets(
    limit: int = Query(20, ge=1, le=200, description="Number of top upsets to return"),
    within_days: int | None = Query(
        None, ge=1, description="Only include upsets from the last N days"
    ),
    min_surprise: float = Query(
        0.0,
        ge=0.0,
        le=1.0,
        description="Only include upsets with at least this surprise (0-1)",
    ),
    game_format: str | None = Query(
        None, description="Filter by game format: 2v2, 3v3, 4v4"
    ),
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> list[RatingUpset]:
    """Upsets: games where the model's favored team lost.

    Sorted by surprise (the favorite's win-probability edge over the actual
    winner) descending. Optionally restricted to the last ``within_days`` days
    and to a ``min_surprise`` threshold; the top ``limit`` are returned.
    """
    games = competitive_matches(replay_manager)
    game_list = matches.filter_by_format(list(games.values()), game_format)
    ratings_and_counts = player_rating.compute_player_ratings(game_list)
    upsets = matches.filter_since(
        ratings_and_counts.upsets, within_days, key=lambda u: u.at_date
    )
    if min_surprise > 0.0:
        upsets = [u for u in upsets if u.surprise >= min_surprise]
    return [
        RatingUpset(
            match_id=u.match_id,
            atdate=u.at_date,
            favored_team=u.favored_team,
            favored_players=u.favored_players,
            favored_win_prob=u.favored_win_prob,
            winning_team=u.winning_team,
            winner_players=u.winner_players,
            winner_win_prob=u.winner_win_prob,
            surprise=u.surprise,
        )
        for u in upsets[:limit]
    ]


@router.get("/api/player_ratings/synergy/", dependencies=[Depends(cache_short)])
def get_player_synergy(
    game_format: str | None = Query(
        None, description="Filter by game format: 2v2, 3v3, 4v4"
    ),
    min_games_together: int = Query(
        player_synergy.DEFAULT_MIN_GAMES_TOGETHER,
        ge=1,
        description="Only return pairs that have played at least this many games together",
    ),
    regularization: float = Query(
        player_synergy.DEFAULT_LAMBDA_PAIR,
        gt=0.0,
        description="L2 shrinkage for pair synergy; higher = more conservative",
    ),
    main_regularization: float = Query(
        player_synergy.DEFAULT_LAMBDA_MAIN,
        gt=0.0,
        description="L2 shrinkage for per-player main effects; raise to stop strong "
        "players' main effects running away and saturating pair synergy",
    ),
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> list[PlayerSynergy]:
    """Pairwise synergy: do two players win more/less as teammates than their ratings predict.

    Ridge logistic regression over team games with the rating model's log-odds as a
    fixed offset, player main effects, and pairwise interaction terms. Sorted by
    synergy descending. See ``SYNERGY_METHODOLOGY.md``.
    """
    games = competitive_matches(replay_manager)
    game_list = matches.filter_by_format(list(games.values()), game_format)
    pairs = player_synergy.compute_player_synergy(
        game_list,
        lambda_pair=regularization,
        lambda_main=main_regularization,
        min_games_together=min_games_together,
    )
    return [PlayerSynergy.model_validate(p) for p in pairs]


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


@router.get("/api/player_head_to_head/", dependencies=[Depends(cache_short)])
def get_player_head_to_head(
    player1: PlayerName,
    player2: PlayerName,
    game_format: str | None = Query(
        None, description="Filter by game format: 1v1, 2v2, 3v3, 4v4"
    ),
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> HeadToHeadDetail:
    """Detailed head-to-head record between two players (opposite-team games only).

    Considers competitive games where both players took part on *different* teams;
    the winner of each game is the side whose team won. Aggregates the overall
    record, each player's record by the general they piloted, and the record by
    map, plus the full game list (most recent first).
    """
    games = list(competitive_matches(replay_manager).values())
    game_list = matches.filter_by_format(games, game_format)
    return head_to_head.compute_head_to_head(game_list, player1, player2)


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
        list(games.values()), player_list=frozenset(players)
    )
    return {
        ",".join(resolved_to_raw.get(p, p) for p in team): score
        for team, score in team_scores.items()
    }


@router.get("/api/partition_teams/{team_size}")
def partition_teams(
    team_size: int = 2,
    players: SelectedPlayers = Query(
        default_factory=lambda: SelectedPlayers(players=[])
    ),
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> list[list[str]]:
    games = list(competitive_matches(replay_manager).values())
    return create_teams.create_balanced_teams(
        games, player_list={str(p.value) for p in players.players}, team_size=team_size
    )
