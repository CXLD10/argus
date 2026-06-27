"""F-026 tests: spectral index computation (indices.py)."""

from __future__ import annotations

import numpy as np
import pytest

from argus.domains.inland_wq.indices import (
    BLOOM_NDCI_THRESHOLD,
    BLOOM_PIXEL_FRACTION,
    compute_cdom,
    compute_ndci,
    compute_ndti,
    detect_bloom_presence,
)

# ── NDCI ─────────────────────────────────────────────────────────────────────


def test_compute_ndci_formula() -> None:
    b5 = np.array([[0.13]], dtype=np.float32)
    b4 = np.array([[0.04]], dtype=np.float32)
    result = compute_ndci(b5, b4)
    expected = (0.13 - 0.04) / (0.13 + 0.04)
    assert result[0, 0] == pytest.approx(expected, rel=1e-4)


def test_compute_ndci_output_dtype_is_float32() -> None:
    b5 = np.ones((5, 5), dtype=np.float32) * 0.13
    b4 = np.ones((5, 5), dtype=np.float32) * 0.04
    assert compute_ndci(b5, b4).dtype == np.float32


def test_compute_ndci_zero_denominator_returns_nan() -> None:
    b5 = np.zeros((3, 3), dtype=np.float32)
    b4 = np.zeros((3, 3), dtype=np.float32)
    result = compute_ndci(b5, b4)
    assert np.all(np.isnan(result))


def test_compute_ndci_negative_values_valid() -> None:
    b5 = np.array([[0.02]], dtype=np.float32)
    b4 = np.array([[0.08]], dtype=np.float32)
    result = compute_ndci(b5, b4)
    expected = (0.02 - 0.08) / (0.02 + 0.08)
    assert result[0, 0] == pytest.approx(expected, rel=1e-4)


# ── NDTI ─────────────────────────────────────────────────────────────────────


def test_compute_ndti_formula() -> None:
    b4 = np.array([[0.08]], dtype=np.float32)
    b3 = np.array([[0.05]], dtype=np.float32)
    result = compute_ndti(b4, b3)
    expected = (0.08 - 0.05) / (0.08 + 0.05)
    assert result[0, 0] == pytest.approx(expected, rel=1e-4)


def test_compute_ndti_output_dtype_is_float32() -> None:
    b4 = np.ones((5, 5), dtype=np.float32) * 0.08
    b3 = np.ones((5, 5), dtype=np.float32) * 0.05
    assert compute_ndti(b4, b3).dtype == np.float32


def test_compute_ndti_zero_denominator_returns_nan() -> None:
    b4 = np.zeros((3, 3), dtype=np.float32)
    b3 = np.zeros((3, 3), dtype=np.float32)
    result = compute_ndti(b4, b3)
    assert np.all(np.isnan(result))


# ── CDOM ─────────────────────────────────────────────────────────────────────


def test_compute_cdom_formula() -> None:
    b2 = np.array([[0.05]], dtype=np.float32)
    b3 = np.array([[0.06]], dtype=np.float32)
    result = compute_cdom(b2, b3)
    expected = 0.05 / 0.06
    assert result[0, 0] == pytest.approx(expected, rel=1e-4)


def test_compute_cdom_output_dtype_is_float32() -> None:
    b2 = np.ones((5, 5), dtype=np.float32) * 0.05
    b3 = np.ones((5, 5), dtype=np.float32) * 0.06
    assert compute_cdom(b2, b3).dtype == np.float32


def test_compute_cdom_zero_b3_returns_nan() -> None:
    b2 = np.ones((3, 3), dtype=np.float32)
    b3 = np.zeros((3, 3), dtype=np.float32)
    result = compute_cdom(b2, b3)
    assert np.all(np.isnan(result))


# ── Bloom detection ───────────────────────────────────────────────────────────


def test_detect_bloom_presence_algae_patch_triggers_bloom() -> None:
    """A 4% algae patch with NDCI > threshold should exceed BLOOM_PIXEL_FRACTION."""
    ndci = np.full((100, 100), 0.08, dtype=np.float32)  # background: low NDCI
    ndci[20:40, 20:40] = 0.53  # elevated algae patch (4% of pixels)
    assert detect_bloom_presence(ndci) is True


def test_detect_bloom_presence_no_elevated_pixels_returns_false() -> None:
    ndci = np.full((100, 100), 0.08, dtype=np.float32)
    assert detect_bloom_presence(ndci) is False


def test_detect_bloom_presence_all_nan_returns_false() -> None:
    ndci = np.full((10, 10), np.nan, dtype=np.float32)
    assert detect_bloom_presence(ndci) is False


def test_detect_bloom_presence_uses_constants() -> None:
    assert 0.0 < BLOOM_NDCI_THRESHOLD < 1.0
    assert 0.0 < BLOOM_PIXEL_FRACTION < 1.0


def test_detect_bloom_presence_exactly_at_fraction_boundary() -> None:
    """Exactly BLOOM_PIXEL_FRACTION of pixels above threshold should trigger bloom."""
    n = 10000
    ndci = np.full(n, 0.08, dtype=np.float32)
    n_above = int(np.ceil(BLOOM_PIXEL_FRACTION * n))
    ndci[:n_above] = BLOOM_NDCI_THRESHOLD + 0.1
    ndci_2d = ndci.reshape(100, 100)
    assert detect_bloom_presence(ndci_2d) is True
