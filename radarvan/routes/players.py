"""Player stats, ratings, skills, balance, partitioning endpoints."""

import threading
from collections import defaultdict
from datetime import date, timedelta
from enum import Enum

from cachetools import TTLCache
from pydantic import BaseModel

from fastapi import APIRouter, Depends, Query

from .. import (
    create_teams,
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
    PlayerRatingData,
    PlayerRatingDailyChange,
    PlayerSkill,
    PlayerStats,
    PlayerSynergy,
    RatingUpset,
)
from .. import queries
from ..cache import competitive_matches
from ..queries import players as query_players
from ..queries import (
    AllGames,
    CompetitiveGames,
    UnfilteredCompetitiveGames,
    WindowedCompetitiveGames,
)
from ..db_utils import ReplayManager
from ..dependencies import cache_short, get_replay_manager

router = APIRouter()


_TEAM_FORMATS = {"2v2", "3v3", "4v4"}

# Cap on how many (most recent) shared games get scanned for head-to-head
# value destroyed - see get_player_head_to_head's docstring.
_H2H_VALUE_WINDOW = 150


PlayerEnum = Enum(  # type: ignore[misc]
    "PlayerEnum", {v.upper(): v for v in player_ids.PLAYER_NAMES}, type=str
)


class SelectedPlayers(BaseModel):
    players: list[PlayerEnum] = []


@router.get("/api/playerstats", dependencies=[Depends(cache_short)])
def get_player_stats(
    games: AllGames,
    game_format: str | None = Query(None, description=queries.FORMAT_DESCRIPTION),
) -> PlayerStats:
    """Get player stats.

    `game_format` stays a parameter here rather than coming from the corpus
    dependency: `player_stats.get_player_stats` filters per game *category*
    internally, which is finer-grained than `filter_by_format`.
    """
    return player_stats.get_player_stats(games, game_format=game_format)


@router.get("/api/player_colors/", dependencies=[Depends(cache_short)])
def get_player_colors(games: AllGames) -> dict[str, str]:
    """Each player's most common actual in-game color, keyed by player name -
    used as their primary identity color in the UI (see PlayerChip)."""
    return player_stats.most_common_colors(games)


@router.get("/api/player_game_counts/team/", dependencies=[Depends(cache_short)])
def get_player_team_game_counts(games: AllGames) -> list[PlayerGameCount]:
    """Get player names with their total team game count, sorted by count descending."""
    stats = player_stats.get_player_stats(games)
    counts = [
        PlayerGameCount(
            name=stat.player_name,
            count=sum(stat.game_counts.get(fmt, 0) for fmt in _TEAM_FORMATS),
        )
        for stat in stats.player_stats
    ]
    return sorted(counts, key=lambda x: x.count, reverse=True)


@router.get("/api/player_game_counts/", dependencies=[Depends(cache_short)])
def get_player_game_counts(games: AllGames) -> list[PlayerGameCount]:
    """Get all player names with their total game count, sorted by count descending.

    Counts games *played*: spectating is not playing, and the sibling
    ``/api/player_team_game_counts/`` already counts competitors (via
    ``player_stats.get_player_stats``), so reading every slot here made the two
    endpoints answer the same question differently.
    """
    counts: dict[str, int] = {}
    for game in games:
        for player in game.roster().competitors:
            name = player_ids.resolve_player_name(player.name, player.color)
            counts[name] = counts.get(name, 0) + 1
    return [
        PlayerGameCount(name=name, count=count)
        for name, count in sorted(counts.items(), key=lambda x: x[1], reverse=True)
    ]


@router.get("/api/player_ratings/", dependencies=[Depends(cache_short)])
def get_player_ratings(game_list: WindowedCompetitiveGames) -> PlayerRatingData:
    """Ratings, rating history and recent form for every rated player."""
    return query_players.player_ratings_payload(game_list)


@router.get("/api/player_ratings/upsets/", dependencies=[Depends(cache_short)])
def get_rating_upsets(
    game_list: CompetitiveGames,
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
) -> list[RatingUpset]:
    """Upsets: games where the model's favored team lost.

    Sorted by surprise (the favorite's win-probability edge over the actual
    winner) descending. Optionally restricted to the last ``within_days`` days
    and to a ``min_surprise`` threshold; the top ``limit`` are returned.
    """
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
    game_list: CompetitiveGames,
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
) -> list[PlayerSynergy]:
    """Pairwise synergy: do two players win more/less as teammates than their ratings predict.

    Ridge logistic regression over team games with the rating model's log-odds as a
    fixed offset, player main effects, and pairwise interaction terms. Sorted by
    synergy descending. See ``SYNERGY_METHODOLOGY.md``.
    """
    pairs = player_synergy.compute_player_synergy(
        game_list,
        lambda_pair=regularization,
        lambda_main=main_regularization,
        min_games_together=min_games_together,
    )
    return [PlayerSynergy.model_validate(p) for p in pairs]


@router.get("/api/player_skills/", dependencies=[Depends(cache_short)])
def get_player_skills(game_list: CompetitiveGames) -> list[PlayerSkill]:
    """Alternative skill estimate via Whole-History Rating (Coulom 2008).

    Each player's skill is a function of time (one rating per date played) with a
    Gaussian random-walk prior on changes; team Bradley-Terry likelihood for outcomes.
    Returns each player's rating at their most recent game, mean-centered across players.
    """
    skills = player_skill.compute_player_skills(game_list)
    return [
        PlayerSkill(name=s.name, skill=s.skill, game_count=s.game_count) for s in skills
    ]


@router.get("/api/player_ratings/daily_changes/", dependencies=[Depends(cache_short)])
def get_player_rating_daily_changes(
    for_date: date,
    game_list: UnfilteredCompetitiveGames,
) -> list[PlayerRatingDailyChange]:
    """Return each player's ordinal rating change for the given date."""
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
    all_games: UnfilteredCompetitiveGames,
    game_format: str | None = Query(None, description=queries.FORMAT_DESCRIPTION),
) -> dict[str, dict[str, HeadToHead]]:
    """Win/loss record for every rated player against every other rated player."""
    game_list = matches.filter_by_format(all_games, game_format)

    # Rated players come from the *unfiltered* corpus on purpose: it is the same
    # argument every other ratings endpoint passes, so this shares their cached
    # derivation instead of forcing a second one per format.
    rated_players = {
        r.name for r in player_rating.compute_player_ratings(all_games).ratings
    }

    h2h: dict[str, dict[str, list[int]]] = defaultdict(
        lambda: defaultdict(lambda: [0, 0])
    )

    for game in game_list:
        teams: dict[int, list[tuple[str, bool]]] = defaultdict(list)
        for p in game.roster().participants:
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
async def get_player_head_to_head(
    player1: PlayerName,
    player2: PlayerName,
    game_list: CompetitiveGames,
) -> HeadToHeadDetail:
    """Detailed head-to-head record between two players (opposite-team games only).

    Considers competitive games where both players took part on *different* teams;
    the winner of each game is the side whose team won. Aggregates the overall
    record, each player's record by the general they piloted, and the record by
    map, plus the full game list (most recent first), and the value destroyed
    between them over their most recent shared games.
    """
    return await query_players.player_head_to_head_detail(game_list, player1, player2)


# A deliberately frozen answer, which is why it is a wall clock and not a
# derivation. `create_teams.balance_teams` is @derived(on=CORPUS): it follows the
# ratings, so on its own this endpoint would re-rank the splits every time a game
# landed. Some of the group want exactly that; the rest want the teams they were
# given at the start of the evening to still be the teams an hour later. This is
# where that call gets made, in the route that makes the promise - the derivation
# underneath stays honest about tracking the corpus.
#
# Six hours covers a game night. Allow-listed in tests/test_derived_registry.py
# for the same reason routes/draft.py is: a version token cannot express "hold
# this steady until the evening is over".
_BALANCE_HOLD = timedelta(hours=6)
_balance_cache: TTLCache[frozenset[str], dict[tuple[str, ...], float]] = TTLCache(
    maxsize=64, ttl=_BALANCE_HOLD.total_seconds()
)
_balance_cache_lock = threading.Lock()


@router.get("/api/balance_teams/")
def balance_teams(
    players: list[str] = Query(default=[]),
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> dict[str, float]:
    """Win probability for every way of splitting `players` into two teams.

    Held for six hours per roster: ask again with the same players and you get
    the same numbers back, even if games have landed in between. Change the
    roster and you get a fresh computation.
    """
    if len(players) < 4:
        return {}
    # Keyed on the *resolved* roster, so "skp" and "Skip" are one entry rather
    # than two. The raw spellings stay out of the cache and are re-applied per
    # request below, so the caller still sees the names they sent.
    resolved_to_raw = {player_ids.resolve_player_name(n): n for n in players}
    roster = frozenset(resolved_to_raw)

    # One lookup, not `in` + `[]`: an entry can expire between the two, which
    # would raise KeyError on a cache that just reported a hit.
    with _balance_cache_lock:
        team_scores = _balance_cache.get(roster)
    if team_scores is None:
        games = competitive_matches(replay_manager)
        team_scores = create_teams.balance_teams(
            list(games.values()), player_list=frozenset(players)
        )
        with _balance_cache_lock:
            _balance_cache[roster] = team_scores
    return {
        ",".join(resolved_to_raw.get(p, p) for p in team): score
        for team, score in team_scores.items()
    }


@router.get("/api/partition_teams/{team_size}")
def partition_teams(
    games: UnfilteredCompetitiveGames,
    team_size: int = 2,
    players: SelectedPlayers = Query(
        default_factory=lambda: SelectedPlayers(players=[])
    ),
) -> list[list[str]]:
    return create_teams.create_balanced_teams(
        games, player_list={str(p.value) for p in players.players}, team_size=team_size
    )
