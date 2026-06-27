"""F-004 tests: land mask rasterization from GeoJSON coastline."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from shapely.geometry import shape

from argus.preprocess.landmask import GeoTransform, load_coastline, rasterize_land_mask

_COASTLINE = Path(__file__).parent.parent / "data" / "static" / "coastline.geojson"


def _left_half_polygon() -> object:
    """A rectangular polygon covering the left half of the Tobago AOI extent."""
    return shape(
        {
            "type": "Polygon",
            "coordinates": [
                [
                    [-61.2, 10.8],
                    [-60.75, 10.8],
                    [-60.75, 11.5],
                    [-61.2, 11.5],
                    [-61.2, 10.8],
                ]
            ],
        }
    )


def _small_transform(cols: int = 10, rows: int = 10) -> GeoTransform:
    return GeoTransform(
        min_lon=-61.2,
        min_lat=10.8,
        max_lon=-60.3,
        max_lat=11.5,
        cols=cols,
        rows=rows,
    )


def test_rasterize_left_half_has_correct_shape() -> None:
    geom = _left_half_polygon()
    tr = _small_transform(10, 10)
    mask = rasterize_land_mask(geom, tr)
    assert mask.shape == (10, 10)


def test_rasterize_left_half_dtype_bool() -> None:
    geom = _left_half_polygon()
    mask = rasterize_land_mask(geom, _small_transform())
    assert mask.dtype == bool


def test_rasterize_left_half_land_columns() -> None:
    # 10 columns: col 0-4 are land (centres in left half), col 5-9 are water
    geom = _left_half_polygon()
    tr = _small_transform(10, 10)
    mask = rasterize_land_mask(geom, tr)
    # lon_res = 0.9/10 = 0.09; col 4 centre = -61.2 + 4.5*0.09 = -60.795 → inside [-61.2, -60.75]
    # col 5 centre = -61.2 + 5.5*0.09 = -60.705 → outside
    assert np.all(mask[:, :5])  # all rows, first 5 cols = land
    assert not np.any(mask[:, 5:])  # all rows, last 5 cols = water


def test_rasterize_empty_polygon_all_water() -> None:
    empty = shape(
        {
            "type": "Polygon",
            "coordinates": [[[0, 0], [0.001, 0], [0.001, 0.001], [0, 0.001], [0, 0]]],
        }
    )
    tr = _small_transform(10, 10)
    mask = rasterize_land_mask(empty, tr)
    assert not np.any(mask)


def test_load_coastline_returns_geometry() -> None:
    geom = load_coastline(_COASTLINE)
    assert geom is not None
    assert not geom.is_empty
    assert geom.is_valid


def test_tobago_coastline_intersects_aoi_extent() -> None:
    from shapely.geometry import box

    geom = load_coastline(_COASTLINE)
    aoi_box = box(-61.2, 10.8, -60.3, 11.5)
    assert aoi_box.intersects(geom)


def test_tobago_coastline_rasterized_has_land_and_water() -> None:
    # Using the actual Tobago coastline and the full 100x100 AOI grid,
    # there should be both land pixels (island) and water pixels (surrounding sea).
    geom = load_coastline(_COASTLINE)
    tr = GeoTransform(min_lon=-61.2, min_lat=10.8, max_lon=-60.3, max_lat=11.5, cols=100, rows=100)
    mask = rasterize_land_mask(geom, tr)
    # Island should cover some but not all pixels
    assert np.any(mask), "Expected some land pixels for Tobago island"
    assert not np.all(mask), "Expected some water pixels around Tobago"


def test_geo_transform_lon_res() -> None:
    tr = GeoTransform(min_lon=-61.2, min_lat=10.8, max_lon=-60.3, max_lat=11.5, cols=100, rows=100)
    assert abs(tr.lon_res - 0.009) < 1e-10


def test_geo_transform_lat_res() -> None:
    tr = GeoTransform(min_lon=-61.2, min_lat=10.8, max_lon=-60.3, max_lat=11.5, cols=100, rows=100)
    assert abs(tr.lat_res - 0.007) < 1e-10
