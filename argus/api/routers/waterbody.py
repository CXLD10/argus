"""Waterbody forecast and raw-prediction endpoints (F-029 skill gate)."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request

from argus.api.schemas import PredictionListResponse, PredictionSchema
from argus.core.models import Prediction
from argus.core.store import Store
from argus.eval import skill_gate

router = APIRouter()


def _pred_to_schema(pred: Prediction) -> PredictionSchema:
    return PredictionSchema(
        id=pred.id,
        predictor_id=pred.predictor_id,
        kind=pred.kind,
        evidence_class=pred.evidence_class,
        uncertainty=pred.uncertainty,
        created_at=pred.created_at.isoformat(),
        frames=[],
    )


@router.get(
    "/waterbody/{target_id}/forecasts",
    response_model=PredictionListResponse,
    tags=["waterbody"],
)
def get_waterbody_forecasts(target_id: str, request: Request) -> PredictionListResponse:
    """Return gate-validated forecast Predictions for a water body.

    Only predictions from predictors with a passing SkillReport are included.
    Unvalidated predictors are excluded to protect UI trust (F-029 skill gate).
    """
    db_path: Path = request.app.state.db_path
    store = Store(db_path)
    all_forecasts = store.get_predictions_by_kind("forecast")
    gated = skill_gate.gate_predictions(all_forecasts, store)
    items = [_pred_to_schema(p) for p in gated]
    return PredictionListResponse(items=items, count=len(items))


@router.get(
    "/waterbody/{target_id}/raw_predictions",
    response_model=PredictionListResponse,
    tags=["waterbody"],
)
def get_waterbody_raw_predictions(target_id: str, request: Request) -> PredictionListResponse:
    """Return all forecast Predictions for a water body, including unvalidated ones.

    Intended for internal review before a predictor passes the skill gate.
    """
    db_path: Path = request.app.state.db_path
    store = Store(db_path)
    all_forecasts = store.get_predictions_by_kind("forecast")
    items = [_pred_to_schema(p) for p in all_forecasts]
    return PredictionListResponse(items=items, count=len(items))
