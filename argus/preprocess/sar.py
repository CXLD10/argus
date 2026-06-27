"""SAR preprocessing: linear-power → calibrated dB, speckle filter, land mask."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import median_filter

from argus.preprocess.landmask import GeoTransform


@dataclass
class PreprocessedScene:
    """Land-masked σ⁰ dB raster pair derived from a single SAR acquisition."""

    scene_id: str
    vv_db: np.ndarray  # (rows, cols) float32 — np.nan over land
    vh_db: np.ndarray  # (rows, cols) float32 — np.nan over land
    transform: GeoTransform
    crs: str = "EPSG:4326"
    nodata: float = float("nan")


def preprocess(
    vv_linear: np.ndarray,
    vh_linear: np.ndarray,
    land_mask: np.ndarray,
    transform: GeoTransform,
    scene_id: str,
    *,
    speckle_size: int = 3,
    crs: str = "EPSG:4326",
) -> PreprocessedScene:
    """Convert linear-power SAR bands to land-masked dB.

    Steps:
    1. Convert linear power → dB via 10·log₁₀(max(x, ε)).
    2. Apply median speckle filter.
    3. Set land pixels (land_mask == True) to NaN.

    Inputs are not mutated. Output is float32.
    """
    vv_db = _speckle_filter(_to_db(vv_linear), size=speckle_size)
    vh_db = _speckle_filter(_to_db(vh_linear), size=speckle_size)

    vv_out = vv_db.copy()
    vh_out = vh_db.copy()
    vv_out[land_mask] = np.nan
    vh_out[land_mask] = np.nan

    return PreprocessedScene(
        scene_id=scene_id,
        vv_db=vv_out.astype(np.float32),
        vh_db=vh_out.astype(np.float32),
        transform=transform,
        crs=crs,
    )


def _to_db(linear: np.ndarray, epsilon: float = 1e-10) -> np.ndarray:
    return 10.0 * np.log10(np.maximum(linear.astype(np.float64), epsilon))


def _speckle_filter(arr: np.ndarray, size: int) -> np.ndarray:
    result: np.ndarray = median_filter(arr, size=size)
    return result
