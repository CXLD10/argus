"""Impact assessor — intersects ForecastFrame footprints with ExposureLayer geometries.

For each exposure layer, finds the first ForecastFrame (ordered by valid_at) whose
footprint intersects the layer. That frame's valid_at is the ETA. One ImpactAssessment
is produced per layer that is hit; layers with no intersection produce nothing.
"""

from __future__ import annotations

import json
import math
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import shapely
from shapely.geometry import shape

from argus.core.models import ExposureLayer, ForecastFrame, ImpactAssessment, Prediction


def load_exposure_layer(path: Path) -> ExposureLayer:
    """Load an ExposureLayer from a GeoJSON Feature file."""
    data = json.loads(path.read_text())
    props = data.get("properties", {})
    layer_type = props.get("layer_type", "coastline")
    geom = data.get("geometry", data)
    return ExposureLayer(
        id=path.stem,
        name=props.get("name", path.stem),
        layer_type=layer_type,
        geometry=geom,
    )


def _geom_length_km(geom: shapely.geometry.base.BaseGeometry) -> float:
    """Approximate length in km for a shapely geometry (degree units → km).

    Uses shapely's .length (Euclidean in degree coords) × 111.19 km/degree.
    Handles GeometryCollections by summing sub-geometry lengths.
    """
    if geom.is_empty:
        return 0.0
    if hasattr(geom, "geoms"):
        return round(sum(_geom_length_km(g) for g in geom.geoms), 4)
    return round(float(geom.length) * 111.19, 4)


def _geom_area_km2(geom: shapely.geometry.base.BaseGeometry) -> float:
    """Approximate area in km² for a planar shapely geometry in degree coordinates."""
    if geom.is_empty:
        return 0.0
    lat_c = (geom.bounds[1] + geom.bounds[3]) / 2
    return round(float(geom.area) * (111.19**2) * math.cos(math.radians(lat_c)), 4)


def _impact_metrics(layer: ExposureLayer, intersection: Any) -> dict[str, Any]:
    """Compute layer-type-specific metrics from the footprint/layer intersection."""
    if layer.layer_type == "coastline":
        return {"coast_length_km": _geom_length_km(intersection)}
    if layer.layer_type == "marine_protected_area":
        return {"mpa_area_km2": _geom_area_km2(intersection)}
    return {}


def assess_impact(
    prediction: Prediction,
    frames: list[ForecastFrame],
    exposure_layers: list[ExposureLayer],
    t0: datetime,
) -> list[ImpactAssessment]:
    """Compute ETA and impact metrics for each exposure layer.

    For each layer, iterates ForecastFrames in valid_at order. Returns one
    ImpactAssessment per layer that is intersected; layers with no intersection
    produce no record.
    """
    sorted_frames = sorted(frames, key=lambda f: f.valid_at)
    assessments: list[ImpactAssessment] = []

    for layer in exposure_layers:
        layer_geom = shape(layer.geometry)
        for frame in sorted_frames:
            footprint_geom = shape(frame.footprint)
            if not footprint_geom.intersects(layer_geom):
                continue
            intersection = footprint_geom.intersection(layer_geom)
            t0_aware = t0 if t0.tzinfo is not None else t0.replace(tzinfo=UTC)
            frame_ts = (
                frame.valid_at
                if frame.valid_at.tzinfo is not None
                else frame.valid_at.replace(tzinfo=UTC)
            )
            eta_hours = (frame_ts - t0_aware).total_seconds() / 3600
            assessments.append(
                ImpactAssessment(
                    id=str(uuid.uuid4()),
                    prediction_id=prediction.id,
                    exposure_layer_id=layer.id,
                    valid_at=frame.valid_at,
                    eta_hours=round(eta_hours, 2),
                    metrics=_impact_metrics(layer, intersection),
                )
            )
            break  # first intersection per layer = ETA

    return assessments
