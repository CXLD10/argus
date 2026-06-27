"""Load and validate AOI definitions and water-body MonitorTargets from GeoJSON files."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Literal

import yaml
from shapely.geometry import shape
from shapely.validation import explain_validity

from argus.core.errors import AOIError, BelowResolutionError  # noqa: E402 — re-exports
from argus.core.models import AOI, MonitorTarget

# Reject AOIs larger than this — conserves CDSE quota and avoids over-broad requests.
_MAX_AREA_KM2 = 500_000.0

# Minimum water body area for D2 processing (10×10 Sentinel-2 pixels at 10m ≈ 1 ha).
MIN_WATER_BODY_AREA_HA: float = 1.0

__all__ = [
    "AOIError",
    "BelowResolutionError",
    "load_aoi",
    "load_water_body_target",
    "require_eligible",
]


def load_aoi(path: Path) -> AOI:
    """Load and validate an AOI from a GeoJSON Feature file.

    The GeoJSON Feature's ``properties`` must include at least ``id`` and ``domains``.
    Geometry must be a valid Polygon or MultiPolygon within the area cap.
    """
    if not path.exists():
        raise AOIError(f"AOI file not found: {path}")

    with path.open() as fh:
        data = json.load(fh)

    if data.get("type") == "Feature":
        props: dict[str, Any] = data.get("properties") or {}
        geometry: dict[str, Any] = data["geometry"]
    elif data.get("type") in ("Polygon", "MultiPolygon"):
        props = {}
        geometry = data
    else:
        raise AOIError(
            f"Unsupported GeoJSON type {data.get('type')!r}. "
            "Expected 'Feature', 'Polygon', or 'MultiPolygon'."
        )

    _validate_geometry(geometry)

    aoi_id: str = props.get("id") or path.stem
    return AOI(
        id=aoi_id,
        name=props.get("name", aoi_id),
        geometry=geometry,
        domains=list(props.get("domains", [])),
        params=dict(props.get("params", {})),
        active=bool(props.get("active", True)),
        created_at=props.get("created_at"),
    )


def _validate_geometry(geometry: dict[str, Any]) -> None:
    """Validate a GeoJSON geometry dict; raise AOIError on failure."""
    gtype = geometry.get("type", "")
    if gtype not in ("Polygon", "MultiPolygon"):
        raise AOIError(
            f"Geometry type {gtype!r} is not supported. Use 'Polygon' or 'MultiPolygon'."
        )

    geom = shape(geometry)

    if not geom.is_valid:
        raise AOIError(f"Invalid geometry: {explain_validity(geom)}")

    if geom.is_empty:
        raise AOIError("Geometry is empty.")

    area_km2 = _approx_area_km2(geom)
    if area_km2 > _MAX_AREA_KM2:
        raise AOIError(
            f"AOI area ~{area_km2:,.0f} km² exceeds the {_MAX_AREA_KM2:,.0f} km² maximum. "
            "Split into smaller AOIs or reduce the geographic extent."
        )


def _approx_area_km2(geom: Any) -> float:
    """Approximate geodesic area in km² using centroid-latitude scaling."""
    bounds = geom.bounds  # (minx, miny, maxx, maxy)
    center_lat = (bounds[1] + bounds[3]) / 2
    km_per_deg_lon = 111.32 * math.cos(math.radians(center_lat))
    km_per_deg_lat = 111.32
    return float(geom.area * km_per_deg_lon * km_per_deg_lat)


def load_water_body_target(
    geojson_path: Path,
    meta_path: Path | None = None,
    aoi_id: str = "",
) -> MonitorTarget:
    """Load a MonitorTarget(kind="water_body") from a GeoJSON file + optional meta YAML.

    Resolution gate: if the water body is < MIN_WATER_BODY_AREA_HA (1 ha), the target
    is marked ``resolution_status="below_resolution"`` and must not be processed.
    """
    if not geojson_path.exists():
        raise AOIError(f"Water body GeoJSON not found: {geojson_path}")

    with geojson_path.open() as fh:
        data = json.load(fh)

    if data.get("type") == "Feature":
        props: dict[str, Any] = data.get("properties") or {}
        geometry: dict[str, Any] = data["geometry"]
    elif data.get("type") in ("Polygon", "MultiPolygon"):
        props = {}
        geometry = data
    else:
        raise AOIError(
            f"Unsupported GeoJSON type {data.get('type')!r} for water body. "
            "Expected 'Feature', 'Polygon', or 'MultiPolygon'."
        )

    _validate_geometry(geometry)

    meta: dict[str, Any] = {}
    if meta_path and meta_path.exists():
        with meta_path.open() as fh:
            loaded = yaml.safe_load(fh)
            if isinstance(loaded, dict):
                meta = loaded

    geom = shape(geometry)
    area_ha = _approx_area_km2(geom) * 100
    resolution_status: Literal["eligible", "below_resolution"] = (
        "eligible" if area_ha >= MIN_WATER_BODY_AREA_HA else "below_resolution"
    )

    target_id: str = props.get("id") or meta.get("id") or geojson_path.stem
    _skip = {"id", "aoi_id", "name", "domains", "calibration_state", "trophic_class"}
    extra_attrs = {k: v for k, v in meta.items() if k not in _skip}

    return MonitorTarget(
        id=target_id,
        aoi_id=aoi_id or str(props.get("aoi_id") or meta.get("aoi_id", "")),
        kind="water_body",
        name=str(props.get("name") or meta.get("name") or target_id),
        geometry=geometry,
        domains=list(props.get("domains", meta.get("domains", ["inland_wq"]))),
        resolution_status=resolution_status,
        calibration_state=meta.get("calibration_state"),
        attrs={
            "area_ha": round(area_ha, 2),
            "trophic_class": meta.get("trophic_class"),
            **extra_attrs,
        },
    )


def require_eligible(target: MonitorTarget) -> None:
    """Raise BelowResolutionError if the target cannot be processed.

    Call this at the start of Domain.search() for water-body targets.
    """
    if target.resolution_status == "below_resolution":
        raise BelowResolutionError(
            f"MonitorTarget '{target.id}' has resolution_status='below_resolution'. "
            f"Water body must be >= {MIN_WATER_BODY_AREA_HA} ha to be processed by D2. "
            "Verify the water body geometry or use a larger extent."
        )
