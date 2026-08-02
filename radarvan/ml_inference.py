"""Serve win predictions from an N-model ONNX ensemble - torch-free.

The production app has no torch; ONNX Runtime + numpy is all we need at serving
time. Feature encoding reuses ``ml.features`` (the same torch-free encoder used
for training) so there is no train/serve skew. Every prediction runs through
all N replicates in ``ML_ENSEMBLE_DIR`` and reports the mean plus the spread
across replicates (``*_std``) - with ~1,000 training matches a single model's
point estimate isn't trustworthy on its own (see ``ml.bootstrap_matrix``: most
individual general-matchup effects turned out to be within noise). The
replicates share one vocab (frozen from the same split each was resampled
from - see ``ml.bootstrap_matrix``), so one encoding feeds every session.
Sessions are loaded once and cached. See ``ml/model_design.md``,
``ml/export.py`` and ``ml/bootstrap_matrix.py``.
"""

from __future__ import annotations

import os
import statistics
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

import numpy as np
import onnxruntime as ort
import structlog

from ml.features import (
    EncodedMatch,
    EncodedPlayer,
    Vocab,
    encode_match,
    resolved_real_players,
)

from . import game_composition
from .api_types import General, MatchInfo, MatchPrediction, Player, Team
from .notify import notify

logger = structlog.get_logger(__name__)

ENSEMBLE_DIR = Path(os.getenv("ML_ENSEMBLE_DIR", "ml_ensemble"))

# Must match ml.export.INPUT_NAMES (order is the ONNX graph input order).
_TEAM_A = ["a_player", "a_general", "a_faction", "a_start", "a_mask"]
_TEAM_B = ["b_player", "b_general", "b_faction", "b_start", "b_mask"]


class ModelUnavailable(RuntimeError):
    """Raised when the ONNX ensemble / vocab files are missing."""


@lru_cache(maxsize=1)
def _ensemble_sessions() -> list[ort.InferenceSession]:
    paths = sorted(ENSEMBLE_DIR.glob("model-*.onnx"))
    if not paths:
        raise ModelUnavailable(f"no ensemble models found under {ENSEMBLE_DIR}")
    return [
        ort.InferenceSession(str(p), providers=["CPUExecutionProvider"]) for p in paths
    ]


@lru_cache(maxsize=1)
def _input_names() -> frozenset[str]:
    return frozenset(i.name for i in _ensemble_sessions()[0].get_inputs())


@lru_cache(maxsize=1)
def _vocab() -> Vocab:
    vocab_path = ENSEMBLE_DIR / "vocab.json"
    if not vocab_path.exists():
        raise ModelUnavailable(f"ensemble vocab not found at {vocab_path}")
    return Vocab.load(vocab_path)


def model_available() -> bool:
    return (ENSEMBLE_DIR / "vocab.json").exists() and any(
        ENSEMBLE_DIR.glob("model-*.onnx")
    )


def _feed(enc: EncodedMatch) -> dict[str, np.ndarray]:
    """Pad both teams to equal length and build the ONNX input dict (numpy)."""
    max_t = max(len(enc.team_a), len(enc.team_b))

    def team_arrays(team: list[EncodedPlayer]) -> dict[str, np.ndarray]:
        ids = {
            k: np.zeros((1, max_t), dtype=np.int64)
            for k in ("player", "general", "faction", "start")
        }
        mask = np.zeros((1, max_t), dtype=np.float32)
        for j, p in enumerate(team):
            ids["player"][0, j] = p.player
            ids["general"][0, j] = p.general
            ids["faction"][0, j] = p.faction
            ids["start"][0, j] = p.start_pos
            mask[0, j] = 1.0
        return {**ids, "mask": mask}

    a = team_arrays(enc.team_a)
    b = team_arrays(enc.team_b)
    feed = {
        "a_player": a["player"],
        "a_general": a["general"],
        "a_faction": a["faction"],
        "a_start": a["start"],
        "a_mask": a["mask"],
        "b_player": b["player"],
        "b_general": b["general"],
        "b_faction": b["faction"],
        "b_start": b["start"],
        "b_mask": b["mask"],
        "fmt": np.array([enc.fmt], dtype=np.int64),
    }
    # The map input is either a numeric feature vector or a name index, depending
    # on how the loaded model was trained (see ml/export.py).
    if "map_feat" in _input_names():
        feed["map_feat"] = np.array([enc.map_feat], dtype=np.float32)
    else:
        feed["map"] = np.array([enc.map], dtype=np.int64)
    return feed


def _ensemble_probs(feed: dict[str, np.ndarray]) -> list[float]:
    """P(team A wins) from every replicate in the ensemble, same feed each time."""
    return [
        float(sess.run(["prob_team_a"], feed)[0][0]) for sess in _ensemble_sessions()
    ]


def predict_features_raw(
    map_name: str, players: list[tuple[str, General, int]]
) -> list[float]:
    """Raw per-replicate P(team A wins), one value per ensemble model.

    For callers that need the actual distribution (e.g. an empirical
    percentile interval) rather than just the mean/std summary
    ``predict_features``/``MatchPrediction`` carry - see
    ``ml.bootstrap_matrix``, whose percentile-based significance test this
    mirrors. A normal approximation from mean+std alone under-detects here:
    the per-cell distributions are visibly non-normal at n=30.
    """
    vocab = _vocab()
    built = [
        Player(name=name, general=general, team=team, color="")
        for name, general, team in players
    ]
    match = build_match_info(map_name, built)
    enc = encode_match(match, vocab)
    if enc is None:
        raise ValueError("match is not a usable 2-team game (cannot predict)")
    return _ensemble_probs(_feed(enc))


def predict_match_info(match: MatchInfo) -> MatchPrediction:
    """Predict the winner of a (2-team) match. Raises ValueError if not encodable.

    ``prob_team_a_wins`` is the mean across the ensemble; ``prob_team_a_wins_std``
    is the spread across replicates - a large std means the ensemble disagrees
    with itself, i.e. this particular prediction shouldn't be trusted much.
    """
    vocab = _vocab()
    enc = encode_match(match, vocab)
    if enc is None:
        raise ValueError("match is not a usable 2-team game (cannot predict)")

    probs = _ensemble_probs(_feed(enc))
    prob_a = statistics.mean(probs)
    prob_a_std = statistics.stdev(probs) if len(probs) > 1 else 0.0

    # Re-derive teams from the MatchInfo for the response. encode_match uses the
    # same canonical ordering (team A == lower team id), so these align.
    teams: dict[int, list[tuple[str, bool]]] = {}
    for name, p in resolved_real_players(match):
        teams.setdefault(p.team, []).append((name, vocab.player_idx(name) != 0))
    a_id, b_id = sorted(teams)
    unknown = [n for t in teams.values() for n, known in t if not known]
    favored, fav_prob = (a_id, prob_a) if prob_a >= 0.5 else (b_id, 1.0 - prob_a)

    return MatchPrediction(
        match_id=match.id or None,
        map_name=match.map,
        team_a=a_id,
        team_b=b_id,
        team_a_players=[n for n, _ in teams[a_id]],
        team_b_players=[n for n, _ in teams[b_id]],
        prob_team_a_wins=prob_a,
        prob_team_a_wins_std=prob_a_std,
        ensemble_size=len(probs),
        favored_team=favored,
        favored_win_prob=fav_prob,
        unknown_players=unknown,
    )


def build_match_info(map_name: str, players: list[Player]) -> MatchInfo:
    """Assemble a minimal MatchInfo from raw features for prediction.

    The winner is a placeholder (the lowest team id) only so ``encode_match``
    accepts it; it does not affect the prediction.
    """
    team_ids = sorted({p.team for p in players if p.team > 0})
    if len(team_ids) != 2:
        raise ValueError("prediction requires exactly two teams")
    adapters = [
        game_composition.PlayerAdapter(team=p.team, type=p.Type) for p in players
    ]
    composition = game_composition.categorize_game_type(adapters)
    now = datetime.now(UTC)
    return MatchInfo(
        id=0,
        timestamp=now,
        date=now.date(),
        map=map_name,
        winning_team=Team(team_ids[0]),
        players=players,
        duration_minutes=0.0,
        filename="",
        composition=composition,
    )


def _notify_prediction(
    pred: MatchPrediction, actual: str | None, *, expect_actual: bool
) -> None:
    """Build and emit the notify() message for a prediction.

    ``expect_actual`` distinguishes a played match (report the actual winner, or
    "no decisive winner" when missing) from a hypothetical matchup (no actual).
    """
    predicted = "A" if pred.favored_team == pred.team_a else "B"
    team_a = ", ".join(pred.team_a_players)
    team_b = ", ".join(pred.team_b_players)
    header = (
        f"🔮 Prediction for match {pred.match_id}"
        if pred.match_id is not None
        else "🔮 Hypothetical matchup prediction"
    )
    lines = [
        f"{header} on {pred.map_name}",
        f"Team A ({team_a}) vs Team B ({team_b})",
        f"Predicted: Team {predicted} favored ({pred.favored_win_prob:.0%}; "
        f"P(A wins)={pred.prob_team_a_wins:.0%})",
    ]
    if actual is not None:
        mark = "✅ correct" if actual == predicted else "❌ upset"
        lines.append(f"Actual: Team {actual} won - {mark}")
    elif expect_actual:
        lines.append("Actual: no decisive winner recorded")
    if pred.unknown_players:
        lines.append(f"(unknown to model: {', '.join(pred.unknown_players)})")
    notify("\n".join(lines))


def predict_and_notify(match: MatchInfo) -> None:
    """Best-effort: predict a freshly-registered match and notify pred vs actual.

    Called from the match-registration paths. Any failure - model files absent,
    game not a 2-team game, notify webhook error - is swallowed so registration
    is never affected.
    """
    try:
        if not model_available():
            return
        pred = predict_match_info(match)
        winner = int(match.winning_team)
        actual = (
            "A" if winner == pred.team_a else "B" if winner == pred.team_b else None
        )
        _notify_prediction(pred, actual, expect_actual=True)
    except Exception as e:
        logger.info(
            "prediction notify skipped",
            match_id=getattr(match, "id", None),
            error=repr(e),
        )


def predict_and_notify_features(
    map_name: str, players: list[tuple[str, General, int]]
) -> MatchPrediction | None:
    """Best-effort: predict a hypothetical matchup from features and notify.

    Used by pre-game query endpoints (e.g. map_summary) where there is no actual
    result. Returns the prediction (so callers can surface it) or None on any
    failure, which is swallowed.
    """
    try:
        if not model_available():
            return None
        pred = predict_features(map_name, players)
        _notify_prediction(pred, actual=None, expect_actual=False)
        return pred
    except Exception as e:
        logger.info("prediction notify skipped", error=repr(e))
        return None


def predict_features(
    map_name: str, players: list[tuple[str, General, int]]
) -> MatchPrediction:
    """Predict from raw features: (resolved_name, general, team_id) per player."""
    built = [
        Player(name=name, general=general, team=team, color="")
        for name, general, team in players
    ]
    return predict_match_info(build_match_info(map_name, built))
