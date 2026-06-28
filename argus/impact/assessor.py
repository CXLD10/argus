"""Impact assessor — intersects spatial footprints with ExposureLayer geometries.

D1 (marine oil): intersects ForecastFrame footprints with coastal/MPA layers.
D2 (inland WQ): intersects water-body polygon with drinking-intake / recreation-site layers
when a bloom-risk prediction exceeds a threshold.

One ImpactAssessment is produced per layer that is hit; layers with no intersection
produce nothing.
"""

from __future__ import annotations

import json
import math
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import shapely
from shapely.geometry import shape

from argus.core.models import ExposureLayer, ForecastFrame, ImpactAssessment, Prediction

# Bloom risk thresholds for the D2 WQ impact trigger.
_BLOOM_ANOMALY_SIGMA_DEFAULT: float = 2.5  # z-score units
_BLOOM_FORECAST_VALUE_DEFAULT: float = 25.0  # µg/L chlorophyll-a

_WQ_LAYER_TYPES: frozenset[str] = frozenset({"drinking_intake", "recreation_site"})


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
    if layer.layer_type == "drinking_intake":
        return {"intakes_threatened": 1}
    if layer.layer_type == "recreation_site":
        return {"recreation_sites_threatened": 1}
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


def _prediction_exceeds_bloom_threshold(
    prediction: Prediction,
    anomaly_sigma_threshold: float,
    forecast_value_threshold: float,
) -> bool:
    """Return True if the prediction's bloom-risk signal exceeds its kind-specific threshold."""
    if prediction.kind == "anomaly":
        return bool(abs(float(prediction.attrs.get("z_score", 0.0))) >= anomaly_sigma_threshold)
    if prediction.kind == "forecast":
        return bool(float(prediction.attrs.get("value", 0.0)) >= forecast_value_threshold)
    return False


def assess_wq_impact(
    prediction: Prediction,
    water_body_geom: dict[str, Any],
    exposure_layers: list[ExposureLayer],
    *,
    anomaly_sigma_threshold: float = _BLOOM_ANOMALY_SIGMA_DEFAULT,
    forecast_value_threshold: float = _BLOOM_FORECAST_VALUE_DEFAULT,
    t0: datetime | None = None,
) -> list[ImpactAssessment]:
    """Assess WQ impact on drinking intakes and recreation sites.

    When a bloom-risk prediction exceeds the threshold, intersects the water body
    polygon with each WQ exposure layer (drinking_intake, recreation_site) and
    returns one ImpactAssessment per layer that is hit.

    Non-WQ layer types (coastline, marine_protected_area) are ignored.
    Returns [] if the prediction does not exceed the threshold.
    """
    if not _prediction_exceeds_bloom_threshold(
        prediction, anomaly_sigma_threshold, forecast_value_threshold
    ):
        return []

    # ETA: anomaly = immediate (0 h); forecast = forecast horizon
    if prediction.kind == "anomaly":
        eta_hours = 0.0
    else:
        eta_hours = float(prediction.attrs.get("horizon_days", 7)) * 24.0

    t0_aware = t0 or datetime.now(UTC)
    if t0_aware.tzinfo is None:
        t0_aware = t0_aware.replace(tzinfo=UTC)
    valid_at = t0_aware + timedelta(hours=eta_hours)

    water_body = shape(water_body_geom)
    assessments: list[ImpactAssessment] = []

    for layer in exposure_layers:
        if layer.layer_type not in _WQ_LAYER_TYPES:
            continue
        layer_geom = shape(layer.geometry)
        if layer_geom.is_empty:
            continue
        if not water_body.intersects(layer_geom):
            continue
        intersection = water_body.intersection(layer_geom)
        assessments.append(
            ImpactAssessment(
                id=str(uuid.uuid4()),
                prediction_id=prediction.id,
                exposure_layer_id=layer.id,
                valid_at=valid_at,
                eta_hours=eta_hours,
                metrics=_impact_metrics(layer, intersection),
            )
        )

    return assessments
