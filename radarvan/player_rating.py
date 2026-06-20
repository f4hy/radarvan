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
import structlog

logger = structlog.get_logger(__name__)


NON_COMPETITIVE: set[str] = {"EasyArmy", "MediumArmy"}

MIN_GAMES = 1
ITERATIONS = 5

# When a game has any CPU player, scale down how far each player's rating moves
# (both mu and sigma). 1.0 = full movement, 0.0 = no movement. CPU games still
# count, just with diminished weight.
CPU_GAME_RATING_SCALE = 0.5


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
    known_computers = set(player_ids.CPU_NAME_MAPPING.values())
    known_players = set(player_ids.PLAYER_NAME_MAPPING.values())
    if name in NON_COMPETITIVE:
        return NamedRating(name=name, mu=0.5, sigma=r.sigma / 2.0)
    if name in known_computers:
        return NamedRating(name=name, mu=r.mu, sigma=r.sigma / 2.0)
    if name in known_players:
        return NamedRating(name=name, mu=r.mu, sigma=r.sigma)
    return NamedRating(name=name, mu=r.mu, sigma=r.sigma * 8)


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
class GameUpset:
    """A game where the team the model favored to win lost.

    Probabilities are the model's pre-game ``predict_win`` for each team, using
    the (converged) ratings from the final rating pass.
    """

    match_id: int
    at_date: date
    favored_team: int
    favored_win_prob: float
    favored_players: list[str]
    winning_team: int
    winner_win_prob: float
    winner_players: list[str]

    @property
    def surprise(self) -> float:
        """How lopsided the upset was: favorite's edge over the actual winner."""
        return self.favored_win_prob - self.winner_win_prob


@dataclass(slots=True)
class RatingsAndCounts:
    ratings: list[NamedRating]
    game_counts: dict[str, int]
    over_time: dict[str, list[NamedRating]]
    daily_changes: dict[str, list[RatingDailyChange]]
    match_changes: dict[str, list[RatingMatchChange]]
    ordinal_high: dict[str, float]
    ordinal_low: dict[str, float]
    upsets: list[GameUpset]


class TeamBuildResult(NamedTuple):
    teams: dict[int, list[str]]
    counts: dict[str, int]


class RatingUpdateResult(NamedTuple):
    updated: dict[str, NamedRating]
    history: dict[str, NamedRating]
    upset: GameUpset | None


class ProcessGamesResult(NamedTuple):
    players: dict[str, NamedRating]
    game_counts: dict[str, int]
    rating_over_time: dict[str, list[NamedRating]]
    match_changes: dict[str, list[RatingMatchChange]]
    upsets: list[GameUpset]


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
    logger.debug("processing game", game_id=game.id, players=game.players)
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
    logger.debug(
        "surprise", scores=score_values, prediction=prediction, surprise=surprize
    )
    return (surprize - 0.5) * 0.1 if surprize > 0.85 else 0.0


def _update_ratings_for_game(
    game: MatchInfo,
    teams: dict[int, list[str]],
    players: dict[str, NamedRating],
    model: PlackettLuce,
) -> RatingUpdateResult:
    """Return (updated_player_ratings, new_history_entries)."""
    team_ids = list(teams.keys())
    scores = {t: 1.0 if game.winning_team == t else 0 for t in team_ids}
    score_values = list(scores.values())
    pteams = [[players[p].to_rating(model) for p in team] for team in teams.values()]
    prediction = model.predict_win(teams=pteams)
    surprize_uncertainty_add = _compute_surprise_uncertainty(score_values, prediction)
    logger.debug("rating game", teams=teams, uncertainty_add=surprize_uncertainty_add)
    new_ratings = model.rate(teams=pteams, scores=score_values)
    known_computers = set(player_ids.CPU_NAME_MAPPING.values())
    has_cpu = any(name in known_computers for team in teams.values() for name in team)
    # CPU games are noise as "upsets" (the rating model down-weights them); skip them.
    upset = (
        None if has_cpu else _detect_upset(game, teams, dict(zip(team_ids, prediction)))
    )
    scale = CPU_GAME_RATING_SCALE if has_cpu else 1.0
    updated: dict[str, NamedRating] = {}
    history: dict[str, NamedRating] = {}
    for t in new_ratings:
        for p in t:
            if p.name is None:
                continue
            prev = players[p.name]
            target_sigma = p.sigma + surprize_uncertainty_add
            new_rate = NamedRating(
                name=p.name,
                mu=prev.mu + scale * (p.mu - prev.mu),
                sigma=prev.sigma + scale * (target_sigma - prev.sigma),
                at_date=game.date,
            )
            updated[p.name] = new_rate
            history[p.name] = new_rate
    return RatingUpdateResult(updated=updated, history=history, upset=upset)


def _detect_upset(
    game: MatchInfo,
    teams: dict[int, list[str]],
    win_prob_by_team: dict[int, float],
) -> GameUpset | None:
    """Return a GameUpset if the model's favored team lost, else None."""
    favored_team = max(win_prob_by_team, key=lambda t: win_prob_by_team[t])
    if favored_team == game.winning_team:
        return None
    return GameUpset(
        match_id=game.id,
        at_date=game.date,
        favored_team=favored_team,
        favored_win_prob=win_prob_by_team[favored_team],
        favored_players=list(teams[favored_team]),
        winning_team=game.winning_team,
        winner_win_prob=win_prob_by_team.get(game.winning_team, 0.0),
        winner_players=list(teams.get(game.winning_team, [])),
    )


def _process_games(
    games: list[MatchInfo],
    initial_players: dict[str, NamedRating],
    model: PlackettLuce,
) -> ProcessGamesResult:
    players = dict(initial_players)
    game_counts = dict.fromkeys(players, 0)
    rating_over_time: dict[str, list[NamedRating]] = {name: [] for name in players}
    match_changes: dict[str, list[RatingMatchChange]] = {name: [] for name in players}
    upsets: list[GameUpset] = []
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
        updated, history, upset = _update_ratings_for_game(game, teams, players, model)
        players.update(updated)
        if upset is not None:
            upsets.append(upset)
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
        upsets=upsets,
    )


def _log_sorted_ratings(
    sorted_ratings: list[NamedRating], game_counts: dict[str, int]
) -> None:
    for rating in sorted_ratings:
        logger.debug(
            "rating",
            name=rating.name,
            games=game_counts.get(rating.name),
            ordinal=round(rating.ordinal(), 1),
            mu=round(rating.mu, 1),
            sigma=round(rating.sigma, 1),
        )


def include_rating(game_counts: dict[str, int], name: str, min_game_count: int) -> bool:
    known_computers = set(player_ids.CPU_NAME_MAPPING.values())
    if name in known_computers:
        return True
    return game_counts.get(name, 0) > min_game_count


def filter_for_rating(game: MatchInfo) -> bool:
    if game.winning_team < 1:
        return False
    # Disconnects/desyncs/quit-early/too-short games aren't real results.
    if game.incomplete:
        return False
    if game.composition is None:
        return False
    if game.composition.is_comp_stomp:
        return False
    if game.composition.is_ffa:
        return False
    if not game.composition.is_balanced:
        return False
    for p in game.players:
        resolved = player_ids.resolve_player_name(p.name)
        if resolved in NON_COMPETITIVE:
            return False
        if resolved not in player_ids.PLAYER_NAMES:
            return False
    return True


@cached(cache={}, key=lambda games: frozenset(g.id for g in games))
def compute_player_ratings(games: list[MatchInfo]) -> RatingsAndCounts:
    model = get_model()
    filtered_games = [g for g in games if filter_for_rating(g)]
    all_players = _collect_all_players(filtered_games)
    player_ratings = {name: initialize_player(name, model) for name in all_players}
    logger.debug("initial players", players=player_ratings)

    for i in range(ITERATIONS):
        min_sigmaed = {k: v.with_min_sigma(5.0) for k, v in player_ratings.items()}
        player_ratings, game_counts, rating_over_time, match_changes, upsets = (
            _process_games(filtered_games, min_sigmaed, model)
        )
        logger.debug("pass", iteration=i)
        _log_sorted_ratings(
            [
                r
                for r in player_ratings.values()
                if include_rating(game_counts, r.name, min_game_count=MIN_GAMES)
            ],
            game_counts,
        )
    logger.debug("done computing ratings")

    ratings = [
        r
        for r in player_ratings.values()
        if include_rating(game_counts, r.name, min_game_count=MIN_GAMES)
    ]
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

    sorted_upsets = sorted(upsets, key=lambda u: u.surprise, reverse=True)

    return RatingsAndCounts(
        ratings=sorted_ratings,
        game_counts=game_counts,
        over_time=over_time_filtered,
        daily_changes=daily_changes,
        match_changes=match_changes,
        ordinal_high=ordinal_high,
        ordinal_low=ordinal_low,
        upsets=sorted_upsets,
    )
