"""Hydro endpoints: choke points, flood risk, acid deposition risk."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request

from argus.api.schemas import (
    ChokePointListResponse,
    ChokePointSchema,
    RiskPredictionListResponse,
    RiskPredictionSchema,
)
from argus.core.store import Store

router = APIRouter()


@router.get(
    "/{aoi_id}/choke-points",
    response_model=ChokePointListResponse,
    tags=["hydro"],
    summary="List choke points for an AOI (D4).",
)
def list_choke_points(aoi_id: str, request: Request) -> ChokePointListResponse:
    """Return all choke points for the given AOI, sorted by constriction_score descending."""
    db_path: Path = request.app.state.db_path
    store = Store(db_path)
    choke_points = store.get_choke_points(aoi_id)
    items = [
        ChokePointSchema(
            id=cp.id,
            aoi_id=cp.aoi_id,
            location=cp.location,
            upstream_area_km2=cp.upstream_area_km2,
            constriction_score=cp.constriction_score,
            dem_source=cp.dem_source,
            evidence_class=cp.evidence_class,
        )
        for cp in choke_points
    ]
    return ChokePointListResponse(items=items, count=len(items))


@router.get(
    "/{aoi_id}/flood-risk",
    response_model=RiskPredictionListResponse,
    tags=["hydro"],
    summary="Latest FloodRisk predictions for an AOI (D3/D4).",
)
def list_flood_risk(aoi_id: str, request: Request) -> RiskPredictionListResponse:
    """Return FloodRisk predictions (predictor_id=FloodRisk) for the given AOI."""
    db_path: Path = request.app.state.db_path
    store = Store(db_path)
    predictions = store.get_predictions_by_predictor("FloodRisk")
    items = [
        RiskPredictionSchema(
            id=pred.id,
            predictor_id=pred.predictor_id,
            kind=pred.kind,
            evidence_class=pred.evidence_class,
            label=pred.attrs.get("label", "modeled flood risk (not a measured flood)"),
            risk_score=pred.uncertainty.get("risk_score"),
            risk_level=pred.attrs.get("risk_level"),
            acid_risk_index=None,
            uncertainty=pred.uncertainty,
            created_at=pred.created_at.isoformat(),
        )
        for pred in predictions
        if pred.attrs.get("aoi_id") == aoi_id
    ]
    return RiskPredictionListResponse(items=items, count=len(items))


@router.get(
    "/{aoi_id}/acid-risk",
    response_model=RiskPredictionListResponse,
    tags=["hydro"],
    summary="Latest AcidDepositionRisk predictions for an AOI (D3).",
)
def list_acid_risk(aoi_id: str, request: Request) -> RiskPredictionListResponse:
    """Return AcidDepositionRisk predictions for the given AOI."""
    db_path: Path = request.app.state.db_path
    store = Store(db_path)
    predictions = store.get_predictions_by_predictor("AcidDepositionRisk")
    items = [
        RiskPredictionSchema(
            id=pred.id,
            predictor_id=pred.predictor_id,
            kind=pred.kind,
            evidence_class=pred.evidence_class,
            label=pred.attrs.get(
                "label",
                "modeled acid-deposition risk index (0–10 scale) — NOT a pH measurement",
            ),
            risk_score=None,
            risk_level=None,
            acid_risk_index=pred.attrs.get("acid_risk_index"),
            uncertainty=pred.uncertainty,
            created_at=pred.created_at.isoformat(),
        )
        for pred in predictions
        if pred.attrs.get("aoi_id") == aoi_id
    ]
    return RiskPredictionListResponse(items=items, count=len(items))
