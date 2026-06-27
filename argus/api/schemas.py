"""Pydantic response schemas for the Argus API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from argus import __version__

_OPEN_METEO_ATTRIBUTION = "Weather data by Open-Meteo.com (CC BY 4.0)"


class HealthResponse(BaseModel):
    status: str = Field(default="ok", description="Always 'ok' if the server is running.")
    version: str = Field(
        default_factory=lambda: __version__,
        description="Argus package version.",
    )


class AOISchema(BaseModel):
    id: str = Field(description="Unique AOI identifier (slug).")
    name: str = Field(description="Human-readable AOI name.")
    geometry: dict[str, Any] = Field(description="GeoJSON geometry of the area of interest.")
    domains: list[str] = Field(description="Domain IDs enabled for this AOI (e.g. 'marine_oil').")
    active: bool = Field(description="Whether this AOI is scheduled for monitoring.")


class AOIListResponse(BaseModel):
    items: list[AOISchema] = Field(description="List of AOI objects.")
    count: int = Field(description="Total number of items returned.")


class ObservationSchema(BaseModel):
    id: str = Field(description="Unique observation ID.")
    analysis_run_id: str = Field(
        description="ID of the AnalysisRun that produced this observation."
    )
    scene_id: str = Field(description="Source scene (satellite product) ID.")
    obs_type: str = Field(
        description="Observation type, e.g. 'oil_slick', 'chlorophyll_a', 'turbidity'."
    )
    evidence_class: Literal["measured", "modeled", "inferred"] = Field(
        description="Evidence provenance (INV-3). 'measured' = directly observable from orbit."
    )
    geometry: dict[str, Any] = Field(description="GeoJSON geometry of the detected feature.")
    area_km2: float = Field(description="Estimated area in km².")
    confidence: float = Field(description="Classifier confidence in [0, 1].", ge=0.0, le=1.0)
    status: str = Field(
        description="Review status: 'candidate', 'confirmed', 'dismissed', 'archived'."
    )
    created_at: str = Field(description="ISO-8601 UTC timestamp when the observation was created.")


class ObservationListResponse(BaseModel):
    items: list[ObservationSchema] = Field(description="List of observation objects.")
    count: int = Field(description="Total number of items returned.")


class ForecastFrameSchema(BaseModel):
    id: str = Field(description="Unique forecast-frame ID.")
    prediction_id: str = Field(description="Parent Prediction ID.")
    valid_at: str = Field(description="ISO-8601 UTC timestamp this frame is valid at.")
    footprint: dict[str, Any] = Field(
        description="GeoJSON Polygon enclosing the particle cloud at this timestep."
    )
    particle_count: int = Field(description="Number of simulated particles in this frame.")
    stats: dict[str, Any] = Field(
        description="Aggregate stats: mean_lon, mean_lat, spread_km, etc."
    )


class PredictionSchema(BaseModel):
    id: str = Field(description="Unique prediction ID.")
    predictor_id: str = Field(description="Predictor that produced this prediction.")
    kind: str = Field(description="Prediction kind, e.g. 'trajectory'.")
    evidence_class: str = Field(description="Always 'modeled' for predictions (INV-3).")
    uncertainty: dict[str, Any] = Field(
        description="Uncertainty quantification (INV-9). Must be non-empty."
    )
    created_at: str = Field(description="ISO-8601 UTC timestamp when the prediction was created.")
    frames: list[ForecastFrameSchema] = Field(
        default=[], description="Embedded ForecastFrames sorted by valid_at."
    )


class PredictionListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[PredictionSchema] = Field(description="List of prediction objects.")
    count: int = Field(description="Total number of items returned.")
    # Serialized as "_attribution" to satisfy CC-BY-4.0 attribution requirement.
    attribution: str = Field(
        default=_OPEN_METEO_ATTRIBUTION,
        alias="_attribution",
        description="Open-Meteo CC BY 4.0 attribution (required by data licence).",
    )


class ImpactAssessmentSchema(BaseModel):
    id: str = Field(description="Unique impact-assessment ID.")
    prediction_id: str = Field(description="Source Prediction ID.")
    exposure_layer_id: str = Field(description="Exposure layer that was intersected.")
    valid_at: str = Field(description="ISO-8601 UTC timestamp of the first intersection frame.")
    eta_hours: float = Field(description="Estimated time of arrival in hours from prediction T0.")
    metrics: dict[str, Any] = Field(
        description="Impact metrics: coast_length_km, mpa_area_km2, etc."
    )


class ImpactListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[ImpactAssessmentSchema] = Field(description="List of impact-assessment objects.")
    count: int = Field(description="Total number of items returned.")
    # Serialized as "_attribution" to satisfy CC-BY-4.0 attribution requirement.
    attribution: str = Field(
        default=_OPEN_METEO_ATTRIBUTION,
        alias="_attribution",
        description="Open-Meteo CC BY 4.0 attribution (required by data licence).",
    )
