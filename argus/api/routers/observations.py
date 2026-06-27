"""Observations endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request

from argus.api.schemas import ObservationListResponse, ObservationSchema
from argus.core.store import Store

router = APIRouter()


@router.get("/{aoi_id}/observations", response_model=ObservationListResponse)
def list_observations(
    aoi_id: str,
    request: Request,
    status: str | None = None,
    obs_type: str | None = None,
) -> ObservationListResponse:
    """List Observations for an AOI, with optional status/obs_type filters."""
    db_path: Path = request.app.state.db_path
    store = Store(db_path)
    # Observations are keyed by analysis_run_id, not aoi_id directly.
    # Retrieve all runs for this aoi_id then collect their observations.
    with store._connect() as conn:  # noqa: SLF001
        run_rows = conn.execute(
            "SELECT id FROM analysis_runs WHERE aoi_id = ?", (aoi_id,)
        ).fetchall()
    obs_all = []
    for run_row in run_rows:
        obs_all.extend(store.get_observations_for_run(run_row["id"]))
    if status is not None:
        obs_all = [o for o in obs_all if o.status == status]
    if obs_type is not None:
        obs_all = [o for o in obs_all if o.obs_type == obs_type]
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
