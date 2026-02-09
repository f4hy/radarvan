from cachetools import TTLCache, cached
from itertools import combinations, permutations
from openskill.models import PlackettLuce
from collections import defaultdict
from . import player_ids
from radarvan.api_types import (
    MatchDetails,
    Team,
    Matches,
    MatchInfo,
    PlayerStats,
    GeneralStats,
    SpentOverTime,
    WinnerOverride,
    GameRecord,
    TournamentResult,
    ReplayFileSchema,
    ParsedReplayJsonSchema,
    TournamentReport,
)
import logging

logger = logging.getLogger(__name__)


# players = {
#     # Experienced players - higher mu, lower sigma (more certain)
#     "Alice": Rating(mu=30, sigma=5),  # Known strong player
#     "Bob": Rating(mu=28, sigma=6),  # Known good player
#     # Average/unknown players - default
#     "Charlie": model.rating(),  # mu=25, sigma=8.333 (default)
#     # Beginners - lower mu, higher sigma (uncertain but probably weak)
#     "David": Rating(mu=15, sigma=10),  # Complete beginner
#     "Eve": Rating(mu=18, sigma=9),  # Played a few times
# }
# def initialize_player(experience_level):
#     """
#     experience_level: 'beginner', 'casual', 'average', 'experienced', 'expert'
#     """
#     priors = {
#         "beginner": Rating(mu=15, sigma=10),
#         "casual": Rating(mu=20, sigma=8),
#         "average": Rating(mu=25, sigma=8.333),  # default
#         "experienced": Rating(mu=30, sigma=6),
#         "expert": Rating(mu=35, sigma=5),
#     }
#     return priors.get(experience_level, Rating())  # default if not found


# # Usage
# player_info = {
#     "Alice": "expert",
#     "Bob": "experienced",
#     "Charlie": "average",
#     "David": "beginner",
# }

# players = {name: initialize_player(level) for name, level in player_info.items()}


def initialize_player(name, model):
    """
    experience_level: 'beginner', 'casual', 'average', 'experienced', 'expert'
    """

    beginners = {"EnragedFerret", "Neo"}
    casual = {"CPU"}
    # experienced = {"Gorn", "Tytan"}
    experienced = {}

    if name in beginners:
        return model.rating(name=name, mu=15, sigma=12)
    if name in casual:
        return model.rating(name=name, mu=20, sigma=10)
    if name in experienced:
        return model.rating(name=name, mu=30, sigma=6)

    return model.rating(name=name)


@cached(cache={})
def get_model() -> PlackettLuce:
    return PlackettLuce()


def compute_player_ratings(games: list[MatchInfo]):
    model = get_model()

    all_players = {
        player_ids.player_name_map(p.name) for game in games for p in game.players
    }
    game_counts = {p: 0 for p in all_players}

    players = {name: initialize_player(name, model) for name in all_players}
    logger.info(f"players: {players}")

    # Process games
    for game in games:
        teams = defaultdict(list)
        actual_players = [p for p in game.players if p.team > 0]
        if sum((1 if p.name == "HardArmy" else 0) for p in actual_players) > 1:
            continue
        if len(actual_players) < 3:
            continue
        logger.info(f"game: {game.id} players {game.players}")
        for player in actual_players:
            teams[player.team].append(player_ids.player_name_map(player.name))
            game_counts[player_ids.player_name_map(player.name)] += 1
        if len(teams) != 2:
            continue

        scores = {t: 1 if game.winning_team == t else 0 for t in teams.keys()}
        pteams = [[players.get(p) for p in team] for team in teams.values()]
        logger.info(f"Teams: {pteams} scores:{scores}")
        new_ratings = model.rate(pteams, scores=list(scores.values()))
        for t in new_ratings:
            for p in t:
                players[p.name] = p

    ratings = [r for r in players.values() if game_counts.get(r.name, 0) > 3]
    sorted_ratings = sorted(ratings, key=lambda x: x.ordinal(), reverse=True)
    # Display results
    for rating in sorted_ratings:
        if game_counts.get(rating.name) < 5:
            continue
        print(
            f"{rating.name}[games={game_counts.get(rating.name)}]: {rating.ordinal():.1f} (μ={rating.mu:.1f}, σ={rating.sigma:.1f})"
        )

    return sorted_ratings


def balance_teams(games: list[MatchInfo], player_list: set[str]):
    team_size = len(player_list) // 2
    ratings = compute_player_ratings(games)

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
