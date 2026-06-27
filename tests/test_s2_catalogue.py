"""F-025 tests: Sentinel-2 L2A catalogue search and optical preprocessing."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest
import responses as resp_lib

from argus.core.models import AOI, SourceRef
from argus.ingest.catalogue import CDSE_STAC_URL, search_s2
from argus.preprocess.optical import OpticalScene, mask_clouds, preprocess_optical

_FIXTURE_DIR = Path(__file__).parent / "fixtures"
_S2_FIXTURE = _FIXTURE_DIR / "cdse_s2_search_reference_lake.json"
_S2_NPY = _FIXTURE_DIR / "s2_water_body_100x100.npy"

_LAKE_AOI = AOI(
    id="reference_region",
    name="Reference Region",
    geometry={
        "type": "Polygon",
        "coordinates": [
            [[-60.6, 10.4], [-60.4, 10.4], [-60.4, 10.6], [-60.6, 10.6], [-60.6, 10.4]]
        ],
    },
    domains=["inland_wq"],
)

_T0 = datetime(2024, 2, 7, tzinfo=UTC)
_T1 = datetime(2024, 2, 9, tzinfo=UTC)


# ── search_s2() — mocked HTTP ─────────────────────────────────────────────────


@resp_lib.activate
def test_search_s2_returns_source_refs() -> None:
    fixture = json.loads(_S2_FIXTURE.read_text())
    resp_lib.add(resp_lib.POST, CDSE_STAC_URL, json=fixture, status=200)
    refs = search_s2(_LAKE_AOI, _T0, _T1)
    assert len(refs) == 2
    assert all(isinstance(r, SourceRef) for r in refs)


@resp_lib.activate
def test_search_s2_sorted_by_sensing_time() -> None:
    fixture = json.loads(_S2_FIXTURE.read_text())
    resp_lib.add(resp_lib.POST, CDSE_STAC_URL, json=fixture, status=200)
    refs = search_s2(_LAKE_AOI, _T0, _T1)
    times = [r.sensing_time for r in refs]
    assert times == sorted(times)


@resp_lib.activate
def test_search_s2_source_ref_has_s2_collection() -> None:
    fixture = json.loads(_S2_FIXTURE.read_text())
    resp_lib.add(resp_lib.POST, CDSE_STAC_URL, json=fixture, status=200)
    refs = search_s2(_LAKE_AOI, _T0, _T1)
    assert all(r.collection == "SENTINEL-2" for r in refs)


@resp_lib.activate
def test_search_s2_source_ref_has_product_type_s2msi2a() -> None:
    fixture = json.loads(_S2_FIXTURE.read_text())
    resp_lib.add(resp_lib.POST, CDSE_STAC_URL, json=fixture, status=200)
    refs = search_s2(_LAKE_AOI, _T0, _T1)
    assert all(r.product_type == "S2MSI2A" for r in refs)


@resp_lib.activate
def test_search_s2_source_ref_no_polarizations() -> None:
    fixture = json.loads(_S2_FIXTURE.read_text())
    resp_lib.add(resp_lib.POST, CDSE_STAC_URL, json=fixture, status=200)
    refs = search_s2(_LAKE_AOI, _T0, _T1)
    assert all(r.polarizations == [] for r in refs)


@resp_lib.activate
def test_search_s2_attrs_contain_cloud_cover() -> None:
    fixture = json.loads(_S2_FIXTURE.read_text())
    resp_lib.add(resp_lib.POST, CDSE_STAC_URL, json=fixture, status=200)
    refs = search_s2(_LAKE_AOI, _T0, _T1)
    assert all("eo:cloud_cover" in r.attrs for r in refs)


@resp_lib.activate
def test_search_s2_cloud_filter_excludes_high_cloud(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cloud cover filter: if max_cloud_cover=5, only the 3.5% scene should return."""
    fixture = json.loads(_S2_FIXTURE.read_text())
    resp_lib.add(resp_lib.POST, CDSE_STAC_URL, json=fixture, status=200)
    refs = search_s2(_LAKE_AOI, _T0, _T1, max_cloud_cover=5.0)
    assert len(refs) == 1
    assert refs[0].attrs["eo:cloud_cover"] == pytest.approx(3.5)


@resp_lib.activate
def test_search_s2_empty_features_returns_empty() -> None:
    resp_lib.add(
        resp_lib.POST, CDSE_STAC_URL, json={"type": "FeatureCollection", "features": []}, status=200
    )
    refs = search_s2(_LAKE_AOI, _T0, _T1)
    assert refs == []


# ── preprocess_optical() ──────────────────────────────────────────────────────


def test_preprocess_optical_returns_optical_scene() -> None:
    arr = np.load(_S2_NPY)
    band_arrays = {
        "B2": arr[0],
        "B3": arr[1],
        "B4": arr[2],
        "B5": arr[3],
        "B8A": arr[4],
        "B11": arr[5],
    }
    scene = preprocess_optical(band_arrays)
    assert isinstance(scene, OpticalScene)


def test_preprocess_optical_has_all_bands() -> None:
    arr = np.load(_S2_NPY)
    band_names = ["B2", "B3", "B4", "B5", "B8A", "B11"]
    band_arrays = {n: arr[i] for i, n in enumerate(band_names)}
    scene = preprocess_optical(band_arrays)
    assert set(scene.bands.keys()) == set(band_names)


def test_preprocess_optical_land_mask_sets_nan() -> None:
    arr = np.load(_S2_NPY)
    band_arrays = {"B4": arr[2].copy()}
    land_mask = np.zeros((100, 100), dtype=bool)
    land_mask[80:, 80:] = True  # bottom-right quadrant = land
    scene = preprocess_optical(band_arrays, land_mask=land_mask)
    assert np.all(np.isnan(scene.bands["B4"][80:, 80:]))


def test_preprocess_optical_water_pixels_not_nan() -> None:
    arr = np.load(_S2_NPY)
    band_arrays = {"B4": arr[2].copy()}
    land_mask = np.zeros((100, 100), dtype=bool)
    land_mask[80:, 80:] = True
    scene = preprocess_optical(band_arrays, land_mask=land_mask)
    assert np.all(~np.isnan(scene.bands["B4"][:80, :80]))


def test_preprocess_optical_without_land_mask_no_nans() -> None:
    arr = np.load(_S2_NPY)
    band_arrays = {"B4": arr[2].copy()}
    scene = preprocess_optical(band_arrays)
    assert not np.any(np.isnan(scene.bands["B4"]))


def test_preprocess_optical_output_is_float32() -> None:
    arr = np.load(_S2_NPY)
    band_arrays = {"B4": arr[2]}
    scene = preprocess_optical(band_arrays)
    assert scene.bands["B4"].dtype == np.float32


def test_mask_clouds_is_noop_stub() -> None:
    arr = np.load(_S2_NPY)
    band_arrays = {"B4": arr[2].copy()}
    scene = preprocess_optical(band_arrays)
    result = mask_clouds(scene)
    assert result is scene  # same object (no-op)


# ── Quota tracking — byte_count propagation ───────────────────────────────────


def test_s2_band_names_constant_has_six_entries() -> None:
    from argus.ingest.process_api import S2_BAND_NAMES

    assert len(S2_BAND_NAMES) == 6


def test_s3_band_names_constant_has_ten_entries() -> None:
    from argus.ingest.process_api import S3_BAND_NAMES

    assert len(S3_BAND_NAMES) == 10
