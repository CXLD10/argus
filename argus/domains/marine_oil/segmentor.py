"""SAR dark-spot segmentation via Otsu thresholding and morphological opening."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import binary_dilation, binary_erosion

_MORPH_ITERATIONS: int = 2  # opening strength: removes noise patches ≤ 4px diameter


def segment(vv_db: np.ndarray, *, morph_iterations: int = _MORPH_ITERATIONS) -> np.ndarray:
    """Return a boolean dark-spot mask from a land-masked VV dB raster.

    Steps:
    1. Compute Otsu threshold on finite (water) pixels.
    2. Flag pixels below threshold as dark.
    3. Morphological opening (erosion then dilation) removes isolated noise.

    Returns a bool (rows, cols) array. NaN (land) pixels are always False.
    """
    water_px = vv_db[np.isfinite(vv_db)]
    if water_px.size < 10:
        return np.zeros(vv_db.shape, dtype=bool)

    threshold = _otsu_threshold(water_px)
    dark: np.ndarray = np.isfinite(vv_db) & (vv_db < threshold)
    dark = binary_erosion(dark, iterations=morph_iterations)
    dark = binary_dilation(dark, iterations=morph_iterations)
    return dark


def _otsu_threshold(arr: np.ndarray, bins: int = 256) -> float:
    """Compute Otsu's optimal binary threshold.

    Returns a value below all data if the array is effectively uniform
    (peak-to-peak < 1e-10), so no pixels are flagged.
    """
    if float(np.ptp(arr)) < 1e-10:
        return float(arr.min()) - 1.0

    hist, edges = np.histogram(arr, bins=bins)
    centers = (edges[:-1] + edges[1:]) / 2.0

    p = hist.astype(np.float64) / hist.sum()
    w0 = np.cumsum(p)
    mu_total = float(np.dot(p, centers))
    mu0_cumsum = np.cumsum(p * centers)
    mu0 = mu0_cumsum / np.where(w0 > 0.0, w0, 1e-15)
    w1 = 1.0 - w0
    mu1 = (mu_total - mu0_cumsum) / np.where(w1 > 0.0, w1, 1e-15)

    var_between = w0 * w1 * (mu0 - mu1) ** 2
    return float(centers[int(np.argmax(var_between))])
