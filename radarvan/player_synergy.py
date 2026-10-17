"""Teammate pairs' actual wins minus chronological pregame expectations."""

import math
from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations

from . import player_rating
from .api_types import MatchInfo
from .derived import CORPUS, derived

DEFAULT_MIN_GAMES_TOGETHER = 3
# Fewer games apart than this and a player's solo baseline is too noisy to show.
MIN_SOLO_GAMES = 5


@dataclass(frozen=True)
class PregameExpectation:
    match_id: int
    game_format: str
    teams: tuple[tuple[str, ...], ...]
    probabilities: tuple[float, ...]
    outcomes: tuple[int, ...]


@dataclass(frozen=True)
class PairSynergy:
    player_a: str
    player_b: str
    games_together: int
    wins_together: int
    expected_wins: float
    # Per-game excess in each player's games without the other; None below MIN_SOLO_GAMES.
    solo_a: float | None
    solo_b: float | None
    # Sum of p(1-p): the model's variance of wins_together.
    variance: float

    @property
    def excess_wins(self) -> float:
        return self.wins_together - self.expected_wins

    @property
    def win_rate_delta(self) -> float:
        return self.excess_wins / self.games_together

    @property
    def z_score(self) -> float:
        return self.excess_wins / math.sqrt(self.variance) if self.variance else 0.0


@dataclass
class _Tally:
    games: int = 0
    wins: int = 0
    expected: float = 0.0
    variance: float = 0.0

    def add(self, outcome: int, probability: float) -> None:
        self.games += 1
        self.wins += outcome
        self.expected += probability
        self.variance += probability * (1 - probability)


@derived(on=CORPUS, maxsize=6)
def pregame_expectations(games: list[MatchInfo]) -> list[PregameExpectation]:
    model = player_rating.get_model()
    prepared, _ = player_rating._ratable_games(games)
    names = {name for _, teams in prepared for team in teams.values() for name in team}
    ratings = {name: player_rating.initialize_player(name, model) for name in names}
    rows = []
    for game, teams in prepared:
        eligible = not game.roster().has_cpu and not any(
            player_rating.is_guest_name(name)
            for team in teams.values()
            for name in team
        )
        # `composition` is always set here; the check narrows the type.
        if eligible and game.composition is not None:
            probabilities = player_rating.displayed_win_probs(
                [
                    [ratings[name].to_rating(model) for name in team]
                    for team in teams.values()
                ]
            )
            rows.append(
                PregameExpectation(
                    match_id=game.id,
                    game_format=game.composition.category,
                    teams=tuple(tuple(sorted(team)) for team in teams.values()),
                    probabilities=tuple(probabilities),
                    outcomes=tuple(int(team == game.winning_team) for team in teams),
                )
            )
        # CPU/guest games and tournament 1v1s still move the pregame ratings.
        update = player_rating._update_ratings_for_game(game, teams, ratings, model)
        ratings.update(update.updated)
    return rows


def _solo(player: _Tally, pair: _Tally) -> float | None:
    games = player.games - pair.games
    if games < MIN_SOLO_GAMES:
        return None
    return ((player.wins - pair.wins) - (player.expected - pair.expected)) / games


@derived(on=CORPUS, maxsize=32)
def compute_player_synergy(
    games: list[MatchInfo],
    min_games_together: int = DEFAULT_MIN_GAMES_TOGETHER,
    game_format: str | None = None,
) -> list[PairSynergy]:
    if min_games_together < 1:
        raise ValueError("min_games_together must be positive")
    pairs: dict[tuple[str, str], _Tally] = defaultdict(_Tally)
    players: dict[str, _Tally] = defaultdict(_Tally)
    # Filter after replay so other formats still inform point-in-time ratings.
    for row in pregame_expectations(games):
        if game_format is not None and row.game_format != game_format:
            continue
        for team, probability, outcome in zip(
            row.teams, row.probabilities, row.outcomes, strict=True
        ):
            if len(team) < 2:
                continue  # a 1v1 says nothing about team play
            for name in team:
                players[name].add(outcome, probability)
            for pair in combinations(team, 2):
                pairs[pair].add(outcome, probability)
    result = [
        PairSynergy(
            player_a=a,
            player_b=b,
            games_together=t.games,
            wins_together=t.wins,
            expected_wins=t.expected,
            solo_a=_solo(players[a], t),
            solo_b=_solo(players[b], t),
            variance=t.variance,
        )
        for (a, b), t in pairs.items()
        if t.games >= min_games_together
    ]
    return sorted(result, key=lambda p: (-p.z_score, p.player_a, p.player_b))
