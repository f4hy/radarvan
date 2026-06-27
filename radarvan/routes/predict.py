"""Match-outcome prediction endpoints (ONNX model)."""

import structlog
from fastapi import APIRouter, Depends, HTTPException

from .. import ml_inference
from ..api_types import MatchPrediction, PredictRequest
from ..cache import sorted_deduped_matches
from ..db_utils import ReplayManager
from ..dependencies import get_replay_manager

logger = structlog.get_logger(__name__)

router = APIRouter()


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
