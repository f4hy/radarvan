"""Fit, evaluate and export the equal-skill composition/map model.

Penalties are tuned by cross-validation over game nights (generals are always
assigned at random, so these effects are treated as stationary), then scored on
chronological outer cuts where each fit sees only games before its cut. The exported artifact holds the
full-data fit plus game-night block-bootstrap replicates, general-level tables
only: player strengths are a training nuisance and never leave this script.

Usage::

    uv run python -m ml.scenario_train ml/data/snapshot-YYYYMMDD.jsonl.gz
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np
import structlog

from radarvan import player_ids
from radarvan.api_types import MatchInfo
from radarvan.logging_config import configure_logging

from .map_features import FEATURE_NAMES, normalize_map_name
from .scenario import N_GENERALS, EffectTables, Layout, design_row, fit_logistic
from .snapshot import load_snapshot

logger = structlog.get_logger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = REPO_ROOT / "ml_scenario" / "scenario_model.json"
ARTIFACT_VERSION = 1

CV_FOLDS = 10
# Grids run strongest-first and a change must strictly improve, so ties keep the
# more heavily shrunk model. Blocks are never switched off: a block the data
# can't support ends up near zero with its bootstrap spread intact, rather than
# claiming an exact zero.
TUNE_TOL = 1e-5
OUTER_CUTS = (0.78, 0.86, 0.93)
BLOCK_FRAC = 0.07
OFF = 1e8
PENALTY_GRID = (3000.0, 1000.0, 300.0, 100.0, 30.0, 10.0, 3.0, 1.0, 0.3)
HALF_LIFE_GRID = (None, 1095.0, 730.0, 365.0)
GENERAL_BLOCKS = (
    "faction",
    "general",
    "faction_synergy",
    "synergy",
    "faction_counter",
    "counter",
    "map_faction",
    "map_general",
)


@dataclass(frozen=True, slots=True)
class Game:
    match_id: int
    date: date
    team_a: tuple[int, ...]
    team_b: tuple[int, ...]
    players_a: tuple[str, ...]
    players_b: tuple[str, ...]
    label: int
    map_key: str
    duration_minutes: float


@dataclass(frozen=True, slots=True)
class Config:
    penalties: dict[str, float]
    half_life_days: float | None

    def with_penalty(self, block: str, value: float) -> Config:
        return Config({**self.penalties, block: value}, self.half_life_days)


def extract_game(m: MatchInfo) -> Game | None:
    teams: dict[int, list[tuple[str, int]]] = defaultdict(list)
    for p in m.roster().participants:
        teams[int(p.team)].append(
            (player_ids.resolve_player_name(p.name, p.color), int(p.general))
        )
    if len(teams) != 2:
        return None
    a_id, b_id = sorted(teams)
    a, b = teams[a_id], teams[b_id]
    winner = int(m.winning_team)
    if winner not in (a_id, b_id) or len(a) != len(b):
        return None
    if any(not 0 <= g < N_GENERALS for _, g in a + b):
        return None
    return Game(
        match_id=m.id,
        date=m.date,
        team_a=tuple(g for _, g in a),
        team_b=tuple(g for _, g in b),
        players_a=tuple(n for n, _ in a),
        players_b=tuple(n for n, _ in b),
        label=1 if winner == a_id else 0,
        map_key=normalize_map_name(m.map),
        duration_minutes=m.duration_minutes,
    )


class MapStandardizer:
    def __init__(self, table: dict[str, list[float]], games: list[Game]) -> None:
        self.table = table
        raw = np.array([table[g.map_key] for g in games if g.map_key in table])
        self.mean = raw.mean(0)
        self.std = raw.std(0)

    def features(self, map_key: str) -> np.ndarray:
        raw = self.table.get(map_key)
        if raw is None:
            return np.zeros(len(FEATURE_NAMES))
        return (np.asarray(raw) - self.mean) / self.std


@dataclass(frozen=True, slots=True)
class Design:
    layout: Layout
    x: np.ndarray
    y: np.ndarray
    ordinal: np.ndarray

    def penalty_vector(self, cfg: Config) -> np.ndarray:
        pen = np.zeros(self.layout.width)
        for name, sl in self.layout.offsets().items():
            pen[sl] = cfg.penalties.get(name, 0.0)
        return pen


def build_design(games: list[Game], maps: MapStandardizer) -> Design:
    players = tuple(sorted({p for g in games for p in (*g.players_a, *g.players_b)}))
    layout = Layout(n_map=len(FEATURE_NAMES), players=players)
    x = np.array(
        [
            design_row(
                layout,
                g.team_a,
                g.team_b,
                maps.features(g.map_key),
                g.players_a,
                g.players_b,
            )
            for g in games
        ]
    )
    y = np.array([g.label for g in games], float)
    ordinal = np.array([g.date.toordinal() for g in games], float)
    return Design(layout, x, y, ordinal)


def recency_weights(ordinal: np.ndarray, half_life_days: float | None) -> np.ndarray:
    if half_life_days is None or len(ordinal) == 0:
        return np.ones(len(ordinal))
    w = 0.5 ** ((ordinal.max() - ordinal) / half_life_days)
    return w * (len(w) / w.sum())


def fit(d: Design, idx: np.ndarray, cfg: Config) -> np.ndarray:
    w = recency_weights(d.ordinal[idx], cfg.half_life_days)
    return fit_logistic(d.x[idx], d.y[idx], w, d.penalty_vector(cfg))


@dataclass(frozen=True, slots=True)
class Pooled:
    probs: np.ndarray
    labels: np.ndarray
    ordinal: np.ndarray

    @property
    def nll(self) -> np.ndarray:
        p = np.clip(self.probs, 1e-6, 1 - 1e-6)
        return -(self.labels * np.log(p) + (1 - self.labels) * np.log(1 - p))

    def metrics(self) -> dict[str, float]:
        return {
            "n": len(self.labels),
            "log_loss": float(self.nll.mean()),
            "brier": float(((self.probs - self.labels) ** 2).mean()),
            "accuracy": float(((self.probs > 0.5) == (self.labels == 1)).mean()),
        }


def rolling(d: Design, cfg: Config, cuts: tuple[float, ...]) -> Pooled:
    n = len(d.y)
    probs, labels, ords = [], [], []
    for frac in cuts:
        cut = int(n * frac)
        end = min(n, cut + int(n * BLOCK_FRAC))
        beta = fit(d, np.arange(cut), cfg)
        test = np.arange(cut, end)
        probs.append(1 / (1 + np.exp(-(d.x[test] @ beta))))
        labels.append(d.y[test])
        ords.append(d.ordinal[test])
    return Pooled(np.concatenate(probs), np.concatenate(labels), np.concatenate(ords))


def night_folds(d: Design, k: int = CV_FOLDS, seed: int = 0) -> list[np.ndarray]:
    nights = np.unique(d.ordinal)
    order = np.random.default_rng(seed).permutation(len(nights))
    fold_of = dict(zip(nights[order], np.arange(len(nights)) % k, strict=True))
    fold = np.array([fold_of[o] for o in d.ordinal])
    return [np.flatnonzero(fold == i) for i in range(k)]


def cross_validate(d: Design, cfg: Config, folds: list[np.ndarray]) -> Pooled:
    probs = np.zeros(len(d.y))
    everything = np.arange(len(d.y))
    for test in folds:
        beta = fit(d, np.setdiff1d(everything, test), cfg)
        probs[test] = 1 / (1 + np.exp(-(d.x[test] @ beta)))
    return Pooled(probs, d.y, d.ordinal)


def paired_block_ci(
    a: Pooled, b: Pooled, n_boot: int = 2000, seed: int = 0
) -> tuple[float, float, float]:
    """Mean per-game log-loss difference a-b with a 95% interval resampling game nights."""
    diff = a.nll - b.nll
    nights = np.unique(a.ordinal)
    groups = [diff[a.ordinal == o] for o in nights]
    rng = np.random.default_rng(seed)
    stats = []
    for _ in range(n_boot):
        pick = rng.integers(0, len(groups), len(groups))
        stats.append(np.concatenate([groups[i] for i in pick]).mean())
    lo, hi = np.percentile(stats, [2.5, 97.5])
    return float(diff.mean()), float(lo), float(hi)


def tune(d: Design, start: Config, folds: list[np.ndarray], rounds: int = 3) -> Config:
    def score(c: Config) -> float:
        return cross_validate(d, c, folds).metrics()["log_loss"]

    best = start
    best_ll = score(best)
    tunable = ("player", *GENERAL_BLOCKS)
    for _ in range(rounds):
        improved = False
        for hl in HALF_LIFE_GRID:
            cand = Config(best.penalties, hl)
            ll = score(cand)
            if ll < best_ll - TUNE_TOL:
                best, best_ll, improved = cand, ll, True
        for block in tunable:
            for value in PENALTY_GRID:
                cand = best.with_penalty(block, value)
                ll = score(cand)
                if ll < best_ll - TUNE_TOL:
                    best, best_ll, improved = cand, ll, True
        logger.info("tune round", cv_log_loss=round(best_ll, 4), config=best)
        if not improved:
            break
    return best


def players_only(cfg: Config) -> Config:
    return Config(
        {**cfg.penalties, **dict.fromkeys(GENERAL_BLOCKS, OFF)}, cfg.half_life_days
    )


def bootstrap_tables(
    d: Design, cfg: Config, n_boot: int, seed: int = 1
) -> list[EffectTables]:
    nights = np.unique(d.ordinal)
    rows_by_night = {o: np.flatnonzero(d.ordinal == o) for o in nights}
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n_boot):
        pick = rng.choice(nights, len(nights), replace=True)
        idx = np.concatenate([rows_by_night[o] for o in pick])
        out.append(EffectTables.from_beta(d.layout, fit(d, idx, cfg)))
    return out


def composition_records(games: list[Game]) -> list[list]:
    return [
        [sorted(g.team_a), sorted(g.team_b), g.map_key, g.label, g.date.isoformat()]
        for g in games
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--n-boot", type=int, default=200)
    parser.add_argument("--no-tune", action="store_true")
    args = parser.parse_args()
    configure_logging(dev=True)

    stamp = args.snapshot.name.split(".")[0].replace("snapshot-", "")
    map_table = json.loads(
        (args.snapshot.parent / f"map_features-{stamp}.json").read_text()
    )
    matches = sorted(load_snapshot(args.snapshot), key=lambda m: m.timestamp)
    games = [g for m in matches if (g := extract_game(m)) is not None]
    maps = MapStandardizer(map_table, games)
    d = build_design(games, maps)
    logger.info(
        "design", games=len(games), players=len(d.layout.players), width=d.layout.width
    )

    start = Config(
        {"player": 1.0, **dict.fromkeys(GENERAL_BLOCKS, 3000.0)},
        730.0,
    )
    folds = night_folds(d)
    cfg = start if args.no_tune else tune(d, start, folds)

    variants = {
        "players_only": players_only(cfg),
        "players+generals": Config(
            {
                **cfg.penalties,
                **dict.fromkeys(GENERAL_BLOCKS[2:], OFF),
            },
            cfg.half_life_days,
        ),
        "full": cfg,
    }
    evaluation: dict[str, dict[str, object]] = {}
    for protocol, run in (
        ("night_cv", lambda c: cross_validate(d, c, night_folds(d, seed=7))),
        ("chronological", lambda c: rolling(d, c, OUTER_CUTS)),
    ):
        pooled = {name: run(c) for name, c in variants.items()}
        section: dict[str, object] = {}
        for name, p in pooled.items():
            section[name] = p.metrics()
            logger.info("eval", protocol=protocol, variant=name, **p.metrics())
        for name in ("players+generals", "full"):
            mean, lo, hi = paired_block_ci(pooled[name], pooled["players_only"])
            section[f"{name}_vs_players_only"] = {"mean": mean, "lo": lo, "hi": hi}
            logger.info(
                "vs players_only",
                protocol=protocol,
                variant=name,
                delta=round(mean, 4),
                lo=round(lo, 4),
                hi=round(hi, 4),
            )
        evaluation[protocol] = section

    all_idx = np.arange(len(games))
    point = EffectTables.from_beta(d.layout, fit(d, all_idx, cfg))
    replicates = bootstrap_tables(d, cfg, args.n_boot)

    general_games = np.zeros(N_GENERALS, int)
    for g in games:
        for gen in (*g.team_a, *g.team_b):
            general_games[gen] += 1
    map_games: dict[str, int] = defaultdict(int)
    for g in games:
        map_games[g.map_key] += 1
    map_keys = set(map_table) | set(map_games)

    artifact = {
        "version": ARTIFACT_VERSION,
        "trained_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "snapshot": args.snapshot.name,
        "n_games": len(games),
        "date_min": games[0].date.isoformat(),
        "date_max": games[-1].date.isoformat(),
        "penalties": cfg.penalties,
        "half_life_days": cfg.half_life_days,
        "evaluation": evaluation,
        "map_feature_names": list(FEATURE_NAMES),
        "map_mean": maps.mean.tolist(),
        "map_std": maps.std.tolist(),
        "maps": {
            k: {"raw": map_table.get(k), "games": map_games.get(k, 0)}
            for k in sorted(map_keys)
        },
        "general_games": general_games.tolist(),
        "compositions": composition_records(games),
        "point": point.to_json(),
        "replicates": [t.to_json() for t in replicates],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(artifact, separators=(",", ":")))
    logger.info(
        "wrote artifact", path=str(args.out), mb=round(args.out.stat().st_size / 1e6, 2)
    )


if __name__ == "__main__":
    main()
