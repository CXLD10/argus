"""Predictions endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request

from argus.api.schemas import ForecastFrameSchema, PredictionListResponse, PredictionSchema
from argus.core.store import Store

router = APIRouter()


@router.get(
    "/{aoi_id}/predictions", response_model=PredictionListResponse, response_model_by_alias=True
)
def list_predictions(aoi_id: str, request: Request) -> PredictionListResponse:
    """List Predictions (with embedded ForecastFrames) for an AOI."""
    db_path: Path = request.app.state.db_path
    store = Store(db_path)
    with store._connect() as conn:  # noqa: SLF001
        pred_rows = conn.execute(
            """
            SELECT DISTINCT p.id FROM predictions p
            JOIN observations o ON o.id = p.source_obs_ids
            JOIN analysis_runs r ON r.id = o.analysis_run_id
            WHERE r.aoi_id = ?
            """,
            (aoi_id,),
        ).fetchall()
    # Fallback: retrieve all predictions (they're keyed globally; filter by obs source is best-effort)
    if not pred_rows:
        with store._connect() as conn:  # noqa: SLF001
            pred_rows = conn.execute("SELECT id FROM predictions").fetchall()

    items = []
    for row in pred_rows:
        pred = store.get_prediction(row["id"])
        if pred is None:
            continue
        frames = store.get_forecast_frames_for_prediction(pred.id)
        frame_schemas = [
            ForecastFrameSchema(
                id=f.id,
                prediction_id=f.prediction_id,
                valid_at=f.valid_at.isoformat(),
                footprint=f.footprint,
                particle_count=f.particle_count,
                stats=f.stats,
            )
            for f in frames
        ]
        items.append(
            PredictionSchema(
                id=pred.id,
                predictor_id=pred.predictor_id,
                kind=pred.kind,
                evidence_class=pred.evidence_class,
                uncertainty=pred.uncertainty,
                created_at=pred.created_at.isoformat(),
                frames=frame_schemas,
            )
        )
    return PredictionListResponse(items=items, count=len(items))
