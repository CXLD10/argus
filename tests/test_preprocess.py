"""F-004 tests: SAR preprocessing pipeline."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pytest

from argus.preprocess.landmask import GeoTransform
from argus.preprocess.sar import PreprocessedScene, preprocess

_FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_sar_100x100.npy"

# Tobago AOI extent — matches config/aois/tobago.geojson
_TRANSFORM = GeoTransform(
    min_lon=-61.2, min_lat=10.8, max_lon=-60.3, max_lat=11.5, cols=100, rows=100
)


@pytest.fixture(scope="module")
def sar_bands() -> tuple[np.ndarray, np.ndarray]:
    data = np.load(_FIXTURE)
    return data[0], data[1]  # vv, vh


@pytest.fixture(scope="module")
def land_mask_left_half() -> np.ndarray:
    """Boolean mask: True for left 50 columns (synthetic land area)."""
    mask = np.zeros((100, 100), dtype=bool)
    mask[:, :50] = True
    return mask


@pytest.fixture(scope="module")
def processed(
    sar_bands: tuple[np.ndarray, np.ndarray],
    land_mask_left_half: np.ndarray,
) -> PreprocessedScene:
    vv, vh = sar_bands
    return preprocess(vv, vh, land_mask_left_half, _TRANSFORM, scene_id="test-scene")


def test_preprocess_returns_preprocessed_scene(processed: PreprocessedScene) -> None:
    assert isinstance(processed, PreprocessedScene)


def test_vv_db_is_float32(processed: PreprocessedScene) -> None:
    assert processed.vv_db.dtype == np.float32


def test_vh_db_is_float32(processed: PreprocessedScene) -> None:
    assert processed.vh_db.dtype == np.float32


def test_vv_db_shape_preserved(processed: PreprocessedScene) -> None:
    assert processed.vv_db.shape == (100, 100)


def test_vh_db_shape_preserved(processed: PreprocessedScene) -> None:
    assert processed.vh_db.shape == (100, 100)


def test_water_pixels_have_finite_vv(processed: PreprocessedScene) -> None:
    # Right 50 columns are water — must all be finite
    water = processed.vv_db[:, 50:]
    assert np.all(np.isfinite(water))


def test_water_pixels_have_finite_vh(processed: PreprocessedScene) -> None:
    water = processed.vh_db[:, 50:]
    assert np.all(np.isfinite(water))


def test_land_pixels_are_nan_vv(processed: PreprocessedScene) -> None:
    # Left 50 columns are land — must all be NaN (after speckle filter edge)
    # Use interior columns (avoid speckle filter border artefacts at column 49)
    land = processed.vv_db[:, 1:49]
    assert np.all(np.isnan(land))


def test_land_pixels_are_nan_vh(processed: PreprocessedScene) -> None:
    land = processed.vh_db[:, 1:49]
    assert np.all(np.isnan(land))


def test_water_vv_db_in_expected_range(processed: PreprocessedScene) -> None:
    # Synthetic VV: linear 0.0001–0.01 → dB range: -40 to -20 dB (approximately)
    water = processed.vv_db[:, 51:]  # avoid speckle border at col 50
    assert float(np.nanmin(water)) >= -50.0
    assert float(np.nanmax(water)) <= 0.0


def test_scene_id_preserved(processed: PreprocessedScene) -> None:
    assert processed.scene_id == "test-scene"


def test_transform_preserved(processed: PreprocessedScene) -> None:
    assert processed.transform is _TRANSFORM


def test_crs_default(processed: PreprocessedScene) -> None:
    assert processed.crs == "EPSG:4326"


def test_preprocessing_is_deterministic(
    sar_bands: tuple[np.ndarray, np.ndarray],
    land_mask_left_half: np.ndarray,
) -> None:
    """Same input must produce byte-for-byte identical output (INV-8)."""
    vv, vh = sar_bands

    def _hash(scene: PreprocessedScene) -> str:
        return hashlib.sha256(scene.vv_db.tobytes() + scene.vh_db.tobytes()).hexdigest()

    r1 = preprocess(vv, vh, land_mask_left_half, _TRANSFORM, scene_id="s")
    r2 = preprocess(vv, vh, land_mask_left_half, _TRANSFORM, scene_id="s")
    assert _hash(r1) == _hash(r2)


def test_input_arrays_not_mutated(
    sar_bands: tuple[np.ndarray, np.ndarray],
    land_mask_left_half: np.ndarray,
) -> None:
    vv, vh = sar_bands
    vv_copy = vv.copy()
    vh_copy = vh.copy()
    preprocess(vv, vh, land_mask_left_half, _TRANSFORM, scene_id="s")
    assert np.array_equal(vv, vv_copy)
    assert np.array_equal(vh, vh_copy)
