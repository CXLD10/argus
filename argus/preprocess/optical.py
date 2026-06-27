"""Sentinel-2/3 optical preprocessing: water masking and cloud masking stub."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from argus.preprocess.landmask import GeoTransform


@dataclass
class OpticalScene:
    """Preprocessed multi-band optical scene with land/cloud pixels masked to NaN."""

    bands: dict[str, np.ndarray]  # band_name → (H, W) float32 array (NaN = masked)
    transform: GeoTransform
    crs: str = "WGS84"
    source: str = "s2"  # "s2" | "s3"
    attrs: dict = field(default_factory=dict)


def preprocess_optical(
    band_arrays: dict[str, np.ndarray],
    land_mask: np.ndarray | None = None,
    transform: GeoTransform | None = None,
    *,
    source: str = "s2",
) -> OpticalScene:
    """Convert raw band arrays to a water-focused OpticalScene.

    Applies:
    1. Land masking: set land pixels to NaN (using provided binary land_mask).
    2. Cloud masking stub: no-op (requires SCL band — deferred to Phase 5).

    Args:
        band_arrays: dict of band_name → 2D float32 array (values in [0, 1]).
        land_mask: boolean array (True = land); same (H, W) as band arrays.
        transform: GeoTransform for spatial reference.
        source: "s2" or "s3".
    """
    default_transform = transform or GeoTransform(
        min_lon=0.0,
        min_lat=0.0,
        max_lon=1.0,
        max_lat=1.0,
        cols=100,
        rows=100,
    )

    masked: dict[str, np.ndarray] = {}
    for name, arr in band_arrays.items():
        band = arr.astype(np.float32, copy=True)
        if land_mask is not None:
            band[land_mask] = np.nan
        masked[name] = band

    return OpticalScene(
        bands=masked,
        transform=default_transform,
        source=source,
    )


def mask_clouds(scene: OpticalScene) -> OpticalScene:
    """Cloud masking stub — returns the scene unchanged.

    Full implementation requires the Sentinel-2 SCL (Scene Classification Layer)
    band, which is not requested in the current evalscript. Deferred to Phase 5.
    """
    return scene
