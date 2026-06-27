"""F-007 tests: shape and backscatter feature extraction."""

from __future__ import annotations

import numpy as np

from argus.domains.marine_oil.features import extract_features
from argus.preprocess.landmask import GeoTransform

_TRANSFORM = GeoTransform(
    min_lon=-61.2, min_lat=10.8, max_lon=-60.3, max_lat=11.5, cols=100, rows=100
)
_BACKGROUND_MEAN_DB = -15.0
_REQUIRED_FEATURE_KEYS = {
    "area_km2",
    "perimeter_km",
    "compactness",
    "elongation",
    "convexity",
    "orientation",
    "mean_sigma0_db",
    "contrast_vs_background_db",
    "texture_glcm",
}


def _make_blob_mask(
    rows: slice = slice(40, 56),
    cols: slice = slice(40, 56),
    size: int = 100,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (mask, vv_db) with a dark blob region."""
    mask = np.zeros((size, size), dtype=bool)
    mask[rows, cols] = True
    vv = np.full((size, size), _BACKGROUND_MEAN_DB, dtype=np.float32)
    vv[rows, cols] = -30.0
    return mask, vv


# ── Required keys ─────────────────────────────────────────────────────────────


def test_all_required_keys_present() -> None:
    mask, vv = _make_blob_mask()
    feats = extract_features(mask, vv, _BACKGROUND_MEAN_DB, _TRANSFORM)
    assert _REQUIRED_FEATURE_KEYS.issubset(feats.keys())


# ── Shape features ─────────────────────────────────────────────────────────────


def test_area_km2_positive() -> None:
    mask, vv = _make_blob_mask()
    feats = extract_features(mask, vv, _BACKGROUND_MEAN_DB, _TRANSFORM)
    assert feats["area_km2"] > 0.0


def test_perimeter_km_positive() -> None:
    mask, vv = _make_blob_mask()
    feats = extract_features(mask, vv, _BACKGROUND_MEAN_DB, _TRANSFORM)
    assert feats["perimeter_km"] > 0.0


def test_compactness_in_range() -> None:
    mask, vv = _make_blob_mask()
    feats = extract_features(mask, vv, _BACKGROUND_MEAN_DB, _TRANSFORM)
    assert 0.0 < feats["compactness"] <= 1.0


def test_elongation_at_least_one() -> None:
    mask, vv = _make_blob_mask()
    feats = extract_features(mask, vv, _BACKGROUND_MEAN_DB, _TRANSFORM)
    assert feats["elongation"] >= 1.0


def test_convexity_in_range() -> None:
    mask, vv = _make_blob_mask()
    feats = extract_features(mask, vv, _BACKGROUND_MEAN_DB, _TRANSFORM)
    assert 0.0 < feats["convexity"] <= 1.0


def test_square_blob_has_high_compactness() -> None:
    """A perfectly square blob is close to circular; compactness should be > 0.5."""
    mask, vv = _make_blob_mask()
    feats = extract_features(mask, vv, _BACKGROUND_MEAN_DB, _TRANSFORM)
    assert feats["compactness"] > 0.5


def test_orientation_in_range() -> None:
    mask, vv = _make_blob_mask()
    feats = extract_features(mask, vv, _BACKGROUND_MEAN_DB, _TRANSFORM)
    assert 0.0 <= feats["orientation"] < 180.0


# ── Backscatter features ───────────────────────────────────────────────────────


def test_mean_sigma0_db_equals_blob_value() -> None:
    mask, vv = _make_blob_mask()
    feats = extract_features(mask, vv, _BACKGROUND_MEAN_DB, _TRANSFORM)
    assert abs(feats["mean_sigma0_db"] - (-30.0)) < 0.1


def test_contrast_positive_for_dark_blob() -> None:
    mask, vv = _make_blob_mask()
    feats = extract_features(mask, vv, _BACKGROUND_MEAN_DB, _TRANSFORM)
    assert feats["contrast_vs_background_db"] > 0.0


def test_contrast_equals_expected() -> None:
    mask, vv = _make_blob_mask()
    feats = extract_features(mask, vv, _BACKGROUND_MEAN_DB, _TRANSFORM)
    expected = _BACKGROUND_MEAN_DB - (-30.0)  # 15 dB
    assert abs(feats["contrast_vs_background_db"] - expected) < 0.1


def test_texture_glcm_nonnegative() -> None:
    mask, vv = _make_blob_mask()
    feats = extract_features(mask, vv, _BACKGROUND_MEAN_DB, _TRANSFORM)
    assert feats["texture_glcm"] >= 0.0


# ── Integration: features in detector Observation ─────────────────────────────


def test_observation_attrs_contains_features() -> None:
    """F-007: features must be stored in Observation.attrs['features']."""
    from argus.domains.base import Acquisition
    from argus.domains.marine_oil.detector import MarineOilDomain
    from argus.preprocess.sar import PreprocessedScene

    vv = np.full((100, 100), -15.0, dtype=np.float32)
    vv[40:56, 40:56] = -30.0
    prep = PreprocessedScene(
        scene_id="feat-test",
        vv_db=vv,
        vh_db=np.full((100, 100), -20.0, dtype=np.float32),
        transform=_TRANSFORM,
    )
    acq = Acquisition(scene_id="feat-test", source_ref=None, preprocessed=prep, attrs={})  # type: ignore[arg-type]
    obs = MarineOilDomain().analyze(acq)
    assert obs, "Expected at least one observation"
    assert "features" in obs[0].attrs
    feats = obs[0].attrs["features"]
    assert _REQUIRED_FEATURE_KEYS.issubset(feats.keys())
