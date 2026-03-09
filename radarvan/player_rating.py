from dataclasses import dataclass
from cachetools import cached
from openskill.models import PlackettLuce, PlackettLuceRating
from collections import defaultdict
from . import player_ids
from . import game_composition
from radarvan.api_types import (
    MatchInfo,
)
from datetime import date
import logging

logger = logging.getLogger(__name__)


@dataclass
class NamedRating:
    """Wrapper around PlackettLuceRating where name is guaranteed to be str."""

    name: str
    mu: float
    sigma: float
    at_date: date | None = None

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
    experienced: set[str] = {"WildCard", "Tytan", "Gorn"}
    expert = {"[OoE]Excal^"}

    if name in beginners:
        return NamedRating(name=name, mu=5, sigma=12)
    if name in compters:
        return NamedRating(name=name, mu=10, sigma=6)
    if name in casual:
        return NamedRating(name=name, mu=15, sigma=6)
    if name in experienced:
        return NamedRating(name=name, mu=30, sigma=15)
    if name in expert:
        return NamedRating(name=name, mu=40, sigma=10)

    r = model.rating(name=name)
    return NamedRating(name=name, mu=r.mu, sigma=r.sigma)


@cached(cache={})
def get_model() -> PlackettLuce:
    # return PlackettLuce(beta=(25.0/3.0), tau=(25.0 / 200.0))
    return PlackettLuce(beta=(25.0 / 4.0))


@dataclass
class RatingsAndCounts:
    ratings: list[NamedRating]
    game_counts: dict[str, int]
    over_time: dict[str, list[NamedRating]]


def compute_player_ratings(games: list[MatchInfo]) -> RatingsAndCounts:
    model = get_model()

    all_players = {
        player_ids.resolve_player_name(p.name, p.color)
        for game in games
        for p in game.players
    }
    game_counts = dict.fromkeys(all_players, 0)

    players = {name: initialize_player(name, model) for name in all_players}
    logger.info(f"players: {players}")
    rating_over_time: dict[str, list[NamedRating]] = {name: [] for name in all_players}

    # Process games
    for game in sorted(games, key=lambda x: x.timestamp):
        if not game.composition:
            continue
        if not game_composition.competitive_game_filter(game.composition):
            continue
        if game.composition.is_1v1:
            continue
        teams = defaultdict(list)
        actual_players = [p for p in game.players if p.team > 0]
        logger.info(f"game: {game.id} players {[game.players]}")
        for player in actual_players:
            teams[player.team].append(
                player_ids.resolve_player_name(player.name, player.color)
            )
            game_counts[player_ids.resolve_player_name(player.name, player.color)] += 1
        if len(teams) != 2:
            continue

        scores = {t: 1 if game.winning_team == t else 0 for t in teams.keys()}
        score_values = list(scores.values())
        pteams = [
            [players[p].to_rating(model) for p in team] for team in teams.values()
        ]
        prediction = model.predict_win(teams=pteams)
        surprize = 1.0 - sum(b * p for b, p in zip(score_values, prediction))
        surprize_uncertainty_add = (surprize-0.5)*0.1 if surprize > 0.85 else 0.0
        logger.info(f"{teams}")
        logger.info(
            f"scores:{score_values} prediction={prediction} {surprize=} adding{surprize_uncertainty_add}"
        )
        new_ratings = model.rate(teams=pteams, scores=score_values)

        for t in new_ratings:
            for p in t:
                if p.name is not None:
                    new_rate = NamedRating(
                        name=p.name,
                        mu=p.mu,
                        sigma=p.sigma + surprize_uncertainty_add,
                        at_date=game.date,
                    )
                    players[p.name] = new_rate
                    rating_over_time[p.name].append(new_rate)

    ratings = [r for r in players.values() if game_counts.get(r.name, 0) > 20]
    sorted_ratings = sorted(ratings, key=lambda x: x.ordinal(), reverse=True)
    # Display results
    for rating in sorted_ratings:
        logger.info(
            f"{rating.name}[games={game_counts.get(rating.name)}]: {rating.ordinal():.1f} (μ={rating.mu:.1f}, σ={rating.sigma:.1f})"
        )

    over_time_filtered = {n: v for n, v in rating_over_time.items() if len(v) > 30}

    return RatingsAndCounts(
        ratings=sorted_ratings,
        game_counts=game_counts,
        over_time=over_time_filtered,
    )
