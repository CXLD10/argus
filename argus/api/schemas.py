"""Pydantic response schemas for the Argus API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

_OPEN_METEO_ATTRIBUTION = "Weather data by Open-Meteo.com (CC BY 4.0)"


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"


class AOISchema(BaseModel):
    id: str
    name: str
    geometry: dict[str, Any]
    domains: list[str]
    active: bool


class AOIListResponse(BaseModel):
    items: list[AOISchema]
    count: int


class ObservationSchema(BaseModel):
    id: str
    analysis_run_id: str
    scene_id: str
    obs_type: str
    evidence_class: str
    geometry: dict[str, Any]
    area_km2: float
    confidence: float
    status: str
    created_at: str


class ObservationListResponse(BaseModel):
    items: list[ObservationSchema]
    count: int


class ForecastFrameSchema(BaseModel):
    id: str
    prediction_id: str
    valid_at: str
    footprint: dict[str, Any]
    particle_count: int
    stats: dict[str, Any]


class PredictionSchema(BaseModel):
    id: str
    predictor_id: str
    kind: str
    evidence_class: str
    uncertainty: dict[str, Any]
    created_at: str
    frames: list[ForecastFrameSchema] = []


class PredictionListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[PredictionSchema]
    count: int
    # Serialized as "_attribution" to satisfy CC-BY-4.0 attribution requirement.
    attribution: str = Field(default=_OPEN_METEO_ATTRIBUTION, alias="_attribution")


class ImpactAssessmentSchema(BaseModel):
    id: str
    prediction_id: str
    exposure_layer_id: str
    valid_at: str
    eta_hours: float
    metrics: dict[str, Any]


class ImpactListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[ImpactAssessmentSchema]
    count: int
    # Serialized as "_attribution" to satisfy CC-BY-4.0 attribution requirement.
    attribution: str = Field(default=_OPEN_METEO_ATTRIBUTION, alias="_attribution")
