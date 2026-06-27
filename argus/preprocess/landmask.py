"""Land mask generation: rasterize coastline polygons onto a numpy grid."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import shapely
from shapely.geometry import shape

_DEFAULT_COASTLINE = Path(__file__).parent.parent.parent / "data" / "static" / "coastline.geojson"


@dataclass
class GeoTransform:
    """Pixel ↔ geographic coordinate mapping for a regularly-spaced raster."""

    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float
    cols: int
    rows: int

    @property
    def lon_res(self) -> float:
        return (self.max_lon - self.min_lon) / self.cols

    @property
    def lat_res(self) -> float:
        return (self.max_lat - self.min_lat) / self.rows


def load_coastline(path: Path = _DEFAULT_COASTLINE) -> Any:
    """Load a GeoJSON file and return a unified shapely geometry."""
    with path.open() as fh:
        data = json.load(fh)

    gtype = data.get("type", "")
    if gtype == "FeatureCollection":
        geoms = np.array(
            [shape(f["geometry"]) for f in data["features"]],
            dtype=object,
        )
        return shapely.union_all(geoms)
    if gtype == "Feature":
        return shape(data["geometry"])
    return shape(data)


def rasterize_land_mask(
    land_geom: Any,
    transform: GeoTransform,
) -> np.ndarray:
    """Return a boolean (rows, cols) mask; True = land.

    Uses shapely 2.0 vectorised point-in-polygon on pixel centres.
    """
    rows, cols = transform.rows, transform.cols
    lons = transform.min_lon + (np.arange(cols) + 0.5) * transform.lon_res
    lats = transform.max_lat - (np.arange(rows) + 0.5) * transform.lat_res
    lon_grid, lat_grid = np.meshgrid(lons, lats)

    points = shapely.points(lon_grid.ravel(), lat_grid.ravel())
    is_land: np.ndarray = shapely.contains(land_geom, points).reshape(rows, cols)
    return is_land
