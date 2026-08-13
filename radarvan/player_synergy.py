"""Pairwise player synergy.

Measures, for every pair of players, whether they win *more or less often as
teammates than their individual ratings predict*. See
``SYNERGY_METHODOLOGY.md`` for the full derivation.

Model: ridge logistic regression over team games. Each game is one Bernoulli
trial oriented so "team A" is the lower team id. The OpenSkill rating model's
log-odds is a fixed offset; we then explain the residual with signed player
main-effect terms and signed pairwise interaction terms::

    logit P(A wins) = logit(p_A)
                    + sum_{i in A} m_i   - sum_{i in B} m_i
                    + sum_{i<j in A} s_ij - sum_{i<j in B} s_ij

``s_ij`` is the synergy: the extra log-odds a team gets purely because i and j
are paired, beyond what their ratings predict and beyond each player's own
individual deviation (the main effect, which absorbs rating lag so it is not
mis-attributed to every pair containing that player). L2 penalties shrink
thinly-observed pairs toward zero.
"""

from dataclasses import dataclass
from collections import defaultdict

import numpy as np
import structlog
from cachetools import LRUCache
from openskill.models import PlackettLuce

from .api_types import MatchInfo
from .player_rating import (
    NamedRating,
    build_teams,
    compute_player_ratings,
    get_model,
    is_ratable_team_game,
)
from .utils import locked_cached

logger = structlog.get_logger(__name__)

# lambda_pair sets how much shared history a pair needs before its coefficient is
# believed; lambda_main controls the per-player main effects. Both must be fairly
# strong: in balanced team games the main effects (and pair terms) have an additive
# gauge freedom - only the L2 penalty pins them - so a weak penalty lets strong
# players' main effects run away to absurd magnitudes (they cancel within matchups
# but blow up the joint fit and saturate the pair coefficients).
DEFAULT_LAMBDA_PAIR = 10.0
DEFAULT_LAMBDA_MAIN = 25.0
DEFAULT_MIN_GAMES_TOGETHER = 3

# Bounds the synergy cache: keyed on (match-id set, lambda_pair, lambda_main,
# min_games_together), so it grows both as new matches land and as callers vary
# the (partly user-controlled, via /api/player_ratings/synergy/) regularization
# params. An LRU bound keeps that growth from being unlimited - see cache.py's
# module docstring for why every process-global cachetools cache needs one.
_SYNERGY_CACHE_MAXSIZE = 32

_NEWTON_ITERATIONS = 50
_NEWTON_TOL = 1e-8
_PROB_EPS = 1e-6


@dataclass(slots=True)
class PairSynergy:
    player_a: str
    player_b: str
    synergy: float  # log-odds coefficient s_ij
    win_prob_delta: float  # effect on win prob at an even (50/50) matchup
    games_together: int
    wins_together: int
    expected_wins: float  # sum of the rating model's (rating-only) predicted win prob
    std_error: float
    z_score: float
    # Diagnostics (admin view): help judge whether a large synergy is trustworthy.
    games_apart: int  # ratable games where the two were on opposing teams
    main_a: float  # player_a's fitted individual main effect (log-odds)
    main_b: float  # player_b's fitted individual main effect (log-odds)
    adjusted_expected_wins: (
        float  # expected wins from offset + main effects (no pair term)
    )


@dataclass(slots=True)
class _GameRow:
    y: float
    offset: float  # logit(prob_a), the regression's fixed exposure
    prob_a: float  # team A's rating-model win probability
    players_a: list[str]
    players_b: list[str]
    pairs_a: list[tuple[str, str]]
    pairs_b: list[tuple[str, str]]


def _pairs(names: list[str]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            out.append((a, b) if a < b else (b, a))
    return out


def _logit(p: float) -> float:
    p = min(max(p, _PROB_EPS), 1.0 - _PROB_EPS)
    return float(np.log(p / (1.0 - p)))


def _collect_rows(
    games: list[MatchInfo],
    rating_by_name: dict[str, NamedRating],
    model: PlackettLuce,
) -> list[_GameRow]:
    # Synergy is about human chemistry; drop any game with a CPU player so CPUs
    # never form pairs or main effects (PLAYER_NAMES includes CPU names, so the
    # rating filter alone doesn't exclude them).
    rows: list[_GameRow] = []
    for game in games:
        if not is_ratable_team_game(game):
            continue
        result = build_teams(game)
        if result is None:
            continue
        teams = result.teams
        if game.roster().has_cpu:
            continue
        if any(name not in rating_by_name for team in teams.values() for name in team):
            continue
        team_a, team_b = sorted(teams.keys())  # lower id is "A"
        players_a = list(teams[team_a])
        players_b = list(teams[team_b])
        ratings_a = [rating_by_name[n].to_rating(model) for n in players_a]
        ratings_b = [rating_by_name[n].to_rating(model) for n in players_b]
        prob_a, _ = model.predict_win(teams=[ratings_a, ratings_b])
        rows.append(
            _GameRow(
                y=1.0 if game.winning_team == team_a else 0.0,
                offset=_logit(prob_a),
                prob_a=prob_a,
                players_a=players_a,
                players_b=players_b,
                pairs_a=_pairs(players_a),
                pairs_b=_pairs(players_b),
            )
        )
    return rows


def _fit_ridge_logistic(
    X: np.ndarray, y: np.ndarray, offset: np.ndarray, penalty: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Newton-Raphson (IRLS) for L2-penalized logistic regression.

    Returns (coefficients, covariance) where covariance is the inverse penalized
    Hessian at the optimum (Laplace approximation), used for standard errors.
    """
    n_features = X.shape[1]
    beta = np.zeros(n_features)
    P = np.diag(penalty)
    hessian = P
    for _ in range(_NEWTON_ITERATIONS):
        eta = X @ beta + offset
        mu = 1.0 / (1.0 + np.exp(-eta))
        w = np.clip(mu * (1.0 - mu), _PROB_EPS, None)
        grad = X.T @ (y - mu) - penalty * beta
        hessian = X.T @ (X * w[:, None]) + P
        step = np.linalg.solve(hessian, grad)
        beta = beta + step
        if np.max(np.abs(step)) < _NEWTON_TOL:
            break
    cov = np.linalg.inv(hessian)
    return beta, cov


@locked_cached(
    cache=LRUCache(maxsize=_SYNERGY_CACHE_MAXSIZE),
    key=lambda games, lambda_pair=DEFAULT_LAMBDA_PAIR, lambda_main=DEFAULT_LAMBDA_MAIN, min_games_together=DEFAULT_MIN_GAMES_TOGETHER: (
        frozenset(g.id for g in games),
        lambda_pair,
        lambda_main,
        min_games_together,
    ),
)
def compute_player_synergy(
    games: list[MatchInfo],
    lambda_pair: float = DEFAULT_LAMBDA_PAIR,
    lambda_main: float = DEFAULT_LAMBDA_MAIN,
    min_games_together: int = DEFAULT_MIN_GAMES_TOGETHER,
) -> list[PairSynergy]:
    """Synergy coefficient per teammate pair, sorted by synergy descending."""
    ratings_and_counts = compute_player_ratings(games)
    rating_by_name = {r.name: r for r in ratings_and_counts.ratings}
    model = get_model()

    rows = _collect_rows(games, rating_by_name, model)
    if not rows:
        return []

    # Stable column layout: player main effects, then pair interactions.
    players = sorted({p for r in rows for p in (*r.players_a, *r.players_b)})
    pairs = sorted({pr for r in rows for pr in (*r.pairs_a, *r.pairs_b)})
    player_col = {name: i for i, name in enumerate(players)}
    pair_col = {pr: len(players) + i for i, pr in enumerate(pairs)}
    n_features = len(players) + len(pairs)

    X = np.zeros((len(rows), n_features))
    y = np.array([r.y for r in rows])
    offset = np.array([r.offset for r in rows])
    for ri, row in enumerate(rows):
        for name in row.players_a:
            X[ri, player_col[name]] += 1.0
        for name in row.players_b:
            X[ri, player_col[name]] -= 1.0
        for pr in row.pairs_a:
            X[ri, pair_col[pr]] += 1.0
        for pr in row.pairs_b:
            X[ri, pair_col[pr]] -= 1.0

    penalty = np.empty(n_features)
    penalty[: len(players)] = lambda_main
    penalty[len(players) :] = lambda_pair

    beta, cov = _fit_ridge_logistic(X, y, offset, penalty)
    std_err = np.sqrt(np.clip(np.diag(cov), 0.0, None))
    main = beta[: len(players)]  # fitted per-player main effects

    # Per-pair shared-game tallies. `adjusted_expected` is the model's expectation
    # from offset + main effects only (no pair term) - the baseline the synergy is
    # actually measured against. `games_apart` counts games where the two were on
    # opposing teams (the key trust signal: a pair that never splits up is the
    # collinear, hard-to-identify case).
    games_together: dict[tuple[str, str], int] = defaultdict(int)
    wins_together: dict[tuple[str, str], int] = defaultdict(int)
    expected_wins: dict[tuple[str, str], float] = defaultdict(float)
    adjusted_expected: dict[tuple[str, str], float] = defaultdict(float)
    games_apart: dict[tuple[str, str], int] = defaultdict(int)
    for row in rows:
        main_a = sum(main[player_col[n]] for n in row.players_a)
        main_b = sum(main[player_col[n]] for n in row.players_b)
        adj_prob_a = 1.0 / (1.0 + np.exp(-(row.offset + main_a - main_b)))
        for pr in row.pairs_a:
            games_together[pr] += 1
            wins_together[pr] += int(row.y == 1.0)
            expected_wins[pr] += row.prob_a
            adjusted_expected[pr] += adj_prob_a
        for pr in row.pairs_b:
            games_together[pr] += 1
            wins_together[pr] += int(row.y == 0.0)
            expected_wins[pr] += 1.0 - row.prob_a
            adjusted_expected[pr] += 1.0 - adj_prob_a
        for a in row.players_a:
            for b in row.players_b:
                games_apart[(a, b) if a < b else (b, a)] += 1

    results: list[PairSynergy] = []
    for pr in pairs:
        if games_together[pr] < min_games_together:
            continue
        col = pair_col[pr]
        s = float(beta[col])
        se = float(std_err[col])
        results.append(
            PairSynergy(
                player_a=pr[0],
                player_b=pr[1],
                synergy=s,
                win_prob_delta=float(1.0 / (1.0 + np.exp(-s)) - 0.5),
                games_together=games_together[pr],
                wins_together=wins_together[pr],
                expected_wins=round(expected_wins[pr], 2),
                std_error=se,
                z_score=float(s / se) if se > 0 else 0.0,
                games_apart=games_apart.get(pr, 0),
                main_a=float(main[player_col[pr[0]]]),
                main_b=float(main[player_col[pr[1]]]),
                adjusted_expected_wins=round(adjusted_expected[pr], 2),
            )
        )

    results.sort(key=lambda r: r.synergy, reverse=True)
    return results
