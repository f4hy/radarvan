"""Equal-skill scenario predictions: generals, composition and map, no players."""

from fastapi import APIRouter, Depends, HTTPException, Query

from ml.map_features import normalize_map_name

from .. import scenario_inference
from ..api_types import ScenarioModelSummary, ScenarioPick, ScenarioPrediction
from ..cache import maps_by_player_count
from ..db_utils import ReplayManager
from ..dependencies import cache_short, get_replay_manager

router = APIRouter(tags=["scenario"])

MAX_TEAM_SIZE = 4


def _players_by_map(replay_manager: ReplayManager) -> dict[str, int]:
    return {
        normalize_map_name(name): count
        for count, names in maps_by_player_count(replay_manager).items()
        for name in names
    }


def _require_model() -> None:
    if not scenario_inference.model_available():
        raise HTTPException(
            status_code=503, detail="scenario model is not available on this server"
        )


@router.get("/api/scenario/model", dependencies=[Depends(cache_short)])
def scenario_model(
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> ScenarioModelSummary:
    """What the equal-skill model learned: general, matchup, teammate and map effects."""
    _require_model()
    return scenario_inference.summary(_players_by_map(replay_manager))


@router.get("/api/scenario/predict", dependencies=[Depends(cache_short)])
def scenario_predict(
    team_a: list[ScenarioPick] = Query(...),
    team_b: list[ScenarioPick] = Query(...),
    map_name: str | None = None,
    replay_manager: ReplayManager = Depends(get_replay_manager),
) -> ScenarioPrediction:
    """P(team A wins) between equally skilled players for these generals on this map."""
    _require_model()
    if not 1 <= len(team_a) <= MAX_TEAM_SIZE or len(team_a) != len(team_b):
        raise HTTPException(
            status_code=422,
            detail=f"teams must be the same size, 1 to {MAX_TEAM_SIZE} players",
        )
    return scenario_inference.predict(
        team_a, team_b, map_name, _players_by_map(replay_manager)
    )
