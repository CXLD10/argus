"""Spectral indices for inland water quality from Sentinel-2 L2A reflectance."""

from __future__ import annotations

import numpy as np

# NDCI value above which a pixel is considered bloom-positive
BLOOM_NDCI_THRESHOLD: float = 0.25
# Fraction of water pixels that must exceed the threshold to flag bloom presence
BLOOM_PIXEL_FRACTION: float = 0.02


def compute_ndci(b5_red_edge: np.ndarray, b4_red: np.ndarray) -> np.ndarray:
    """Normalised Difference Chlorophyll Index — proxy for chlorophyll-a.

    NDCI = (B5 − B4) / (B5 + B4); NaN where the denominator is zero.
    """
    denom = b5_red_edge + b4_red
    with np.errstate(invalid="ignore", divide="ignore"):
        result = np.where(denom == 0, np.nan, (b5_red_edge - b4_red) / denom)
    return result.astype(np.float32)


def compute_ndti(b4_red: np.ndarray, b3_green: np.ndarray) -> np.ndarray:
    """Normalised Difference Turbidity Index.

    NDTI = (B4 − B3) / (B4 + B3); NaN where the denominator is zero.
    """
    denom = b4_red + b3_green
    with np.errstate(invalid="ignore", divide="ignore"):
        result = np.where(denom == 0, np.nan, (b4_red - b3_green) / denom)
    return result.astype(np.float32)


def compute_cdom(b2_blue: np.ndarray, b3_green: np.ndarray) -> np.ndarray:
    """CDOM proxy: ratio of blue to green reflectance.

    CDOM = B2 / B3; NaN where B3 is zero.
    """
    with np.errstate(invalid="ignore", divide="ignore"):
        result = np.where(b3_green == 0, np.nan, b2_blue / b3_green)
    return result.astype(np.float32)


def detect_bloom_presence(ndci: np.ndarray) -> bool:
    """Return True if ≥ BLOOM_PIXEL_FRACTION of water pixels exceed BLOOM_NDCI_THRESHOLD."""
    valid = ndci[~np.isnan(ndci)]
    if valid.size == 0:
        return False
    fraction_above = float(np.mean(valid > BLOOM_NDCI_THRESHOLD))
    return fraction_above >= BLOOM_PIXEL_FRACTION
