"""Waterbody forecast, prediction, observation, and anomaly endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request

from argus.api.schemas import (
    ObservationListResponse,
    ObservationSchema,
    PredictionListResponse,
    PredictionSchema,
    WaterbodyListResponse,
)
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


@router.get(
    "/waterbody/{target_id}/observations",
    response_model=ObservationListResponse,
    tags=["waterbody"],
)
def get_waterbody_observations(
    target_id: str,
    request: Request,
    obs_type: str | None = None,
) -> ObservationListResponse:
    """Return WQ Observations for a water body, optionally filtered by obs_type.

    Observations are keyed directly by target_id (set by the inland_wq domain).
    Supports obs_type filtering for trend charts (e.g. obs_type=chlorophyll_a).
    """
    db_path: Path = request.app.state.db_path
    store = Store(db_path)
    obs_all = store.get_observations_by_target(target_id, obs_types=[obs_type] if obs_type else None)
    items = [
        ObservationSchema(
            id=o.id,
            analysis_run_id=o.analysis_run_id,
            scene_id=o.scene_id,
            obs_type=o.obs_type,
            evidence_class=o.evidence_class,
            geometry=o.geometry,
            area_km2=o.area_km2,
            confidence=o.confidence,
            status=o.status,
            created_at=o.created_at.isoformat(),
        )
        for o in obs_all
    ]
    return ObservationListResponse(items=items, count=len(items))


@router.get(
    "/waterbody/{target_id}/anomalies",
    response_model=PredictionListResponse,
    tags=["waterbody"],
)
def get_waterbody_anomalies(target_id: str, request: Request) -> PredictionListResponse:
    """Return anomaly Predictions linked to a water body's observations.

    Resolves target → source observations → predictions (kind=anomaly).
    """
    db_path: Path = request.app.state.db_path
    store = Store(db_path)
    anomalies = store.get_predictions_for_target(target_id, kind="anomaly")
    items = [_pred_to_schema(p) for p in anomalies]
    return PredictionListResponse(items=items, count=len(items))


@router.get(
    "/waterbodies",
    response_model=WaterbodyListResponse,
    tags=["waterbody"],
)
def list_waterbodies(request: Request) -> WaterbodyListResponse:
    """List all water body target IDs that have WQ observations in the store."""
    db_path: Path = request.app.state.db_path
    store = Store(db_path)
    target_ids = store.get_waterbody_targets()
    return WaterbodyListResponse(target_ids=target_ids, count=len(target_ids))
