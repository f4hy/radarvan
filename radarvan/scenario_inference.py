"""Serve the equal-skill composition/map model (``ml/scenario_train.py``) - numpy only."""

from __future__ import annotations

import itertools
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

from ml.map_features import normalize_map_name
from ml.scenario import N_GENERALS, EffectTables, contributions, stack

from .api_types import (
    Faction,
    General,
    ScenarioContributions,
    ScenarioEvaluation,
    ScenarioFactionPairEffect,
    ScenarioGeneralEffect,
    ScenarioInterval,
    ScenarioMapEffect,
    ScenarioMapEntry,
    ScenarioMapInfo,
    ScenarioMapOption,
    ScenarioModelInfo,
    ScenarioModelSummary,
    ScenarioPairEffect,
    ScenarioPick,
    ScenarioPrediction,
    ScenarioSlotSwaps,
    ScenarioSupport,
    ScenarioSwapOption,
)

MODEL_PATH = Path(os.getenv("SCENARIO_MODEL_PATH", "ml_scenario/scenario_model.json"))

MAX_COMBINATIONS = 4096
# Swaps and the map list each rerun the scenario dozens of times.
MAX_COMBINATIONS_DERIVED = 256
MAP_COMPARISONS = 12
TOP_PAIRS = 12

_RANDOM_FACTION = {
    ScenarioPick.RANDOM_USA: range(0, 4),
    ScenarioPick.RANDOM_CHINA: range(4, 8),
    ScenarioPick.RANDOM_GLA: range(8, 12),
    ScenarioPick.RANDOM: range(0, 12),
}


class ModelUnavailable(RuntimeError):
    pass


def candidates(pick: ScenarioPick) -> list[int]:
    if pick in _RANDOM_FACTION:
        return list(_RANDOM_FACTION[pick])
    return [General[pick.value].value]


@dataclass(frozen=True, slots=True)
class ScenarioModel:
    raw: dict[str, Any]
    # Index 0 is the full-data point fit; the rest are bootstrap replicates.
    tables: EffectTables
    map_mean: np.ndarray
    map_std: np.ndarray

    @property
    def info(self) -> ScenarioModelInfo:
        return ScenarioModelInfo(
            n_games=self.raw["n_games"],
            date_min=self.raw["date_min"],
            date_max=self.raw["date_max"],
            trained_at=self.raw["trained_at"],
            replicates=len(self.raw["replicates"]),
        )

    def map_features(self, key: str | None) -> np.ndarray:
        raw = self.raw["maps"].get(key, {}).get("raw") if key else None
        if raw is None:
            return np.zeros(len(self.map_mean))
        z: np.ndarray = (np.asarray(raw) - self.map_mean) / self.map_std
        return z


def model_available() -> bool:
    return MODEL_PATH.exists()


@lru_cache(maxsize=1)
def load_model() -> ScenarioModel:
    if not MODEL_PATH.exists():
        raise ModelUnavailable(f"scenario model not found at {MODEL_PATH}")
    raw = json.loads(MODEL_PATH.read_text())
    tables = stack(
        [EffectTables.from_json(raw["point"])]
        + [EffectTables.from_json(r) for r in raw["replicates"]]
    )
    return ScenarioModel(
        raw=raw,
        tables=tables,
        map_mean=np.asarray(raw["map_mean"]),
        map_std=np.asarray(raw["map_std"]),
    )


def resolve_map_key(map_name: str | None) -> str | None:
    if not map_name:
        return None
    return normalize_map_name(map_name)


def _combinations(slots: list[list[int]], cap: int) -> tuple[np.ndarray, bool]:
    total = int(np.prod([len(s) for s in slots]))
    if total <= cap:
        return np.array(list(itertools.product(*slots)), dtype=int), True
    rng = np.random.default_rng(0)
    return np.stack([rng.choice(s, cap) for s in slots], axis=1), False


def _interval(samples: np.ndarray, point: float) -> ScenarioInterval:
    lo, hi = np.percentile(samples, [5, 95])
    return ScenarioInterval(value=float(point), low=float(lo), high=float(hi))


def _probs(
    model: ScenarioModel, combos: np.ndarray, n: int, map_feat: np.ndarray
) -> np.ndarray:
    """P(team A) per table (point first), averaged over combinations in probability space."""
    c = contributions(model.tables, combos[:, :n], combos[:, n:], map_feat)
    return (1 / (1 + np.exp(-c.total))).mean(-1)


def _support(
    model: ScenarioModel, team_a: list[int], team_b: list[int], map_key: str | None
) -> ScenarioSupport:
    a, b = sorted(team_a), sorted(team_b)
    games = wins = games_map = wins_map = 0
    for ra, rb, game_map, label, _ in model.raw["compositions"]:
        if (ra, rb) == (a, b):
            a_won = label == 1
        elif (ra, rb) == (b, a):
            a_won = label == 0
        else:
            continue
        games += 1
        wins += a_won
        if game_map == map_key:
            games_map += 1
            wins_map += a_won
    return ScenarioSupport(
        exact_games=games,
        exact_team_a_wins=wins,
        exact_games_on_map=games_map,
        exact_team_a_wins_on_map=wins_map,
    )


def predict(
    team_a: list[ScenarioPick],
    team_b: list[ScenarioPick],
    map_name: str | None,
    players_by_map: Mapping[str, int],
) -> ScenarioPrediction:
    if not team_a or len(team_a) != len(team_b):
        raise ValueError("teams must be non-empty and the same size")
    model = load_model()
    n = len(team_a)
    slots = [candidates(p) for p in (*team_a, *team_b)]
    map_key = resolve_map_key(map_name)
    map_feat = model.map_features(map_key)

    combos, exact = _combinations(slots, MAX_COMBINATIONS)
    probs = _probs(model, combos, n, map_feat)
    point = contributions(model.tables, combos[:, :n], combos[:, n:], map_feat)

    small, _ = _combinations(slots, MAX_COMBINATIONS_DERIVED)
    base_small = _probs(model, small, n, map_feat)
    swaps = []
    for i in range(2 * n):
        options = []
        for g in range(N_GENERALS):
            swapped = small.copy()
            swapped[:, i] = g
            p = _probs(model, swapped, n, map_feat)
            delta = p - base_small
            options.append(
                ScenarioSwapOption(
                    general=General(g),
                    prob_team_a=float(p[0]),
                    delta=_interval(delta[1:], delta[0]),
                )
            )
        swaps.append(
            ScenarioSlotSwaps(team="A" if i < n else "B", index=i % n, options=options)
        )

    no_map = _probs(model, small, n, np.zeros_like(map_feat))
    popular = sorted(
        (
            (k, v["games"])
            for k, v in model.raw["maps"].items()
            if v["raw"] is not None
            and v["games"] > 0
            and players_by_map.get(k) == 2 * n
        ),
        key=lambda kv: -kv[1],
    )[:MAP_COMPARISONS]
    map_options = []
    for key, games in popular:
        p = _probs(model, small, n, model.map_features(key))
        delta = p - no_map
        map_options.append(
            ScenarioMapOption(
                key=key,
                training_games=games,
                prob_team_a=float(p[0]),
                delta=_interval(delta[1:], delta[0]),
            )
        )

    map_info = None
    if map_key is not None:
        entry = model.raw["maps"].get(map_key, {})
        known = entry.get("raw") is not None
        map_info = ScenarioMapInfo(
            key=map_key,
            known_geometry=known,
            training_games=entry.get("games", 0),
            features=(
                dict(
                    zip(model.raw["map_feature_names"], map_feat.tolist(), strict=True)
                )
                if known
                else {}
            ),
        )

    fixed = all(len(s) == 1 for s in slots)
    return ScenarioPrediction(
        prob_team_a=_interval(probs[1:], probs[0]),
        contributions=ScenarioContributions(
            generals=float(point.main[0].mean()),
            teammates=float(point.synergy[0].mean()),
            matchups=float(point.counter[0].mean()),
            map=float(point.map[0].mean()),
        ),
        combinations=len(combos),
        combinations_exact=exact,
        map=map_info,
        support=(
            _support(
                model, [s[0] for s in slots[:n]], [s[0] for s in slots[n:]], map_key
            )
            if fixed
            else None
        ),
        swaps=swaps,
        maps=map_options,
        model=model.info,
    )


def _counter_effects(values: np.ndarray, limit: int) -> list[ScenarioPairEffect]:
    point = values[0]
    pairs = [(g, h) for g in range(N_GENERALS) for h in range(g + 1, N_GENERALS)]
    pairs.sort(key=lambda gh: -abs(point[gh]))
    return [
        ScenarioPairEffect(
            general_a=General(g),
            general_b=General(h),
            effect=_interval(values[1:, g, h], point[g, h]),
        )
        for g, h in pairs[:limit]
    ]


def _faction_pair_effects(synergy: np.ndarray) -> list[ScenarioFactionPairEffect]:
    out = []
    for f in range(3):
        for h in range(f, 3):
            block = synergy[:, f * 4 : (f + 1) * 4, h * 4 : (h + 1) * 4].mean((-1, -2))
            out.append(
                ScenarioFactionPairEffect(
                    faction_a=Faction(f),
                    faction_b=Faction(h),
                    effect=_interval(block[1:], block[0]),
                )
            )
    return sorted(out, key=lambda e: -e.effect.value)


def summary(players_by_map: Mapping[str, int]) -> ScenarioModelSummary:
    model = load_model()
    t = model.tables
    main = t.main - t.main.mean(axis=1, keepdims=True)
    games = model.raw["general_games"]
    generals = sorted(
        (
            ScenarioGeneralEffect(
                general=General(g),
                effect=_interval(main[1:, g], main[0, g]),
                games=games[g],
            )
            for g in range(N_GENERALS)
        ),
        key=lambda e: -e.effect.value,
    )
    names = model.raw["map_feature_names"]
    slope = t.map_slope
    map_pairs = sorted(
        ((g, k) for g in range(N_GENERALS) for k in range(len(names))),
        key=lambda gk: -abs(slope[0, gk[0], gk[1]]),
    )[:TOP_PAIRS]
    evaluation = []
    for protocol, section in model.raw["evaluation"].items():
        d = section["full_vs_players_only"]
        evaluation.append(
            ScenarioEvaluation(
                protocol=protocol,
                games=section["full"]["n"],
                delta_log_loss=ScenarioInterval(
                    value=d["mean"], low=d["lo"], high=d["hi"]
                ),
            )
        )
    return ScenarioModelSummary(
        model=model.info,
        generals=generals,
        matchups=_counter_effects(t.counter, limit=TOP_PAIRS),
        teammates=_faction_pair_effects(t.synergy),
        map_effects=[
            ScenarioMapEffect(
                general=General(g),
                feature=names[k],
                effect=_interval(slope[1:, g, k], slope[0, g, k]),
            )
            for g, k in map_pairs
        ],
        map_features=names,
        maps=sorted(
            (
                ScenarioMapEntry(
                    key=k,
                    training_games=v["games"],
                    known_geometry=v["raw"] is not None,
                    players=players_by_map.get(k),
                )
                for k, v in model.raw["maps"].items()
            ),
            key=lambda m: (-m.training_games, m.key),
        ),
        evaluation=evaluation,
    )
