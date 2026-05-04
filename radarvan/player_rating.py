from dataclasses import dataclass
from typing import NamedTuple
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


@dataclass(slots=True)
class NamedRating:
    """Wrapper around PlackettLuceRating where name is guaranteed to be str."""

    name: str
    mu: float
    sigma: float
    at_date: date | None = None

    def ordinal(self) -> float:
        return self.mu - 3 * self.sigma

    def with_min_sigma(self, min_sigma: float) -> "NamedRating":
        return NamedRating(
            name=self.name,
            mu=self.mu,
            sigma=max(self.sigma, min_sigma),
            at_date=self.at_date,
        )

    def to_rating(self, model: PlackettLuce) -> PlackettLuceRating:
        return model.rating(name=self.name, mu=self.mu, sigma=self.sigma)


def initialize_player(name: str, model: PlackettLuce) -> NamedRating:
    r = model.rating(name=name)
    return NamedRating(name=name, mu=r.mu, sigma=r.sigma)


@cached(cache={})
def get_model() -> PlackettLuce:
    # return PlackettLuce(beta=(25.0/3.0), tau=(25.0 / 200.0))
    return PlackettLuce(beta=(25.0 / 4.0))


@dataclass(slots=True)
class RatingDailyChange:
    date: date
    delta: float


@dataclass(slots=True)
class RatingMatchChange:
    match_id: int
    delta: float
    at_date: date


@dataclass(slots=True)
class RatingsAndCounts:
    ratings: list[NamedRating]
    game_counts: dict[str, int]
    over_time: dict[str, list[NamedRating]]
    daily_changes: dict[str, list[RatingDailyChange]]
    match_changes: dict[str, list[RatingMatchChange]]
    ordinal_high: dict[str, float]
    ordinal_low: dict[str, float]


class TeamBuildResult(NamedTuple):
    teams: dict[int, list[str]]
    counts: dict[str, int]


class RatingUpdateResult(NamedTuple):
    updated: dict[str, NamedRating]
    history: dict[str, NamedRating]


class ProcessGamesResult(NamedTuple):
    players: dict[str, NamedRating]
    game_counts: dict[str, int]
    rating_over_time: dict[str, list[NamedRating]]
    match_changes: dict[str, list[RatingMatchChange]]


def _collect_all_players(games: list[MatchInfo]) -> set[str]:
    return {
        player_ids.resolve_player_name(p.name, p.color)
        for game in games
        for p in game.players
    }


def _build_teams(game: MatchInfo) -> TeamBuildResult | None:
    """Return (teams, counts_increment) or None if game should be skipped."""
    teams: dict[int, list[str]] = defaultdict(list)
    counts: dict[str, int] = defaultdict(int)
    actual_players = [p for p in game.players if p.team > 0]
    logger.info(f"game: {game.id} players {[game.players]}")
    for player in actual_players:
        name = player_ids.resolve_player_name(player.name, player.color)
        teams[player.team].append(name)
        counts[name] += 1
    if len(teams) != 2:
        return None
    return TeamBuildResult(teams=teams, counts=counts)


def _compute_surprise_uncertainty(
    score_values: list[float], prediction: list[float]
) -> float:
    surprize = 1.0 - sum(b * p for b, p in zip(score_values, prediction))
    logger.info(f"scores:{score_values} prediction={prediction} {surprize=}")
    return (surprize - 0.5) * 0.1 if surprize > 0.85 else 0.0


def _update_ratings_for_game(
    game: MatchInfo,
    teams: dict[int, list[str]],
    players: dict[str, NamedRating],
    model: PlackettLuce,
) -> RatingUpdateResult:
    """Return (updated_player_ratings, new_history_entries)."""
    scores = {t: 1.0 if game.winning_team == t else 0 for t in teams.keys()}
    score_values = list(scores.values())
    pteams = [[players[p].to_rating(model) for p in team] for team in teams.values()]
    prediction = model.predict_win(teams=pteams)
    surprize_uncertainty_add = _compute_surprise_uncertainty(score_values, prediction)
    logger.info(f"{teams}")
    logger.info(f"adding {surprize_uncertainty_add}")
    new_ratings = model.rate(teams=pteams, scores=score_values)
    updated: dict[str, NamedRating] = {}
    history: dict[str, NamedRating] = {}
    for t in new_ratings:
        for p in t:
            if p.name is not None:
                new_rate = NamedRating(
                    name=p.name,
                    mu=p.mu,
                    sigma=p.sigma + surprize_uncertainty_add,
                    at_date=game.date,
                )
                updated[p.name] = new_rate
                history[p.name] = new_rate
    return RatingUpdateResult(updated=updated, history=history)


def _process_games(
    games: list[MatchInfo],
    initial_players: dict[str, NamedRating],
    model: PlackettLuce,
) -> ProcessGamesResult:
    players = dict(initial_players)
    game_counts = dict.fromkeys(players, 0)
    rating_over_time: dict[str, list[NamedRating]] = {name: [] for name in players}
    match_changes: dict[str, list[RatingMatchChange]] = {name: [] for name in players}
    for game in sorted(games, key=lambda x: x.timestamp):
        if not game.composition:
            continue
        if not game_composition.competitive_game_filter(game.composition):
            continue
        if game.composition.is_1v1:
            continue
        result = _build_teams(game)
        if result is None:
            continue
        teams, counts = result
        for name, count in counts.items():
            game_counts[name] += count
        pre_ordinals = {
            name: players[name].ordinal() for team in teams.values() for name in team
        }
        updated, history = _update_ratings_for_game(game, teams, players, model)
        players.update(updated)
        for name, entry in history.items():
            rating_over_time[name].append(entry)
            match_changes[name].append(
                RatingMatchChange(
                    match_id=game.id,
                    delta=entry.ordinal() - pre_ordinals[name],
                    at_date=game.date,
                )
            )
    return ProcessGamesResult(
        players=players,
        game_counts=game_counts,
        rating_over_time=rating_over_time,
        match_changes=match_changes,
    )


def _log_sorted_ratings(
    sorted_ratings: list[NamedRating], game_counts: dict[str, int]
) -> None:
    for rating in sorted_ratings:
        logger.info(
            f"{rating.name}[games={game_counts.get(rating.name)}]: {rating.ordinal():.1f} (μ={rating.mu:.1f}, σ={rating.sigma:.1f})"
        )


@cached(cache={}, key=lambda games: frozenset(g.id for g in games))
def compute_player_ratings(games: list[MatchInfo]) -> RatingsAndCounts:
    model = get_model()
    filtered_games = [g for g in games if g.winning_team > 0]
    all_players = _collect_all_players(filtered_games)
    player_ratings = {name: initialize_player(name, model) for name in all_players}
    logger.info(f"players: {player_ratings}")

    for i in range(5):
        min_sigmaed = {k: v.with_min_sigma(5.0) for k, v in player_ratings.items()}
        player_ratings, game_counts, rating_over_time, match_changes = _process_games(
            filtered_games, min_sigmaed, model
        )
        logger.info(f"Pass {i}")
        _log_sorted_ratings(
            [r for r in player_ratings.values() if game_counts.get(r.name, 0) > 20],
            game_counts,
        )
    logger.info("===")

    ratings = [r for r in player_ratings.values() if game_counts.get(r.name, 0) > 20]
    sorted_ratings = sorted(ratings, key=lambda x: x.ordinal(), reverse=True)
    _log_sorted_ratings(sorted_ratings, game_counts)

    over_time_filtered = {n: v for n, v in rating_over_time.items() if len(v) > 30}

    ordinal_high = {
        name: max(r.ordinal() for r in entries)
        for name, entries in rating_over_time.items()
        if entries
    }
    ordinal_low = {
        name: min(r.ordinal() for r in entries)
        for name, entries in rating_over_time.items()
        if entries
    }

    daily_changes: dict[str, list[RatingDailyChange]] = {}
    for name, changes in match_changes.items():
        by_date: dict[date, float] = defaultdict(float)
        for mc in changes:
            by_date[mc.at_date] += mc.delta
        daily_changes[name] = [
            RatingDailyChange(date=d, delta=delta)
            for d, delta in sorted(by_date.items())
        ]

    return RatingsAndCounts(
        ratings=sorted_ratings,
        game_counts=game_counts,
        over_time=over_time_filtered,
        daily_changes=daily_changes,
        match_changes=match_changes,
        ordinal_high=ordinal_high,
        ordinal_low=ordinal_low,
    )
