"""AOI endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from argus.aoi.loader import AOIError, load_aoi
from argus.api.schemas import AOIListResponse, AOISchema

router = APIRouter()


@router.get("", response_model=AOIListResponse)
def list_aois(request: Request) -> AOIListResponse:
    """List all configured AOIs from the config directory."""
    config_dir: Path = request.app.state.config_dir
    aoi_dir = config_dir / "aois"
    aois = []
    if aoi_dir.exists():
        for path in sorted(aoi_dir.glob("*.geojson")):
            try:
                aoi = load_aoi(path)
                aois.append(
                    AOISchema(
                        id=aoi.id,
                        name=aoi.name,
                        geometry=aoi.geometry,
                        domains=aoi.domains,
                        active=aoi.active,
                    )
                )
            except AOIError:
                continue
    return AOIListResponse(items=aois, count=len(aois))


@router.get("/{aoi_id}", response_model=AOISchema)
def get_aoi(aoi_id: str, request: Request) -> AOISchema:
    """Return a single AOI by ID."""
    config_dir: Path = request.app.state.config_dir
    aoi_dir = config_dir / "aois"
    path = aoi_dir / f"{aoi_id}.geojson"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"AOI '{aoi_id}' not found")
    try:
        aoi = load_aoi(path)
    except AOIError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return AOISchema(
        id=aoi.id,
        name=aoi.name,
        geometry=aoi.geometry,
        domains=aoi.domains,
        active=aoi.active,
    )
