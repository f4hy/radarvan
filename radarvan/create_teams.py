from itertools import combinations
from openskill.models import PlackettLuceRating
from . import player_ids
from radarvan.api_types import (
    MatchInfo,
)
import logging

logger = logging.getLogger(__name__)

from .player_rating import get_model, compute_player_ratings


def balance_teams(games: list[MatchInfo], player_list: set[str]):
    team_size = len(player_list) // 2
    ratings = compute_player_ratings(games).ratings

    player_ratings = {r.name: r for r in ratings}

    model = get_model()
    day_players = [player_ids.player_name_map(n) for n in player_list]
    team_win_pct = {}
    for team1 in combinations(day_players, team_size):
        if tuple(team1) in team_win_pct:
            continue
        team2 = [p for p in day_players if p not in team1]
        team1_ratings = [player_ratings.get(p) for p in team1]
        team2_ratings = [player_ratings.get(p) for p in team2]
        win1_prop, win2_prop = model.predict_win([team1_ratings, team2_ratings])
        logger.info(f"Team1 {team1} team2{team2} {win1_prop} {win2_prop}")
        if win1_prop >= 0.5:
            team_win_pct[tuple(team1)] = win1_prop
        if win2_prop >= 0.5:
            team_win_pct[tuple(team2)] = win2_prop
    logger.info(f"Team win probs {team_win_pct}")
    return dict(sorted(team_win_pct.items(), key=lambda x: x[1]))


def partition_into_teams(players: list[str], team_size: int):
    """
    Generate all possible ways to partition players into teams.

    Args:
        players: List of (name, Rating) tuples
        team_size: Size of each team

    Yields:
        Each possible partition as a list of teams
    """
    n = len(players)
    num_teams = n // team_size

    if n % team_size != 0:
        raise ValueError(f"Cannot divide {n} players into teams of {team_size}")

    def partition_recursive(remaining, current_partition, teams_formed):
        if teams_formed == num_teams:
            yield current_partition
            return

        # We need to form teams_left teams from players_left players
        # To avoid duplicates, only consider combinations where the first
        # remaining player is in the team
        first_player = remaining[0]

        # Choose team_size-1 more players from the rest
        for team_members in combinations(remaining[1:], team_size - 1):
            team = [first_player] + list(team_members)
            new_remaining = [p for p in remaining if p not in team]

            yield from partition_recursive(
                new_remaining, current_partition + [team], teams_formed + 1
            )

    yield from partition_recursive(players, [], 0)


def create_balanced_teams(
    games: list[MatchInfo], player_list: set[str], team_size: int = 2
):
    ratings = compute_player_ratings(games).ratings

    player_ratings = {r.name: r for r in ratings}

    team_configs = dict(enumerate(partition_into_teams(player_list, team_size)))

    config_rating = {
        id: rate_team_partition(team_config, player_ratings)
        for id, team_config in team_configs.items()
    }

    best, score = min(config_rating.items(), key=lambda x: x[1])

    return team_configs[best]


def rate_team_partition(
    teams: list[list[str]], ratings: dict[str, PlackettLuceRating]
) -> float:
    model = get_model()
    loss = 0.0
    for matchup in combinations(teams, 2):
        team1, team2 = matchup
        ratings1 = [ratings.get(p) for p in team1]
        ratings2 = [ratings.get(p) for p in team2]
        win1_prob, _win2_prob = model.predict_win([ratings1, ratings2])
        loss += (0.5 - win1_prob) ** 2
    return loss
