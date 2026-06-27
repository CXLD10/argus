"""Argus core data models (v2.0 canonical entity names)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class AOI(BaseModel):
    """Area of Interest — the spatial unit for a monitoring task."""

    id: str
    name: str
    geometry: dict[str, Any]  # GeoJSON geometry object
    domains: list[str]  # e.g. ["marine_oil"]
    params: dict[str, Any] = Field(default_factory=dict)
    active: bool = True
    created_at: datetime | None = None

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        """(min_lon, min_lat, max_lon, max_lat) derived from geometry coordinates."""
        coords = _extract_coords(self.geometry)
        if not coords:
            return (0.0, 0.0, 0.0, 0.0)
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        return (min(lons), min(lats), max(lons), max(lats))


class MonitorTarget(BaseModel):
    """A specific water body or sub-region within an AOI."""

    id: str
    aoi_id: str
    kind: Literal["water_body", "region"]
    name: str
    geometry: dict[str, Any]  # GeoJSON geometry object
    domains: list[str]
    resolution_status: Literal["eligible", "below_resolution"] = "eligible"
    calibration_state: str | None = None
    attrs: dict[str, Any] = Field(default_factory=dict)


class SourceRef(BaseModel):
    """Reference to a satellite product in an external catalogue (e.g. CDSE)."""

    product_id: str
    source: str  # "cdse"
    collection: str  # "SENTINEL-1"
    product_type: str  # "GRD"
    sensor_mode: str  # "IW"
    sensing_time: datetime
    footprint: dict[str, Any]  # GeoJSON geometry
    polarizations: list[str]  # e.g. ["VV", "VH"]
    bytes_estimated: int | None = None
    attrs: dict[str, Any] = Field(default_factory=dict)


class Scene(BaseModel):
    """A downloaded satellite product tied to an AOI — the unit of raster storage."""

    id: str
    product_id: str  # matches SourceRef.product_id
    aoi_id: str
    sensing_time: datetime
    ingest_status: Literal["pending", "ready", "failed"]
    artifact_path: str | None = None  # absolute path to the raster file on disk
    bytes_or_calls: int = 0  # CDSE byte count for daily quota tracking
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    attrs: dict[str, Any] = Field(default_factory=dict)


class AnalysisRun(BaseModel):
    """Execution record for one domain analysis over one scene (v2.0 canonical name)."""

    id: str
    aoi_id: str
    domain_id: str
    scene_id: str
    started_at: datetime
    completed_at: datetime | None = None
    status: Literal["running", "complete", "failed"] = "running"
    n_observations: int = 0


class Observation(BaseModel):
    """A detected or inferred environmental signal (v2.0 canonical name).

    INV-3: every Observation carries evidence_class ∈ {measured, modeled, inferred}.
    SAR dark-spot detections → evidence_class = "measured".
    """

    id: str
    analysis_run_id: str
    scene_id: str
    obs_type: str  # e.g. "oil_slick", "chlorophyll_a"
    evidence_class: Literal["measured", "modeled", "inferred"]
    geometry: dict[str, Any]  # GeoJSON geometry
    area_km2: float
    confidence: float  # 0–1
    status: Literal["candidate", "confirmed", "dismissed"] = "candidate"
    attrs: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


def _extract_coords(geometry: dict[str, Any]) -> list[tuple[float, float]]:
    """Flatten all coordinate pairs from a GeoJSON geometry."""
    gtype = geometry.get("type", "")
    coords: list[Any] = geometry.get("coordinates", [])
    if gtype == "Point":
        return [(float(coords[0]), float(coords[1]))]
    if gtype == "LineString":
        return [(float(c[0]), float(c[1])) for c in coords]
    if gtype == "Polygon":
        return [(float(c[0]), float(c[1])) for ring in coords for c in ring]
    if gtype == "MultiPolygon":
        return [(float(c[0]), float(c[1])) for poly in coords for ring in poly for c in ring]
    return []
