"""Argus core data models (v2.0 canonical entity names)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

# Registered obs_type values — any new domain must extend this set.
VALID_OBS_TYPES: frozenset[str] = frozenset(
    {
        "oil_slick",
        "chlorophyll_a",
        "turbidity",
        "cdom",
        "surface_temp",
        "inundation",
    }
)


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
    Schema is frozen at v2.0; any change requires a store migration.
    """

    id: str
    analysis_run_id: str
    scene_id: str
    obs_type: str  # validated against VALID_OBS_TYPES
    evidence_class: Literal["measured", "modeled", "inferred"]
    geometry: dict[str, Any]  # GeoJSON geometry
    area_km2: float
    confidence: float  # 0–1
    status: Literal["candidate", "confirmed", "dismissed"] = "candidate"
    # Status transition timestamp — set when status moves from "candidate".
    status_updated_at: datetime | None = None
    # Feature vector (shape/contrast/spectral) — mirrors DATA_MODELS §Observation.features.
    features: dict[str, Any] | None = None
    # Optional DATA_MODELS fields (populated by domain-aware consumers).
    domain: str | None = None
    target_id: str | None = None
    value: float | None = None
    unit: str | None = None
    attrs: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("obs_type")
    @classmethod
    def _check_obs_type(cls, v: str) -> str:
        if v not in VALID_OBS_TYPES:
            raise ValueError(f"obs_type {v!r} not in registered types: {sorted(VALID_OBS_TYPES)}")
        return v


class Prediction(BaseModel):
    """Tier-A predictor output — trajectory, forecast, risk, or anomaly.

    INV-9: uncertainty field is required and must be non-empty.
    INV-8: rng_seed must be provided for stochastic predictors.
    """

    id: str
    predictor_id: str
    source_obs_ids: list[str] = Field(default_factory=list)
    kind: Literal["forecast", "risk", "anomaly", "trajectory"]
    evidence_class: Literal["measured", "modeled", "inferred"] = "modeled"
    uncertainty: dict[str, Any]  # INV-9: required; ensemble spread / CI / probability
    rng_seed: int | None = None  # INV-8: required for stochastic predictors
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    attrs: dict[str, Any] = Field(default_factory=dict)


class ForecastFrame(BaseModel):
    """One timestep output from an oil trajectory simulation (kind='trajectory')."""

    id: str
    prediction_id: str
    valid_at: datetime
    footprint: dict[str, Any]  # GeoJSON probability footprint polygon
    grid_ref: str | None = None  # path to particle grid raster (if any)
    particle_count: int = 0
    stats: dict[str, Any] = Field(default_factory=dict)  # min/mean/max drift distance


class ExposureLayer(BaseModel):
    """A static spatial layer representing something that can be impacted."""

    id: str
    name: str
    layer_type: Literal["coastline", "marine_protected_area"]
    geometry: dict[str, Any]  # GeoJSON geometry (LineString or Polygon)
    attrs: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ImpactAssessment(BaseModel):
    """ETA + quantified impact for one trajectory prediction × exposure layer pair."""

    id: str
    prediction_id: str
    exposure_layer_id: str
    valid_at: datetime  # valid_at of the first intersecting ForecastFrame (= ETA)
    eta_hours: float  # hours from prediction t0 to first intersection
    metrics: dict[str, Any]  # coast_length_km | mpa_area_km2
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
