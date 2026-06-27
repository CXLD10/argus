"""F-005 tests: naive dark-spot detector and Observation model."""

from __future__ import annotations

import numpy as np
import pytest

from argus.domains.base import Acquisition
from argus.domains.marine_oil.detector import OilDomainV0
from argus.preprocess.landmask import GeoTransform
from argus.preprocess.sar import PreprocessedScene

_TRANSFORM = GeoTransform(
    min_lon=-61.2, min_lat=10.8, max_lon=-60.3, max_lat=11.5, cols=100, rows=100
)
_RUN_ID = "run-test-001"
_SCENE_ID = "scene-test-001"


def _make_acq(vv_db: np.ndarray) -> Acquisition:
    prep = PreprocessedScene(
        scene_id=_SCENE_ID,
        vv_db=vv_db.astype(np.float32),
        vh_db=np.zeros_like(vv_db, dtype=np.float32),
        transform=_TRANSFORM,
    )
    return Acquisition(
        scene_id=_SCENE_ID,
        source_ref=None,  # type: ignore[arg-type]
        preprocessed=prep,
        attrs={"analysis_run_id": _RUN_ID},
    )


def _uniform_vv(val: float = -15.0) -> np.ndarray:
    return np.full((100, 100), val, dtype=np.float32)


def _blob_vv(
    background_db: float = -15.0,
    blob_db: float = -30.0,
    row_slice: slice = slice(40, 56),
    col_slice: slice = slice(40, 56),
) -> np.ndarray:
    arr = np.full((100, 100), background_db, dtype=np.float32)
    arr[row_slice, col_slice] = blob_db
    return arr


@pytest.fixture
def domain() -> OilDomainV0:
    return OilDomainV0()


# ── Detection ─────────────────────────────────────────────────────────────────


def test_uniform_raster_no_observations(domain: OilDomainV0) -> None:
    acq = _make_acq(_uniform_vv(-15.0))
    obs = domain.analyze(acq)
    assert obs == []


def test_planted_blob_yields_observation(domain: OilDomainV0) -> None:
    acq = _make_acq(_blob_vv())
    obs = domain.analyze(acq)
    assert len(obs) >= 1


def test_observation_obs_type(domain: OilDomainV0) -> None:
    acq = _make_acq(_blob_vv())
    obs = domain.analyze(acq)
    assert all(o.obs_type == "oil_slick" for o in obs)


def test_observation_evidence_class_measured(domain: OilDomainV0) -> None:
    """INV-3: SAR dark-spot detections must be evidence_class='measured'."""
    acq = _make_acq(_blob_vv())
    obs = domain.analyze(acq)
    assert all(o.evidence_class == "measured" for o in obs)


def test_observation_status_candidate(domain: OilDomainV0) -> None:
    acq = _make_acq(_blob_vv())
    obs = domain.analyze(acq)
    assert all(o.status == "candidate" for o in obs)


def test_observation_area_positive(domain: OilDomainV0) -> None:
    acq = _make_acq(_blob_vv())
    obs = domain.analyze(acq)
    assert all(o.area_km2 > 0 for o in obs)


def test_observation_area_in_plausible_range(domain: OilDomainV0) -> None:
    # 16×16 pixel blob at ~0.009° lon × 0.007° lat per pixel ≈ 190 km²
    acq = _make_acq(_blob_vv())
    obs = domain.analyze(acq)
    areas = [o.area_km2 for o in obs]
    assert all(0 < a < 2000 for a in areas)


def test_observation_confidence_between_0_and_1(domain: OilDomainV0) -> None:
    acq = _make_acq(_blob_vv())
    obs = domain.analyze(acq)
    assert all(0.0 <= o.confidence <= 1.0 for o in obs)


def test_observation_geometry_is_geojson(domain: OilDomainV0) -> None:
    acq = _make_acq(_blob_vv())
    obs = domain.analyze(acq)
    for o in obs:
        assert "type" in o.geometry
        assert o.geometry["type"] in ("Point", "Polygon", "MultiPolygon")


def test_observation_polygon_covers_blob_centroid(domain: OilDomainV0) -> None:
    """The detected polygon should contain the planted blob's geographic centroid."""
    from shapely.geometry import Point, shape

    acq = _make_acq(_blob_vv())
    obs = domain.analyze(acq)
    assert obs, "Expected at least one observation"

    # Centroid of the planted blob in geographic coordinates
    # Blob rows 40-55, cols 40-55; centres:
    lon_centre = _TRANSFORM.min_lon + (47.5) * _TRANSFORM.lon_res
    lat_centre = _TRANSFORM.max_lat - (47.5) * _TRANSFORM.lat_res
    blob_centre = Point(lon_centre, lat_centre)

    # At least one detected polygon must contain (or nearly contain) the blob centroid
    polygons = [shape(o.geometry) for o in obs]
    buffered = [p.buffer(0.05) for p in polygons]  # ~5km buffer for tolerance
    assert any(b.contains(blob_centre) for b in buffered)


def test_no_land_observations_returned(domain: OilDomainV0) -> None:
    """Pixels set to NaN (land-masked) must not contribute to Observations."""
    vv = _blob_vv()
    vv[:, :50] = np.nan  # mask left half as land
    acq = _make_acq(vv)
    obs = domain.analyze(acq)
    # Blob is at cols 40-55 — partially masked (40-49 are NaN); remaining pixels may or may not trigger
    # Key assertion: no observation should have its centroid on land (cols 0-49)
    for o in obs:
        coords = o.geometry.get("coordinates", [])
        if o.geometry["type"] == "Polygon":
            for ring in coords:
                for lon, _lat in ring:
                    assert lon >= _TRANSFORM.min_lon + 50 * _TRANSFORM.lon_res - 0.01


def test_no_observation_without_preprocessed(domain: OilDomainV0) -> None:
    acq = Acquisition(scene_id="s", source_ref=None, preprocessed=None)  # type: ignore[arg-type]
    assert domain.analyze(acq) == []


def test_observation_has_unique_ids(domain: OilDomainV0) -> None:
    acq = _make_acq(_blob_vv())
    obs = domain.analyze(acq)
    ids = [o.id for o in obs]
    assert len(ids) == len(set(ids))
