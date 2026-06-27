"""F-001 tests: AOI GeoJSON loading and geometry validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from argus.aoi.loader import AOIError, load_aoi
from argus.core.models import AOI

_TOBAGO = Path(__file__).parent.parent / "config" / "aois" / "tobago.geojson"


def test_load_tobago_returns_aoi() -> None:
    aoi = load_aoi(_TOBAGO)
    assert isinstance(aoi, AOI)


def test_load_tobago_id() -> None:
    aoi = load_aoi(_TOBAGO)
    assert aoi.id == "tobago"


def test_load_tobago_name() -> None:
    aoi = load_aoi(_TOBAGO)
    assert "tobago" in aoi.name.lower()


def test_load_tobago_domains() -> None:
    aoi = load_aoi(_TOBAGO)
    assert "marine_oil" in aoi.domains


def test_load_tobago_geometry_type() -> None:
    aoi = load_aoi(_TOBAGO)
    assert aoi.geometry["type"] in ("Polygon", "MultiPolygon")


def test_load_tobago_bbox_longitude_range() -> None:
    aoi = load_aoi(_TOBAGO)
    min_lon, _, max_lon, _ = aoi.bbox
    # Tobago is in the western Atlantic, ~60-62°W
    assert -62.0 < min_lon < -59.0
    assert -62.0 < max_lon < -59.0


def test_load_tobago_bbox_latitude_range() -> None:
    aoi = load_aoi(_TOBAGO)
    _, min_lat, _, max_lat = aoi.bbox
    # Tobago is ~10.8-11.5°N
    assert 10.0 < min_lat < 12.0
    assert 10.0 < max_lat < 12.0


def test_load_tobago_active() -> None:
    aoi = load_aoi(_TOBAGO)
    assert aoi.active is True


def test_load_tobago_created_at_parsed() -> None:
    aoi = load_aoi(_TOBAGO)
    assert aoi.created_at is not None


def test_missing_file_raises_aoi_error() -> None:
    with pytest.raises(AOIError, match="not found"):
        load_aoi(Path("config/aois/nonexistent.geojson"))


def test_oversized_polygon_rejected(tmp_path: Path) -> None:
    # A 100°×100° polygon is ~120 million km² — far above any reasonable cap
    oversized = {
        "type": "Feature",
        "properties": {"id": "huge", "domains": ["marine_oil"]},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[-50, -50], [50, -50], [50, 50], [-50, 50], [-50, -50]]],
        },
    }
    path = tmp_path / "oversized.geojson"
    path.write_text(json.dumps(oversized))
    with pytest.raises(AOIError, match="exceeds"):
        load_aoi(path)


def test_invalid_geometry_rejected(tmp_path: Path) -> None:
    # Self-intersecting (bowtie) polygon
    bowtie = {
        "type": "Feature",
        "properties": {"id": "bad", "domains": []},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[0, 0], [2, 2], [2, 0], [0, 2], [0, 0]]],
        },
    }
    path = tmp_path / "bowtie.geojson"
    path.write_text(json.dumps(bowtie))
    with pytest.raises(AOIError):
        load_aoi(path)


def test_unsupported_geojson_type_rejected(tmp_path: Path) -> None:
    fc = {
        "type": "FeatureCollection",
        "features": [],
    }
    path = tmp_path / "fc.geojson"
    path.write_text(json.dumps(fc))
    with pytest.raises(AOIError, match="Unsupported"):
        load_aoi(path)


def test_bare_polygon_geojson_loads(tmp_path: Path) -> None:
    # GeoJSON without a Feature wrapper — geometry only
    poly = {
        "type": "Polygon",
        "coordinates": [
            [[-61.2, 10.8], [-60.3, 10.8], [-60.3, 11.5], [-61.2, 11.5], [-61.2, 10.8]]
        ],
    }
    path = tmp_path / "bare.geojson"
    path.write_text(json.dumps(poly))
    aoi = load_aoi(path)
    assert aoi.geometry["type"] == "Polygon"
    # id defaults to stem
    assert aoi.id == "bare"
