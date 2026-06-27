"""Impact assessment endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request

from argus.api.schemas import ImpactAssessmentSchema, ImpactListResponse
from argus.core.store import Store

router = APIRouter()


@router.get("/{aoi_id}/impact", response_model=ImpactListResponse, response_model_by_alias=True)
def list_impact(aoi_id: str, request: Request) -> ImpactListResponse:
    """List ImpactAssessments for all predictions in an AOI."""
    db_path: Path = request.app.state.db_path
    store = Store(db_path)
    # Retrieve all predictions, then their impact assessments.
    with store._connect() as conn:  # noqa: SLF001
        pred_rows = conn.execute("SELECT id FROM predictions").fetchall()
    items = []
    for row in pred_rows:
        ias = store.get_impact_assessments_for_prediction(row["id"])
        for ia in ias:
            items.append(
                ImpactAssessmentSchema(
                    id=ia.id,
                    prediction_id=ia.prediction_id,
                    exposure_layer_id=ia.exposure_layer_id,
                    valid_at=ia.valid_at.isoformat(),
                    eta_hours=ia.eta_hours,
                    metrics=ia.metrics,
                )
            )
    return ImpactListResponse(items=items, count=len(items))
