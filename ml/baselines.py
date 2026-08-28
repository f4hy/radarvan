"""The floors a 6,859-parameter net has to clear, scored on the same games.

``model_design.md`` has always listed four baselines and only ever implemented
two of them (coin flip, openskill). That mattered more than it sounds: openskill
is a *badly calibrated* bar - on the rolling protocol its stated 90-97%
favourites win 62% of the time and its log-loss is worse than a coin flip - so
"beats openskill on log-loss" is nearly free, and clearing it says nothing about
whether the extra capacity is earning its keep.

The two added here are the ones that actually bite:

``base_rate``
    Predict the training block's own ``team_a`` win rate for everything. Free
    accuracy from any base-rate asymmetry; nothing else.

``bt_logistic``
    L2-penalised Bradley-Terry: one signed indicator per player, mean-pooled
    over the team, recency-weighted, and nothing else - no generals, no map, no
    synergy, no interactions. **17 parameters on this corpus.** It is the
    honest capacity floor for a model whose whole job is "who is on which
    team", and on the rolling protocol it beats the full model on log-loss and
    Brier. Anything that cannot clear it is not paying for its parameters.

Torch-free and sklearn-free (a few Newton steps on a 17x17 system), so this can
be imported from anywhere in ``ml/``.
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np

from radarvan import player_ids
from radarvan.api_types import MatchInfo

# Ridge strength on the summed (weighted) log-likelihood, i.e. the objective is
# ``sum_i w_i * nll_i + 0.5 * L2 * ||beta||^2`` with the intercept unpenalised.
# 1.0 matches scikit-learn's ``LogisticRegression(C=1.0)`` default, which is
# what the sweep behind these numbers used; the corpus cannot separate anything
# between C=0.5 and C=4 (see model_design.md).
L2 = 1.0

# Half-life in days for down-weighting old training games, mirroring
# ``TrainConfig.recency_half_life_days``. Kept separate so the baseline stays a
# fixed reference point when the model's own default is swept.
RECENCY_HALF_LIFE_DAYS = 365.0


def two_teams(match: MatchInfo) -> tuple[list[str], list[str], int] | None:
    """``(team_a_names, team_b_names, label)`` for a usable 2-team game.

    Team A is the lower team id and ``label`` is 1 when it won - the same
    convention ``ml.features.encode_match`` uses, so probabilities from here and
    from the model are directly comparable game by game.
    """
    teams: dict[int, list[str]] = defaultdict(list)
    for p in match.roster().participants:
        teams[p.team].append(player_ids.resolve_player_name(p.name, p.color))
    if len(teams) != 2:
        return None
    a_id, b_id = sorted(teams)
    winner = int(match.winning_team)
    if winner not in (a_id, b_id) or not teams[a_id] or not teams[b_id]:
        return None
    return teams[a_id], teams[b_id], 1 if winner == a_id else 0


def base_rate_probs(
    train: list[MatchInfo], dev: list[MatchInfo]
) -> tuple[list[float], list[int]]:
    """Constant prediction: the training block's own team_a win rate."""
    labels_train = [g[2] for g in map(two_teams, train) if g is not None]
    p = sum(labels_train) / len(labels_train) if labels_train else 0.5
    labels = [g[2] for g in map(two_teams, dev) if g is not None]
    return [p] * len(labels), labels


def _design(
    matches: list[MatchInfo], index: dict[str, int]
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Signed, team-size-normalised player indicators + labels + date ordinals.

    Mean-pooling (``1/|team|`` per slot) rather than summing: with sum-pooling a
    4v4's logit carries four times a 1v1's spread purely from the pooling, and
    one set of coefficients cannot serve both. Measured - it is worth ~0.015
    log-loss here, which is larger than any feature we tried to add.
    """
    rows, labels, dates = [], [], []
    for m in matches:
        got = two_teams(m)
        if got is None:
            continue
        a_names, b_names, label = got
        x = np.zeros(len(index))
        for names, sign in ((a_names, 1.0), (b_names, -1.0)):
            for name in names:
                j = index.get(name)
                if j is not None:
                    x[j] += sign / len(names)
        rows.append(x)
        labels.append(label)
        dates.append(m.date.toordinal())
    if not rows:
        return np.zeros((0, len(index))), np.zeros(0), np.zeros(0)
    return np.array(rows), np.array(labels, float), np.array(dates, float)


def _recency_weights(dates: np.ndarray, half_life_days: float | None) -> np.ndarray:
    """``0.5 ** (age / half_life)``, anchored to the newest game and mean 1.0."""
    if half_life_days is None or len(dates) == 0:
        return np.ones(len(dates))
    w = 0.5 ** ((dates.max() - dates) / half_life_days)
    return w * (len(w) / w.sum())


def _fit_logistic(
    x: np.ndarray, y: np.ndarray, w: np.ndarray, l2: float, iters: int = 50
) -> np.ndarray:
    """Newton-Raphson on the ridge-penalised weighted log-likelihood.

    Returns ``beta`` for ``[x, 1]``; the trailing intercept is unpenalised. The
    system is one row per player, so a handful of exact Newton steps is both
    faster and more reproducible than a first-order solver.
    """
    xi = np.hstack([x, np.ones((len(x), 1))])
    penalty = np.full(xi.shape[1], l2)
    penalty[-1] = 0.0
    beta = np.zeros(xi.shape[1])
    for _ in range(iters):
        p = 1.0 / (1.0 + np.exp(-np.clip(xi @ beta, -30, 30)))
        grad = xi.T @ (w * (y - p)) - penalty * beta
        hess = (xi * (w * p * (1 - p))[:, None]).T @ xi + np.diag(penalty)
        step = np.linalg.solve(hess, grad)
        beta += step
        if np.abs(step).max() < 1e-9:
            break
    return beta


def bt_logistic_probs(
    train: list[MatchInfo],
    dev: list[MatchInfo],
    *,
    l2: float = L2,
    half_life_days: float | None = RECENCY_HALF_LIFE_DAYS,
) -> tuple[list[float], list[int]]:
    """P(team_a wins) from a recency-weighted, L2-penalised Bradley-Terry fit.

    Fit on ``train`` only; players absent from train get no column, so they
    contribute nothing - the same UNK behaviour the model's frozen vocab gives.
    """
    names = sorted({n for m in train if (g := two_teams(m)) for n in (*g[0], *g[1])})
    index = {name: i for i, name in enumerate(names)}
    x, y, dates = _design(train, index)
    if len(x) == 0:
        return base_rate_probs(train, dev)
    beta = _fit_logistic(x, y, _recency_weights(dates, half_life_days), l2)
    x_dev, y_dev, _ = _design(dev, index)
    if len(x_dev) == 0:
        return [], []
    logit = np.hstack([x_dev, np.ones((len(x_dev), 1))]) @ beta
    return (1.0 / (1.0 + np.exp(-logit))).tolist(), [int(v) for v in y_dev]
