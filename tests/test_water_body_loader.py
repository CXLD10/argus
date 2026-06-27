"""F-024 tests: water-body MonitorTarget loader and resolution gate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from argus.aoi.loader import (
    MIN_WATER_BODY_AREA_HA,
    BelowResolutionError,
    load_water_body_target,
    require_eligible,
)
from argus.core.errors import AOIError
from argus.core.models import MonitorTarget

_REPO_ROOT = Path(__file__).parent.parent
_LAKE_GEOJSON = _REPO_ROOT / "config" / "water_bodies" / "reference_lake.geojson"
_LAKE_META = _REPO_ROOT / "config" / "water_bodies" / "reference_lake_meta.yaml"


# ── Reference lake loads correctly ───────────────────────────────────────────


def test_reference_lake_loads_as_monitor_target() -> None:
    target = load_water_body_target(_LAKE_GEOJSON, _LAKE_META)
    assert isinstance(target, MonitorTarget)


def test_reference_lake_kind_is_water_body() -> None:
    target = load_water_body_target(_LAKE_GEOJSON, _LAKE_META)
    assert target.kind == "water_body"


def test_reference_lake_resolution_status_is_eligible() -> None:
    target = load_water_body_target(_LAKE_GEOJSON, _LAKE_META)
    assert target.resolution_status == "eligible"


def test_reference_lake_area_exceeds_minimum() -> None:
    target = load_water_body_target(_LAKE_GEOJSON, _LAKE_META)
    assert target.attrs["area_ha"] >= MIN_WATER_BODY_AREA_HA


def test_reference_lake_domain_is_inland_wq() -> None:
    target = load_water_body_target(_LAKE_GEOJSON, _LAKE_META)
    assert "inland_wq" in target.domains


def test_reference_lake_calibration_state_from_meta() -> None:
    target = load_water_body_target(_LAKE_GEOJSON, _LAKE_META)
    assert target.calibration_state == "uncalibrated"


def test_reference_lake_without_meta_uses_defaults() -> None:
    target = load_water_body_target(_LAKE_GEOJSON)
    assert target.resolution_status == "eligible"
    assert target.calibration_state is None


def test_reference_lake_id_from_geojson_properties() -> None:
    target = load_water_body_target(_LAKE_GEOJSON, _LAKE_META)
    assert target.id == "reference_lake"


# ── Resolution gate: below_resolution ────────────────────────────────────────


def _make_tiny_lake_geojson(tmp_path: Path) -> Path:
    """Create a GeoJSON polygon for a ~0.001 ha lake (well below the 1 ha threshold)."""
    geojson = {
        "type": "Feature",
        "properties": {"id": "tiny_lake", "name": "Tiny Lake", "domains": ["inland_wq"]},
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [-60.5001, 10.5001],
                    [-60.5000, 10.5001],
                    [-60.5000, 10.5000],
                    [-60.5001, 10.5000],
                    [-60.5001, 10.5001],
                ]
            ],
        },
    }
    path = tmp_path / "tiny_lake.geojson"
    path.write_text(json.dumps(geojson))
    return path


def test_below_min_area_sets_resolution_status(tmp_path: Path) -> None:
    tiny = _make_tiny_lake_geojson(tmp_path)
    target = load_water_body_target(tiny)
    assert target.resolution_status == "below_resolution"


def test_below_min_area_attrs_records_area(tmp_path: Path) -> None:
    tiny = _make_tiny_lake_geojson(tmp_path)
    target = load_water_body_target(tiny)
    assert target.attrs["area_ha"] < MIN_WATER_BODY_AREA_HA


# ── require_eligible() ────────────────────────────────────────────────────────


def test_require_eligible_passes_for_eligible_target() -> None:
    target = load_water_body_target(_LAKE_GEOJSON, _LAKE_META)
    require_eligible(target)  # must not raise


def test_require_eligible_raises_for_below_resolution(tmp_path: Path) -> None:
    tiny = _make_tiny_lake_geojson(tmp_path)
    target = load_water_body_target(tiny)
    with pytest.raises(BelowResolutionError):
        require_eligible(target)


def test_below_resolution_error_is_aoi_error(tmp_path: Path) -> None:
    from argus.core.errors import AOIError

    tiny = _make_tiny_lake_geojson(tmp_path)
    target = load_water_body_target(tiny)
    with pytest.raises(AOIError):
        require_eligible(target)


def test_require_eligible_message_mentions_minimum(tmp_path: Path) -> None:
    tiny = _make_tiny_lake_geojson(tmp_path)
    target = load_water_body_target(tiny)
    with pytest.raises(BelowResolutionError, match=str(MIN_WATER_BODY_AREA_HA)):
        require_eligible(target)


# ── Error handling ────────────────────────────────────────────────────────────


def test_missing_geojson_raises_aoi_error(tmp_path: Path) -> None:
    with pytest.raises(AOIError, match="not found"):
        load_water_body_target(tmp_path / "nonexistent.geojson")


def test_invalid_geojson_type_raises_aoi_error(tmp_path: Path) -> None:
    bad = tmp_path / "bad.geojson"
    bad.write_text(json.dumps({"type": "FeatureCollection", "features": []}))
    with pytest.raises(AOIError):
        load_water_body_target(bad)


# ── aoi_id override ───────────────────────────────────────────────────────────


def test_aoi_id_override_applied(tmp_path: Path) -> None:
    target = load_water_body_target(_LAKE_GEOJSON, aoi_id="custom_aoi")
    assert target.aoi_id == "custom_aoi"


def test_aoi_id_from_meta_when_no_override() -> None:
    target = load_water_body_target(_LAKE_GEOJSON, _LAKE_META)
    assert target.aoi_id == "reference_region"
