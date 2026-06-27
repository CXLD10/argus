"""Load and validate AOI definitions from GeoJSON files."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from shapely.geometry import shape
from shapely.validation import explain_validity

from argus.core.models import AOI

# Reject AOIs larger than this — conserves CDSE quota and avoids over-broad requests.
_MAX_AREA_KM2 = 500_000.0


class AOIError(ValueError):
    """Raised when an AOI file or geometry fails validation."""


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
