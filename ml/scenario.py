"""Equal-skill composition/map model: encoding, fit, and the effect tables served.

Torch-free: ``radarvan.scenario_inference`` imports this at serving time. See
``ml/scenario_predictor_design.md``. Player strengths are fitted as a nuisance
block and never leave training.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import combinations
from typing import Any

import numpy as np

N_GENERALS = 12
N_FACTIONS = 3


def faction(general: int) -> int:
    return general // 4


def _sym_index(n: int) -> dict[tuple[int, int], int]:
    return {
        (g, h): i
        for i, (g, h) in enumerate((g, h) for g in range(n) for h in range(g, n))
    }


def _skew_index(n: int) -> dict[tuple[int, int], int]:
    return {pair: i for i, pair in enumerate(combinations(range(n), 2))}


SYM = _sym_index(N_GENERALS)
SKEW = _skew_index(N_GENERALS)
FSYM = _sym_index(N_FACTIONS)
FSKEW = _skew_index(N_FACTIONS)


@dataclass(frozen=True, slots=True)
class Layout:
    """Column blocks of the training design; nuisance blocks are dropped at serving."""

    n_map: int
    players: tuple[str, ...]

    def blocks(self) -> dict[str, int]:
        return {
            "faction": N_FACTIONS,
            "general": N_GENERALS,
            "faction_synergy": len(FSYM),
            "synergy": len(SYM),
            "faction_counter": len(FSKEW),
            "counter": len(SKEW),
            "map_faction": N_FACTIONS * self.n_map,
            "map_general": N_GENERALS * self.n_map,
            "player": len(self.players),
            "intercept": 1,
        }

    def offsets(self) -> dict[str, slice]:
        out: dict[str, slice] = {}
        start = 0
        for name, size in self.blocks().items():
            out[name] = slice(start, start + size)
            start += size
        return out

    @property
    def width(self) -> int:
        return sum(self.blocks().values())


def _add_team(
    x: np.ndarray,
    off: dict[str, slice],
    generals: Sequence[int],
    map_feat: np.ndarray,
    sign: float,
) -> None:
    n = len(generals)
    k = len(map_feat)
    for g in generals:
        f = faction(g)
        x[off["faction"].start + f] += sign / n
        x[off["general"].start + g] += sign / n
        x[
            off["map_faction"].start + f * k : off["map_faction"].start + (f + 1) * k
        ] += sign * map_feat / n
        x[
            off["map_general"].start + g * k : off["map_general"].start + (g + 1) * k
        ] += sign * map_feat / n
    if n >= 2:
        n_pairs = n * (n - 1) / 2
        for g, h in combinations(generals, 2):
            lo, hi = min(g, h), max(g, h)
            x[off["synergy"].start + SYM[lo, hi]] += sign / n_pairs
            flo, fhi = sorted((faction(g), faction(h)))
            x[off["faction_synergy"].start + FSYM[flo, fhi]] += sign / n_pairs


def design_row(
    layout: Layout,
    team_a: Sequence[int],
    team_b: Sequence[int],
    map_feat: np.ndarray,
    players_a: Sequence[str] = (),
    players_b: Sequence[str] = (),
) -> np.ndarray:
    off = layout.offsets()
    x = np.zeros(layout.width)
    _add_team(x, off, team_a, map_feat, 1.0)
    _add_team(x, off, team_b, map_feat, -1.0)
    scale = 1.0 / (len(team_a) * len(team_b))
    for a in team_a:
        for b in team_b:
            if a != b:
                x[off["counter"].start + SKEW[min(a, b), max(a, b)]] += (
                    scale if a < b else -scale
                )
            fa, fb = faction(a), faction(b)
            if fa != fb:
                x[off["faction_counter"].start + FSKEW[min(fa, fb), max(fa, fb)]] += (
                    scale if fa < fb else -scale
                )
    index = {p: i for i, p in enumerate(layout.players)}
    for names, sign in ((players_a, 1.0), (players_b, -1.0)):
        for name in names:
            j = index.get(name)
            if j is not None:
                x[off["player"].start + j] += sign / len(names)
    x[off["intercept"].start] = 1.0
    return x


def fit_logistic(
    x: np.ndarray, y: np.ndarray, w: np.ndarray, penalty: np.ndarray, iters: int = 100
) -> np.ndarray:
    """Newton on ``sum w*nll + 0.5 * sum(penalty * beta**2)``; zero penalty = unpenalised."""
    beta = np.zeros(x.shape[1])
    # A tiny floor keeps directions the data never touches (e.g. unseen pairs) at 0.
    reg = np.maximum(penalty, 1e-8)
    for _ in range(iters):
        p = 1.0 / (1.0 + np.exp(-np.clip(x @ beta, -30, 30)))
        grad = x.T @ (w * (y - p)) - reg * beta
        hess = (x * (w * p * (1 - p))[:, None]).T @ x + np.diag(reg)
        step = np.linalg.solve(hess, grad)
        beta += step
        if np.abs(step).max() < 1e-10:
            break
    return beta


@dataclass(frozen=True, slots=True)
class EffectTables:
    """Equal-skill model in served form; faction-level terms are folded in.

    ``main[g]`` general strength, ``map_slope[g, k]`` its change per standardised
    map feature, ``synergy[g, h]`` symmetric teammate effect, ``counter[g, h]``
    skew-symmetric effect of ``g`` facing ``h``. All on the logit scale.
    """

    main: np.ndarray
    map_slope: np.ndarray
    synergy: np.ndarray
    counter: np.ndarray

    @classmethod
    def from_beta(cls, layout: Layout, beta: np.ndarray) -> EffectTables:
        off = layout.offsets()
        k = layout.n_map

        def block(name: str) -> np.ndarray:
            return beta[off[name]]

        gens = np.arange(N_GENERALS)
        facs = gens // 4
        main = block("faction")[facs] + block("general")
        map_slope = block("map_faction").reshape(N_FACTIONS, k)[facs] + block(
            "map_general"
        ).reshape(N_GENERALS, k)
        synergy = np.zeros((N_GENERALS, N_GENERALS))
        counter = np.zeros((N_GENERALS, N_GENERALS))
        syn, fsyn = block("synergy"), block("faction_synergy")
        cnt, fcnt = block("counter"), block("faction_counter")
        fac = [faction(g) for g in range(N_GENERALS)]
        for g in range(N_GENERALS):
            for h in range(N_GENERALS):
                lo, hi = min(g, h), max(g, h)
                flo, fhi = min(fac[g], fac[h]), max(fac[g], fac[h])
                synergy[g, h] = syn[SYM[lo, hi]] + fsyn[FSYM[flo, fhi]]
                if g != h:
                    counter[g, h] = cnt[SKEW[lo, hi]] * (1.0 if g < h else -1.0)
                if flo != fhi:
                    fsign = 1.0 if fac[g] < fac[h] else -1.0
                    counter[g, h] += fcnt[FSKEW[flo, fhi]] * fsign
        return cls(main=main, map_slope=map_slope, synergy=synergy, counter=counter)

    def to_json(self, digits: int = 5) -> dict[str, list[Any]]:
        return {
            "main": np.round(self.main, digits).tolist(),
            "map_slope": np.round(self.map_slope, digits).tolist(),
            "synergy": np.round(self.synergy, digits).tolist(),
            "counter": np.round(self.counter, digits).tolist(),
        }

    @classmethod
    def from_json(cls, data: dict[str, list[Any]]) -> EffectTables:
        return cls(**{k: np.asarray(data[k], dtype=float) for k in cls.__slots__})


class Contributions:
    """Per-combination logit pieces for ``team_a`` vs ``team_b``, vectorised.

    ``tables`` holds stacked replicate arrays (leading axis R); ``team_a``/``team_b``
    are int arrays of shape (K, n). Every attribute has shape (R, K).
    """

    __slots__ = ("counter", "main", "map", "synergy")

    def __init__(
        self,
        main: np.ndarray,
        map_slope: np.ndarray,
        synergy: np.ndarray,
        counter: np.ndarray,
        team_a: np.ndarray,
        team_b: np.ndarray,
        map_feat: np.ndarray,
    ) -> None:
        self.main = main[:, team_a].mean(-1) - main[:, team_b].mean(-1)
        slope = map_slope @ map_feat  # (R, 12)
        self.map = slope[:, team_a].mean(-1) - slope[:, team_b].mean(-1)
        self.synergy = _team_synergy(synergy, team_a) - _team_synergy(synergy, team_b)
        self.counter = counter[:, team_a[:, :, None], team_b[:, None, :]].mean((-1, -2))

    @property
    def total(self) -> np.ndarray:
        total: np.ndarray = self.main + self.map + self.synergy + self.counter
        return total


def _team_synergy(synergy: np.ndarray, team: np.ndarray) -> np.ndarray:
    n = team.shape[1]
    if n < 2:
        return np.zeros((synergy.shape[0], team.shape[0]))
    i, j = np.triu_indices(n, 1)
    return synergy[:, team[:, i], team[:, j]].mean(-1)


def stack(tables: Sequence[EffectTables]) -> EffectTables:
    return EffectTables(
        main=np.stack([t.main for t in tables]),
        map_slope=np.stack([t.map_slope for t in tables]),
        synergy=np.stack([t.synergy for t in tables]),
        counter=np.stack([t.counter for t in tables]),
    )


def contributions(
    stacked: EffectTables, team_a: np.ndarray, team_b: np.ndarray, map_feat: np.ndarray
) -> Contributions:
    return Contributions(
        stacked.main,
        stacked.map_slope,
        stacked.synergy,
        stacked.counter,
        team_a,
        team_b,
        map_feat,
    )
