"""The bars the sequence model has to clear, scored on the same timesteps.

``predict.py --eval`` used to compare the GRU against ``log(2)`` and nothing
else. For a *mid-game* model that is close to no bar at all: by minute 15 one
side is usually visibly ahead on kills and army value, so almost any function of
the current scoreboard beats a coin flip by a mile. The question that matters is
whether watching the game unfold beats the two cheap answers:

``coin_flip``
    0.5 everywhere. Log-loss ln 2.

``static_logistic``
    An L2-penalised logistic on the *current* standardised feature row, fit over
    every training timestep and applied independently at each timestep - no
    recurrence, no memory of how the game got here. If the GRU cannot beat this,
    it is an expensive way to read a scoreboard.

The third bar - the pre-game model's prediction held flat for the whole match,
i.e. "does watching add anything to knowing who is playing" - needs the other
pipeline's snapshot, so it lives in the rolling harness rather than here; see
``README.md``.

Torch-free (numpy + a Newton solve), so this imports cleanly anywhere.
"""

from __future__ import annotations

import numpy as np

from .features import FeatureStats, SeqMatch

# Ridge strength on the summed log-likelihood, matching
# ``sklearn.linear_model.LogisticRegression(C=1.0)``.
L2 = 1.0


def coin_flip_probs(dev: list[SeqMatch]) -> list[np.ndarray]:
    return [np.full(s.length, 0.5) for s in dev]


def _fit_logistic(
    x: np.ndarray, y: np.ndarray, l2: float, iters: int = 50
) -> np.ndarray:
    """Newton-Raphson on the ridge-penalised log-likelihood; intercept unpenalised."""
    xi = np.hstack([x, np.ones((len(x), 1))])
    penalty = np.full(xi.shape[1], l2)
    penalty[-1] = 0.0
    beta = np.zeros(xi.shape[1])
    for _ in range(iters):
        p = 1.0 / (1.0 + np.exp(-np.clip(xi @ beta, -30, 30)))
        grad = xi.T @ (y - p) - penalty * beta
        hess = (xi * (p * (1 - p))[:, None]).T @ xi + np.diag(penalty)
        step = np.linalg.solve(hess, grad)
        beta += step
        if np.abs(step).max() < 1e-9:
            break
    return beta


def static_logistic_probs(
    train: list[SeqMatch], dev: list[SeqMatch], stats: FeatureStats, l2: float = L2
) -> list[np.ndarray]:
    """P(side A wins) read off the current row only, fit on every train timestep."""
    if not train:
        return coin_flip_probs(dev)
    x = np.concatenate([stats.apply(s.x)[: s.length] for s in train])
    y = np.concatenate([np.full(s.length, float(s.label)) for s in train])
    beta = _fit_logistic(x, y, l2)
    out = []
    for s in dev:
        xd = stats.apply(s.x)[: s.length]
        logit = np.hstack([xd, np.ones((len(xd), 1))]) @ beta
        out.append(1.0 / (1.0 + np.exp(-logit)))
    return out
