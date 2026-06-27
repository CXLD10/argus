"""F-007 tests: Otsu-based dark-spot segmentor."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from argus.domains.marine_oil.segmentor import _otsu_threshold, segment
from argus.preprocess.landmask import GeoTransform
from argus.preprocess.sar import preprocess

_TRANSFORM = GeoTransform(
    min_lon=-61.2, min_lat=10.8, max_lon=-60.3, max_lat=11.5, cols=200, rows=200
)
_FIXTURE = Path(__file__).parent / "fixtures" / "sar_with_blob_and_noise.npy"


@pytest.fixture(scope="module")
def fixture_sar() -> tuple[np.ndarray, np.ndarray]:
    data = np.load(_FIXTURE)
    return data[0], data[1]  # vv_linear, vh_linear


@pytest.fixture(scope="module")
def fixture_vv_db(fixture_sar: tuple[np.ndarray, np.ndarray]) -> np.ndarray:
    vv, vh = fixture_sar
    land_mask = np.zeros((200, 200), dtype=bool)
    prep = preprocess(vv, vh, land_mask, _TRANSFORM, "fixture")
    return prep.vv_db


# ── Otsu threshold ─────────────────────────────────────────────────────────────


def test_otsu_uniform_returns_below_min() -> None:
    arr = np.full(100, -15.0, dtype=np.float32)
    t = _otsu_threshold(arr)
    assert t < arr.min()


def test_otsu_bimodal_between_peaks() -> None:
    low = np.full(500, -30.0)
    high = np.full(500, -15.0)
    arr = np.concatenate([low, high]).astype(np.float32)
    t = _otsu_threshold(arr)
    assert -30.0 < t < -15.0


def test_otsu_below_background_mean(fixture_vv_db: np.ndarray) -> None:
    water_px = fixture_vv_db[np.isfinite(fixture_vv_db)]
    t = _otsu_threshold(water_px)
    assert t < float(np.mean(water_px))


# ── segment() ─────────────────────────────────────────────────────────────────


def test_uniform_raster_no_dark_spots() -> None:
    vv = np.full((100, 100), -15.0, dtype=np.float32)
    mask = segment(vv)
    assert not np.any(mask)


def test_mask_is_boolean() -> None:
    vv = np.full((50, 50), -15.0, dtype=np.float32)
    mask = segment(vv)
    assert mask.dtype == bool


def test_mask_shape_preserved(fixture_vv_db: np.ndarray) -> None:
    mask = segment(fixture_vv_db)
    assert mask.shape == fixture_vv_db.shape


def test_planted_blob_detected(fixture_vv_db: np.ndarray) -> None:
    mask = segment(fixture_vv_db)
    # Blob is at rows 80-100, cols 80-100 in linear space; dB values are very low
    blob_region = mask[80:100, 80:100]
    assert np.any(blob_region), "Expected the planted blob to be detected"


def test_nan_pixels_never_in_mask() -> None:
    vv = np.full((100, 100), -15.0, dtype=np.float32)
    vv[40:60, 40:60] = -30.0
    vv[:, :30] = np.nan  # land pixels
    mask = segment(vv)
    assert not np.any(mask[:, :30]), "NaN (land) pixels must not appear in the mask"


def test_noise_patches_suppressed_by_morphology() -> None:
    """2x2 noise patches must be removed by morphological opening (iterations=2)."""
    vv = np.full((100, 100), -15.0, dtype=np.float32)
    # Plant a large dark blob (survives opening)
    vv[40:60, 40:60] = -30.0
    # Plant tiny noise patches (2x2, suppressed by erosion(2))
    vv[10:12, 10:12] = -28.0
    vv[80:82, 80:82] = -28.0

    mask = segment(vv)

    # Large blob must survive
    assert np.any(mask[40:60, 40:60])
    # Noise patches must be suppressed
    assert not np.any(mask[10:12, 10:12]), "2×2 noise at (10,10) should be eroded away"
    assert not np.any(mask[80:82, 80:82]), "2×2 noise at (80,80) should be eroded away"


def test_all_nan_returns_empty_mask() -> None:
    vv = np.full((50, 50), np.nan, dtype=np.float32)
    mask = segment(vv)
    assert not np.any(mask)
