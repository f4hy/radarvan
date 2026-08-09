"""CPU inference + evaluation harness (model vs baselines).

Loads a run bundle on CPU and reports log-loss / accuracy / AUC / Brier on the
dev split, alongside the baselines the model must beat: coin flip and the repo's
openskill ``predict_win`` (ratings fit on the *train* split, evaluated on dev).

Usage::

    uv run python -m ml.predict ml/data/split-*/runs/<ts>/ --eval
"""

from __future__ import annotations

import argparse
import json
import math
import os
from dataclasses import dataclass
from pathlib import Path

import structlog
import torch

from radarvan import player_ids, player_rating
from radarvan.api_types import General, MatchInfo, Team
from radarvan.db_utils import DatabaseManager, ReplayManager
from radarvan.matches import match_to_matchinfo

from .config import Config, ModelConfig, TrainConfig
from .dataset import Batch, collate
from .features import Vocab, encode_match, resolved_real_players
from .model import OutcomeLitModule
from .snapshot import load_snapshot

logger = structlog.get_logger(__name__)


# --- bundle loading --------------------------------------------------------


def _config_from_json(raw: dict) -> Config:
    m = raw["model"]
    t = raw["train"]
    return Config(
        model=ModelConfig(
            **{**m, "mlp_hidden": tuple(m["mlp_hidden"])}
        ),
        train=TrainConfig(**t),
    )


def load_bundle(run_dir: Path) -> tuple[OutcomeLitModule, Vocab, Config]:
    """Load (module, vocab, config) from a run dir, on CPU, with calibration applied."""
    vocab = Vocab.load(run_dir / "vocab.json")
    cfg = _config_from_json(json.loads((run_dir / "config.json").read_text()))
    module = OutcomeLitModule(vocab, cfg)
    ckpt = torch.load(run_dir / "best.ckpt", map_location="cpu", weights_only=False)
    module.load_state_dict(ckpt["state_dict"])
    calib_path = run_dir / "calibration.json"
    if calib_path.exists():
        t = json.loads(calib_path.read_text())["temperature"]
        module.model.temperature = torch.tensor([float(t)])
    module.eval()
    return module, vocab, cfg


# --- metrics ---------------------------------------------------------------


@dataclass(slots=True)
class Metrics:
    name: str
    n: int
    log_loss: float
    accuracy: float
    brier: float
    auc: float


def _auc(probs: list[float], labels: list[int]) -> float:
    pos = [p for p, y in zip(probs, labels) if y == 1]
    neg = [p for p, y in zip(probs, labels) if y == 0]
    if not pos or not neg:
        return float("nan")
    wins = sum(
        (1.0 if pp > pn else 0.5 if pp == pn else 0.0) for pp in pos for pn in neg
    )
    return wins / (len(pos) * len(neg))


def score(name: str, probs: list[float], labels: list[int]) -> Metrics:
    eps = 1e-7
    n = len(labels)
    ll = -sum(
        y * math.log(max(p, eps)) + (1 - y) * math.log(max(1 - p, eps))
        for p, y in zip(probs, labels)
    ) / n
    acc = sum((p > 0.5) == bool(y) for p, y in zip(probs, labels)) / n
    brier = sum((p - y) ** 2 for p, y in zip(probs, labels)) / n
    return Metrics(name, n, ll, acc, brier, _auc(probs, labels))


# --- baselines -------------------------------------------------------------


def openskill_probs(
    train: list[MatchInfo], dev: list[MatchInfo]
) -> tuple[list[float], list[int]]:
    """openskill predict_win for team_a (smaller team id), fit on train only."""
    model = player_rating.get_model()
    rc = player_rating.compute_player_ratings(train)
    rated = {r.name: r for r in rc.ratings}

    def rating(name: str) -> player_rating.NamedRating:
        return rated.get(name) or player_rating.initialize_player(name, model)

    probs: list[float] = []
    labels: list[int] = []
    for m in dev:
        teams: dict[int, list[str]] = {}
        for p in m.roster().participants:
            teams.setdefault(p.team, []).append(
                player_ids.resolve_player_name(p.name, p.color)
            )
        if len(teams) != 2:
            continue
        a_id, b_id = sorted(teams)
        winner = int(m.winning_team)
        if winner not in (a_id, b_id):
            continue
        pteams = [
            [rating(n).to_rating(model) for n in teams[a_id]],
            [rating(n).to_rating(model) for n in teams[b_id]],
        ]
        p_a, _p_b = model.predict_win(teams=pteams)
        probs.append(float(p_a))
        labels.append(1 if winner == a_id else 0)
    return probs, labels


def model_probs(
    module: OutcomeLitModule, vocab: Vocab, dev: list[MatchInfo]
) -> tuple[list[float], list[int]]:
    encoded = [e for e in (encode_match(m, vocab) for m in dev) if e is not None]
    probs: list[float] = []
    labels: list[int] = []
    with torch.no_grad():
        for i in range(0, len(encoded), 256):
            batch: Batch = collate(encoded[i : i + 256])
            p = torch.sigmoid(module.model.calibrated_logit(batch))
            probs.extend(p.tolist())
            labels.extend(int(e.label) for e in encoded[i : i + 256])
    return probs, labels


def _fmt(m: Metrics) -> str:
    return (
        f"{m.name:<22} n={m.n:<5} logloss={m.log_loss:.4f} "
        f"acc={m.accuracy:.3f} auc={m.auc:.3f} brier={m.brier:.4f}"
    )


def evaluate(run_dir: Path) -> None:
    split_dir = run_dir.parent.parent
    train = load_snapshot(split_dir / "train.jsonl.gz")
    dev = load_snapshot(split_dir / "dev.jsonl.gz")
    module, vocab, _cfg = load_bundle(run_dir)

    results: list[Metrics] = []

    # Coin flip.
    _, dev_labels = model_probs(module, vocab, dev)
    results.append(score("coin_flip", [0.5] * len(dev_labels), dev_labels))

    # openskill.
    os_probs, os_labels = openskill_probs(train, dev)
    results.append(score("openskill", os_probs, os_labels))

    # Our model.
    m_probs, m_labels = model_probs(module, vocab, dev)
    results.append(score("ml_model", m_probs, m_labels))

    print("\n=== dev evaluation ===")
    for r in results:
        print(_fmt(r))


# --- single-match prediction ----------------------------------------------


def fetch_match(match_id: int) -> MatchInfo:
    """Load one match from the DB as a MatchInfo (needs DATABASE_URL)."""
    constring = os.getenv("DATABASE_URL")
    if constring is None:
        raise SystemExit("DATABASE_URL environment variable is not set")
    db_manager = DatabaseManager(constring)
    with db_manager.SessionLocal() as session:
        rm = ReplayManager(session, auto_commit=False, notify=False)
        db_match = rm.get_match(match_id)
        if db_match is None:
            raise SystemExit(f"match {match_id} not found in the database")
        override = rm.get_overrides().get(match_id)
        return match_to_matchinfo(db_match, override)


def _roster(match: MatchInfo, vocab: Vocab) -> dict[int, list[tuple[str, str, bool]]]:
    """team id -> [(resolved_name, general_name, known_to_model)] for real players."""
    teams: dict[int, list[tuple[str, str, bool]]] = {}
    for name, p in resolved_real_players(match):
        known = vocab.player_idx(name) != 0
        teams.setdefault(p.team, []).append((name, General(p.general).name, known))
    return teams


def predict_match(run_dir: Path, match_id: int) -> None:
    module, vocab, _cfg = load_bundle(run_dir)
    match = fetch_match(match_id)
    encoded = encode_match(match, vocab)
    if encoded is None:
        raise SystemExit(
            f"match {match_id} isn't a usable 2-team game (can't encode/predict)"
        )

    with torch.no_grad():
        terms = module.model.explain(collate([encoded]))
    prob_a = float(terms["prob_team_a"].item())

    teams = _roster(match, vocab)
    a_id, b_id = sorted(teams)

    def fmt_team(tid: int) -> str:
        return ", ".join(
            f"{n} ({g}){'' if known else ' [UNKNOWN]'}" for n, g, known in teams[tid]
        )

    unknown = [n for t in teams.values() for n, _g, known in t if not known]

    print(f"\n=== match {match_id} on {match.map} ({match.date}) ===")
    print(f"team A (id {a_id}): {fmt_team(a_id)}")
    print(f"team B (id {b_id}): {fmt_team(b_id)}")
    print(f"\nP(team A wins) = {prob_a:.1%}   P(team B wins) = {1 - prob_a:.1%}")
    favored, fp = ("A", prob_a) if prob_a >= 0.5 else ("B", 1 - prob_a)
    print(f"predicted winner: team {favored} ({fp:.1%})")

    # Logit decomposition (positive favours team A). See model_design.md.
    print("\nlogit terms (+ favours A):")
    for key in ("strength", "synergy", "matchup", "bias"):
        print(f"  {key:<9} {float(terms[key].item()):+.3f}")
    print(
        f"  {'raw':<9} {float(terms['raw_logit'].item()):+.3f}"
        f"   (temperature-scaled: {float(terms['calibrated_logit'].item()):+.3f})"
    )

    if match.winning_team in (Team(a_id), Team(b_id)):
        actual = "A" if int(match.winning_team) == a_id else "B"
        print(f"\nactual winner: team {actual}")
    if unknown:
        print(
            f"\nnote: {len(unknown)} player(s) not in the model vocab "
            f"({', '.join(unknown)}) — prediction degrades to UNK for them."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--eval", action="store_true", help="run baseline comparison")
    parser.add_argument(
        "--match-id", type=int, default=None, help="fetch + predict a single match"
    )
    args = parser.parse_args()
    if args.match_id is not None:
        predict_match(args.run_dir, args.match_id)
    elif args.eval:
        evaluate(args.run_dir)
    else:
        load_bundle(args.run_dir)
        print("Loaded model bundle OK (use --eval, or --match-id N).")


if __name__ == "__main__":
    main()
