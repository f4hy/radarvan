"""Match-outcome prediction endpoints (ONNX model)."""

import statistics
import time

import structlog
from cachetools import LRUCache
from cachetools.keys import hashkey
from fastapi import APIRouter, Depends, HTTPException

from .. import ml_inference, replay_files, winprob_inference
from ..api_types import (
    FactionMatchupOption,
    FactionMatchupPrediction,
    FactionMatrix,
    FactionMatrixCell,
    General,
    MatchPrediction,
    PlayerName,
    PredictRequest,
    WinProbOverTime,
)
from ..cache import sorted_deduped_matches
from ..db_utils import ReplayManager
from ..dependencies import get_replay_manager
from ..utils import locked_cached

logger = structlog.get_logger(__name__)

router = APIRouter()

# Recognised generals only (skip UNRECOGNIZED = -1), mirroring ml/features.py's
# closed vocab so every value here is one the model actually has an embedding for.
_RECOGNIZED_GENERALS = [g for g in General if g.value >= 0]

# No real map has this name, so map_idx()/map_feature_vector() both fall through
# to their UNK/train-mean fallback (see ml/features.py) - a legitimate "we don't
# know the map yet" input, not a degenerate one.
_UNKNOWN_MAP_PLACEHOLDER = "Unknown Map"

# Never resolved by player_ids.resolve_player_name (not in NAME_MAPPING) and never
# in the training vocab, so both fall through to the model's UNK player slot -
# used by faction_matrix to strip player identity out entirely and get a pure
# faction-vs-faction signal. Two distinct placeholders only for readability in
# logs; the model sees UNK=0 for both either way.
_UNKNOWN_PLAYER_A = "Unknown Player A"
_UNKNOWN_PLAYER_B = "Unknown Player B"


def _percentile_stats(vals: list[float]) -> tuple[float, float, bool]:
    """mean, std, significant (90% empirical CI across the ensemble excludes
    0.5) - the same percentile method ``ml.bootstrap_matrix`` validated. A
    normal approximation from mean+std alone under-detects here: per-cell
    distributions are visibly non-normal at n=30 (see the conversation that
    led here - a 1.645*std cutoff found 0/144 significant vs. 8/144 by this
    exact percentile method on the same ensemble)."""
    vals = sorted(vals)
    n = len(vals)
    mean = statistics.mean(vals)
    std = statistics.stdev(vals) if n > 1 else 0.0
    lo = vals[max(0, int(n * 0.05))]
    hi = vals[min(n - 1, int(n * 0.95))]
    return mean, std, (lo > 0.5 or hi < 0.5)


# 144 combos x the full N-model ensemble takes ~1.3s, and Bracket.tsx's
# MatchupPopup fires faction_matchup on every open - so the same grid gets
# recomputed constantly for the same handful of tournament pairs. The result
# is a pure function of (map, player1, player2) plus the frozen ONNX weights
# and vocab, none of which change within a process, so an unbounded-lifetime
# LRU is correct here - no TTL needed, unlike the match-derived caches in
# cache.py that must follow new games landing.
_FACTION_GRID_CACHE: LRUCache[tuple[object, ...], list[tuple[object, ...]]] = LRUCache(
    maxsize=256
)


@locked_cached(
    cache=_FACTION_GRID_CACHE,
    key=lambda map_name, player1, player2: hashkey(map_name, player1, player2),
)
def _faction_grid(
    map_name: str, player1: str, player2: str
) -> list[tuple[General, General, float, float, bool, int]]:
    """(general1, general2, prob_player1_wins, std, significant, ensemble_size)
    for every general combination - the 144-call loop shared by
    faction_matchup and faction_matrix. Each cell runs the full N-model
    ensemble (see ``ml_inference.predict_features_raw``).

    Cached (see ``_FACTION_GRID_CACHE``); callers must treat the returned list
    as read-only - it's the shared cached object, not a fresh copy.
    """
    results = []
    for gen1 in _RECOGNIZED_GENERALS:
        for gen2 in _RECOGNIZED_GENERALS:
            probs = ml_inference.predict_features_raw(
                map_name, [(player1, gen1, 1), (player2, gen2, 2)]
            )
            mean, std, significant = _percentile_stats(probs)
            results.append((gen1, gen2, mean, std, significant, len(probs)))
    return results


def _require_model() -> None:
    if not ml_inference.model_available():
        raise HTTPException(
            status_code=503,
            detail="prediction model is not available on this server",
        )


@router.get("/api/predict/match/{match_id}")
def predict_match(
    match_id: int,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> MatchPrediction:
    """Predict the winner of an existing match by id."""
    _require_model()
    match = sorted_deduped_matches(replay_manager).get(match_id)
    if match is None:
        raise HTTPException(status_code=404, detail=f"match {match_id} not found")
    try:
        return ml_inference.predict_match_info(match)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.get("/api/predict/over_time/{match_id}")
def predict_over_time(
    match_id: int,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> WinProbOverTime:
    """Win-probability-over-time curve for an existing match.

    Streams the match's parsed replay JSON from S3 and runs the sequence ONNX
    model, returning P(team A wins) at each 30-second window.
    """
    if not winprob_inference.model_available():
        raise HTTPException(
            status_code=503,
            detail="win-probability model is not available on this server",
        )
    rep = replay_manager.get_replay_json_by_match_id(match_id)
    if rep is None:
        raise HTTPException(status_code=404, detail=f"match {match_id} not found")
    replay = replay_files.parse_json(rep.json_s3_uri)
    result = winprob_inference.predict_over_time(replay)
    if result is None:
        raise HTTPException(
            status_code=422,
            detail="match is not a usable 2-team game (cannot predict over time)",
        )
    return result


@router.post("/api/predict")
def predict_from_features(
    request: PredictRequest,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> MatchPrediction:
    """Predict the winner from raw features: map, players, teams, generals."""
    _require_model()
    # Resolve the map name to its canonical stored form so it matches the vocab.
    map_name = replay_manager.resolve_map_name(request.map_name) or request.map_name
    features = [(p.name, p.general, p.team) for p in request.players]
    try:
        return ml_inference.predict_features(map_name, features)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.get("/api/predict/faction_matchup")
def predict_faction_matchup(
    player1: PlayerName,
    player2: PlayerName,
    map_name: str | None = None,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> FactionMatchupPrediction:
    """Rank every general-vs-general draw for a hypothetical 1v1 between
    player1 and player2, by running the win-prediction model once per
    (player1_general, player2_general) combination - 12x12 = 144 calls.

    Backs the "best possible draws" section of Bracket.tsx's MatchupPopup,
    which calls this on every popup open - hence the grid cache (see
    ``_FACTION_GRID_CACHE``); ``compute_ms`` is near-zero on a cache hit.

    No map is known before the draw; omit map_name to use a placeholder the
    model treats as "unknown" (see ``_UNKNOWN_MAP_PLACEHOLDER``), or pass a
    real map name to fix it.
    """
    _require_model()
    resolved_map = (
        (replay_manager.resolve_map_name(map_name) or map_name)
        if map_name
        else _UNKNOWN_MAP_PLACEHOLDER
    )
    start = time.monotonic()
    grid = _faction_grid(resolved_map, player1, player2)
    options = [
        FactionMatchupOption(
            player1_general=gen1,
            player2_general=gen2,
            prob_player1_wins=prob,
            prob_player1_wins_std=std,
        )
        for gen1, gen2, prob, std, _significant, _n in grid
    ]
    options.sort(key=lambda o: o.prob_player1_wins, reverse=True)
    compute_ms = (time.monotonic() - start) * 1000
    ensemble_size = grid[0][5] if grid else 1
    logger.info(
        "faction matchup grid computed",
        player1=player1,
        player2=player2,
        map_name=resolved_map,
        n_options=len(options),
        ensemble_size=ensemble_size,
        compute_ms=round(compute_ms, 1),
    )
    return FactionMatchupPrediction(
        player1=player1,
        player2=player2,
        map_name=resolved_map,
        options=options,
        ensemble_size=ensemble_size,
        compute_ms=compute_ms,
    )


@router.get("/api/predict/faction_matrix")
def predict_faction_matrix() -> FactionMatrix:
    """The full 12x12 general-vs-general grid with both players and the map
    forced to the model's UNK slot - a pure faction-vs-faction signal with no
    player identity or map mixed in. Same 144-call approach as
    faction_matchup, just with placeholder inputs instead of a real pair of
    players.
    """
    _require_model()
    start = time.monotonic()
    grid = _faction_grid(_UNKNOWN_MAP_PLACEHOLDER, _UNKNOWN_PLAYER_A, _UNKNOWN_PLAYER_B)
    cells = [
        FactionMatrixCell(
            general_a=gen1,
            general_b=gen2,
            prob_a_wins=prob,
            prob_a_wins_std=std,
            significant=significant,
        )
        for gen1, gen2, prob, std, significant, _n in grid
    ]
    probs = sorted(c.prob_a_wins for c in cells)
    mid = len(probs) // 2
    median = (probs[mid - 1] + probs[mid]) / 2 if len(probs) % 2 == 0 else probs[mid]
    compute_ms = (time.monotonic() - start) * 1000
    ensemble_size = grid[0][5] if grid else 1
    logger.info(
        "faction matrix computed",
        n_cells=len(cells),
        n_significant=sum(1 for c in cells if c.significant),
        median_prob_a_wins=round(median, 4),
        ensemble_size=ensemble_size,
        compute_ms=round(compute_ms, 1),
    )
    return FactionMatrix(
        map_name=_UNKNOWN_MAP_PLACEHOLDER,
        median_prob_a_wins=median,
        cells=cells,
        ensemble_size=ensemble_size,
        compute_ms=compute_ms,
    )
