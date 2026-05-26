"""Whole-History Rating (Coulom, 2008) for player skill estimation.

Each player's skill is modeled as a step function of time — one rating per date the
player participated in a game — with a Gaussian random-walk prior on changes:
    r_p(t_{k+1}) - r_p(t_k) ~ N(0, w² · (t_{k+1} - t_k))

Game outcomes follow the team Bradley-Terry likelihood:
    P(team A wins) = sigmoid(Σ_{i∈A} r_i(t_g) - Σ_{i∈B} r_i(t_g))

Fit by alternating per-player Newton updates: with all other players' trajectories
held fixed, each player's full trajectory is solved jointly via a tridiagonal Newton
system (the Hessian is tridiagonal because the prior couples only consecutive dates).

Subsumes both OpenSkill (time-evolution) and batch BT (likelihood) in one principled
model. Output is each player's skill at their most recent game.
"""

import structlog
from collections import defaultdict
from dataclasses import dataclass
from typing import NamedTuple

import numpy as np
from cachetools import TTLCache, cached

from . import game_composition
from . import player_ids
from .api_types import MatchInfo

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class NamedSkill:
    name: str
    skill: float
    game_count: int


class _Game(NamedTuple):
    team1: list[tuple[int, int]]  # (player_idx, date_idx)
    team2: list[tuple[int, int]]
    y: float  # 1.0 if team1 won, 0.0 if team2 won


@dataclass
class _Prepared:
    idx_to_name: dict[int, str]
    player_dates: list[np.ndarray]  # sorted unique date ordinals per player
    skills: list[np.ndarray]  # mutable skill trajectory per player
    games: list[_Game]
    games_per_player: list[list[list[tuple[int, int]]]]  # [p][k] -> [(game_idx, sign)]
    game_counts: dict[str, int]


def _prepare(games_in: list[MatchInfo]) -> _Prepared:
    name_to_idx: dict[str, int] = {}
    player_dates_set: dict[int, set[int]] = defaultdict(set)
    raw_games: list[tuple[int, list[str], list[str], float]] = []

    for g in games_in:
        if g.winning_team <= 0 or g.composition is None:
            continue
        if not game_composition.competitive_game_filter(g.composition):
            continue
        teams: dict[int, list[str]] = defaultdict(list)
        for player in g.players:
            if player.team <= 0:
                continue
            name = player_ids.resolve_player_name(player.name, player.color)
            teams[player.team].append(name)
        if len(teams) != 2 or g.winning_team not in teams:
            continue
        t1_id, t2_id = sorted(teams.keys())
        team1_names = teams[t1_id]
        team2_names = teams[t2_id]
        y = 1.0 if g.winning_team == t1_id else 0.0
        date_ord = g.date.toordinal()
        for n in team1_names + team2_names:
            if n not in name_to_idx:
                name_to_idx[n] = len(name_to_idx)
            player_dates_set[name_to_idx[n]].add(date_ord)
        raw_games.append((date_ord, team1_names, team2_names, y))

    n_players = len(name_to_idx)
    idx_to_name = {i: n for n, i in name_to_idx.items()}
    dates_lists = [sorted(player_dates_set[p]) for p in range(n_players)]
    date_idx_for = [{d: i for i, d in enumerate(dl)} for dl in dates_lists]
    player_dates = [np.asarray(dl, dtype=np.int64) for dl in dates_lists]
    skills = [np.zeros(len(dl), dtype=np.float64) for dl in dates_lists]
    games_per_player: list[list[list[tuple[int, int]]]] = [
        [[] for _ in dl] for dl in dates_lists
    ]

    games: list[_Game] = []
    counts: dict[str, int] = defaultdict(int)
    for date_ord, t1, t2, y in raw_games:
        team1 = [(name_to_idx[n], date_idx_for[name_to_idx[n]][date_ord]) for n in t1]
        team2 = [(name_to_idx[n], date_idx_for[name_to_idx[n]][date_ord]) for n in t2]
        gi = len(games)
        games.append(_Game(team1=team1, team2=team2, y=y))
        for pi, k in team1:
            games_per_player[pi][k].append((gi, +1))
            counts[idx_to_name[pi]] += 1
        for pi, k in team2:
            games_per_player[pi][k].append((gi, -1))
            counts[idx_to_name[pi]] += 1

    return _Prepared(
        idx_to_name=idx_to_name,
        player_dates=player_dates,
        skills=skills,
        games=games,
        games_per_player=games_per_player,
        game_counts=dict(counts),
    )


def _sigmoid(x: np.ndarray) -> np.ndarray:
    # Skills stay in O(few units), so plain form is numerically safe here.
    return np.asarray(1.0 / (1.0 + np.exp(-x)))


def _update_player(
    p: int, prep: _Prepared, w2: float, l2: float, max_inner: int, tol: float
) -> float:
    """Inner Newton on player p's trajectory until converged or max_inner reached.

    All other players held fixed. Per-game teammate sums are cached across inner iters
    since only p's own skills change: diff_g = const_g + sign_g · skills_p[k].
    Returns the final inner step's max |Δ|.
    """
    skills_p = prep.skills[p]
    dates_p = prep.player_dates[p]
    n = len(skills_p)
    if n == 0:
        return 0.0

    ks_l, signs_l, consts_l, ys_l = [], [], [], []
    for k in range(n):
        for gi, sign in prep.games_per_player[p][k]:
            game = prep.games[gi]
            t1 = sum(prep.skills[pp][kk] for pp, kk in game.team1 if pp != p)
            t2 = sum(prep.skills[pp][kk] for pp, kk in game.team2 if pp != p)
            ks_l.append(k)
            signs_l.append(sign)
            consts_l.append(t1 - t2)
            ys_l.append(game.y)
    ks = np.asarray(ks_l, dtype=np.int64)
    signs = np.asarray(signs_l, dtype=np.float64)
    consts = np.asarray(consts_l, dtype=np.float64)
    ys = np.asarray(ys_l, dtype=np.float64)

    prior_inv = (
        1.0 / (w2 * np.maximum(np.diff(dates_p).astype(np.float64), 1.0))
        if n >= 2
        else np.zeros(0)
    )

    last_max = 0.0
    for _ in range(max_inner):
        p_win = _sigmoid(consts + signs * skills_p[ks])
        g = np.zeros(n, dtype=np.float64)
        diag = np.zeros(n, dtype=np.float64)
        np.add.at(g, ks, signs * (p_win - ys))
        np.add.at(diag, ks, p_win * (1.0 - p_win))

        if n >= 2:
            ds = np.diff(skills_p)
            g[:-1] -= ds * prior_inv
            g[1:] += ds * prior_inv
            diag[:-1] += prior_inv
            diag[1:] += prior_inv

        # Weak ridge anchors absolute level (only relative skill is identified).
        g += 2.0 * l2 * skills_p
        diag += 2.0 * l2

        if n == 1:
            delta = g / diag
        else:
            off = -prior_inv
            T = np.diag(diag) + np.diag(off, 1) + np.diag(off, -1)
            delta = np.linalg.solve(T, g).astype(np.float64, copy=False)

        skills_p -= delta
        last_max = float(np.max(np.abs(delta)))
        if last_max < tol:
            break
    return last_max


def _fit(
    prep: _Prepared,
    w2: float = 1e-3,
    l2: float = 1e-4,
    max_iters: int = 100,
    inner_iters: int = 5,
    tol: float = 1e-3,
) -> None:
    """Alternating per-player Newton. Per-player problem is convex, so the inner Newton
    converges quadratically — info propagates much faster than one-step-per-outer-iter."""
    for it in range(max_iters):
        max_change = max(
            _update_player(p, prep, w2, l2, inner_iters, tol)
            for p in range(len(prep.player_dates))
        )
        if it % 5 == 0:
            logger.debug("iter", iteration=it, max_change=max_change)
        if max_change < tol:
            logger.debug("converged", iteration=it, max_change=max_change)
            break


_skills_cache: TTLCache[frozenset[int], list[NamedSkill]] = TTLCache(maxsize=8, ttl=600)


@cached(cache=_skills_cache, key=lambda games: frozenset(g.id for g in games))
def compute_player_skills(games: list[MatchInfo]) -> list[NamedSkill]:
    prep = _prepare(games)
    if not prep.games:
        return []
    _fit(prep)

    finals = np.asarray([s[-1] for s in prep.skills if s.size > 0], dtype=np.float64)
    mean = float(finals.mean())

    results = [
        NamedSkill(
            name=prep.idx_to_name[idx],
            skill=float(prep.skills[idx][-1]) - mean,
            game_count=prep.game_counts[prep.idx_to_name[idx]],
        )
        for idx in range(len(prep.skills))
        if prep.skills[idx].size > 0 and prep.game_counts[prep.idx_to_name[idx]] > 20
    ]
    results.sort(key=lambda r: r.skill, reverse=True)
    return results
