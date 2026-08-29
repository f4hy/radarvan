"""The pre-game prior, frozen from the training split — an input to the sequence.

Measured on the rolling protocol: for roughly the **first four minutes** of a
match the sequence model is *worse* than knowing nothing except who is playing
(log-loss 0.698 against 0.644 over minutes 0-2). That is not surprising - almost
nothing has happened yet - but it means the curve opens at the wrong place, and
the first minutes are exactly where a win-probability bar is interesting.

So the roster strength goes in as a feature: one extra column, constant across
the match, holding the log-odds that side A wins from the players alone. The GRU
then learns for itself how fast to discount it as evidence arrives, instead of
starting from an uninformative prior and spending four minutes catching up.

The model is the same 17-parameter Bradley-Terry fit that ``ml/baselines.py``
uses for the pre-game task - one signed indicator per player, mean-pooled over
the team - and it is deliberately **not** imported from there: this one is fit
on *this* module's records (rosters and labels are all it needs), so training
here never depends on the other pipeline's snapshot being present or current.

Like ``FeatureStats``, it is fit on the train split only and frozen into the
split directory, so nothing about the dev block reaches the features.

Names are alias-resolved without colour, because the snapshot record stores
in-game names and not colours. That is deterministic and identical at training
and serving time, so there is no skew; the only cost is that the 38 bare "pc"
slots in the corpus (1.1%) all resolve to Pancake rather than splitting with
pcap. Worth knowing, not worth a schema change.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from radarvan import player_ids

# Ridge strength on the summed log-likelihood (matches sklearn's C=1.0), and the
# recency half-life in days. Both mirror ml/baselines.py; the corpus cannot
# separate anything between C=0.5 and C=4 (see ml/model_design.md).
L2 = 1.0


@dataclass(slots=True)
class PregamePrior:
    """Frozen Bradley-Terry coefficients: player -> column, plus an intercept."""

    players: dict[str, int]
    coef: list[float]  # len(players) + 1; the last entry is the intercept

    def logit(self, team_a: list[str], team_b: list[str]) -> float:
        """Log-odds that side A wins, from the rosters alone.

        Players absent from the frozen vocab contribute nothing — the same UNK
        behaviour the sequence model's feature stats give.
        """
        v = np.zeros(len(self.players) + 1)
        v[-1] = 1.0
        for team, sign in ((team_a, 1.0), (team_b, -1.0)):
            for raw in team:
                j = self.players.get(player_ids.resolve_player_name(raw))
                if j is not None:
                    v[j] += sign / max(len(team), 1)
        return float(v @ np.asarray(self.coef))

    def save(self, path: Path) -> None:
        path.write_text(
            json.dumps({"players": self.players, "coef": self.coef}, indent=2)
        )

    @classmethod
    def load(cls, path: Path) -> PregamePrior:
        d = json.loads(Path(path).read_text())
        return cls(
            players={str(k): int(v) for k, v in d["players"].items()},
            coef=[float(x) for x in d["coef"]],
        )

    @classmethod
    def neutral(cls) -> PregamePrior:
        """A prior that always says 0.0 — for runs trained before this existed."""
        return cls(players={}, coef=[0.0])


def _newton(x: np.ndarray, y: np.ndarray, l2: float, iters: int = 50) -> np.ndarray:
    """Ridge-penalised logistic by Newton-Raphson; the intercept is unpenalised."""
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


def fit(records: list[dict[str, Any]], l2: float = L2) -> PregamePrior:
    """Fit the prior on snapshot records — rosters and labels are all it uses."""
    names = sorted(
        {
            player_ids.resolve_player_name(p)
            for r in records
            for p in (*r["team_a_players"], *r["team_b_players"])
        }
    )
    index = {n: i for i, n in enumerate(names)}
    if not index or not records:
        return PregamePrior.neutral()
    x = np.zeros((len(records), len(index)))
    y = np.zeros(len(records))
    for i, r in enumerate(records):
        for team, sign in ((r["team_a_players"], 1.0), (r["team_b_players"], -1.0)):
            for raw in team:
                j = index.get(player_ids.resolve_player_name(raw))
                if j is not None:
                    x[i, j] += sign / max(len(team), 1)
        y[i] = float(r["label_a_win"])
    return PregamePrior(players=index, coef=_newton(x, y, l2).tolist())
