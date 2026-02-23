from dataclasses import dataclass
from cachetools import cached
from openskill.models import PlackettLuce, PlackettLuceRating
from collections import defaultdict
from . import player_ids
from radarvan.api_types import (
    MatchInfo,
)
import logging

logger = logging.getLogger(__name__)


@dataclass
class NamedRating:
    """Wrapper around PlackettLuceRating where name is guaranteed to be str."""

    name: str
    mu: float
    sigma: float

    def ordinal(self) -> float:
        return self.mu - 3 * self.sigma

    def to_rating(self, model: PlackettLuce) -> PlackettLuceRating:
        return model.rating(name=self.name, mu=self.mu, sigma=self.sigma)


def initialize_player(name: str, model: PlackettLuce) -> NamedRating:
    """
    experience_level: 'beginner', 'casual', 'average', 'experienced', 'expert'
    """
    compters = {"CPU", "HardArmy"}
    beginners = {"EnragedFerret"}
    # casual = {"Neo"}
    casual: set[str] = set()
    experienced: set[str] = set()
    expert = {"[OoE]Excal^"}

    if name in beginners:
        return NamedRating(name=name, mu=5, sigma=12)
    if name in compters:
        return NamedRating(name=name, mu=10, sigma=6)
    if name in casual:
        return NamedRating(name=name, mu=15, sigma=6)
    if name in experienced:
        return NamedRating(name=name, mu=30, sigma=10)
    if name in expert:
        return NamedRating(name=name, mu=40, sigma=10)

    r = model.rating(name=name)
    return NamedRating(name=name, mu=r.mu, sigma=r.sigma)


@cached(cache={})
def get_model() -> PlackettLuce:
    # return PlackettLuce(beta=(25.0/3.0), tau=(25.0 / 200.0))
    return PlackettLuce(beta=(25.0 / 3.0))


@dataclass
class RatingsAndCounts:
    ratings: list[NamedRating]
    game_counts: dict[str, int]


def compute_player_ratings(games: list[MatchInfo]) -> RatingsAndCounts:
    model = get_model()

    all_players = {
        player_ids.player_name_map(p.name) for game in games for p in game.players
    }
    game_counts = dict.fromkeys(all_players, 0)

    players = {name: initialize_player(name, model) for name in all_players}
    logger.info(f"players: {players}")

    # Process games
    for game in games:
        teams = defaultdict(list)
        actual_players = [p for p in game.players if p.team > 0]
        if sum((1 if p.Type == "Cpu" else 0) for p in actual_players) > 1:
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
        pteams = [
            [players[p].to_rating(model) for p in team] for team in teams.values()
        ]
        logger.info(f"Teams: {pteams} scores:{scores}")
        new_ratings = model.rate(teams=pteams, scores=list(scores.values()))
        for t in new_ratings:
            for p in t:
                if p.name is not None:
                    players[p.name] = NamedRating(name=p.name, mu=p.mu, sigma=p.sigma)

    ratings = [r for r in players.values() if game_counts.get(r.name, 0) > 10]
    sorted_ratings = sorted(ratings, key=lambda x: x.ordinal(), reverse=True)
    # Display results
    for rating in sorted_ratings:
        if game_counts.get(rating.name, 0) < 5:
            continue
        print(
            f"{rating.name}[games={game_counts.get(rating.name)}]: {rating.ordinal():.1f} (μ={rating.mu:.1f}, σ={rating.sigma:.1f})"
        )

    return RatingsAndCounts(ratings=sorted_ratings, game_counts=game_counts)
