"""Shape and backscatter feature extraction for SAR dark-spot candidates."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.ndimage import binary_erosion
from scipy.spatial import ConvexHull

from argus.preprocess.landmask import GeoTransform

_N_GLCM_LEVELS: int = 32


def extract_features(
    mask: np.ndarray,
    vv_db: np.ndarray,
    background_mean_db: float,
    transform: GeoTransform,
) -> dict[str, Any]:
    """Extract shape and backscatter features from a single dark-spot component mask.

    Returns a dict suitable for storage in Observation.attrs["features"].
    All features are scalar floats.
    """
    rows, cols = np.where(mask)
    n_px = int(rows.size)

    area_km2 = _area_km2(n_px, transform, rows)
    perimeter_km = _perimeter_km(mask, transform)
    compactness = _compactness(area_km2, perimeter_km)
    elongation = _elongation(rows, cols)
    convexity = _convexity(rows, cols)
    orientation = _orientation(rows, cols)

    comp_vals = vv_db[mask & np.isfinite(vv_db)]
    mean_sigma0_db = float(np.mean(comp_vals)) if comp_vals.size > 0 else float("nan")
    contrast_vs_background_db = background_mean_db - mean_sigma0_db
    texture_glcm = _texture_glcm_contrast(vv_db, mask)

    return {
        "area_km2": round(area_km2, 4),
        "perimeter_km": round(perimeter_km, 4),
        "compactness": round(compactness, 4),
        "elongation": round(elongation, 4),
        "convexity": round(convexity, 4),
        "orientation": round(orientation, 2),
        "mean_sigma0_db": round(mean_sigma0_db, 4),
        "contrast_vs_background_db": round(contrast_vs_background_db, 4),
        "texture_glcm": round(texture_glcm, 6),
    }


def _area_km2(n_px: int, transform: GeoTransform, rows: np.ndarray) -> float:
    if n_px == 0:
        return 0.0
    center_lat = float(np.mean(transform.max_lat - (rows + 0.5) * transform.lat_res))
    km_per_deg_lon = 111.32 * math.cos(math.radians(center_lat))
    km_per_deg_lat = 111.32
    pixel_area_km2 = transform.lon_res * km_per_deg_lon * transform.lat_res * km_per_deg_lat
    return float(n_px) * pixel_area_km2


def _perimeter_km(mask: np.ndarray, transform: GeoTransform) -> float:
    eroded = binary_erosion(mask, iterations=1)
    border_px = int(np.sum(mask & ~eroded))
    if border_px == 0:
        return 0.0
    avg_res_km = (transform.lon_res * 111.32 + transform.lat_res * 111.32) / 2.0
    return float(border_px) * avg_res_km


def _compactness(area_km2: float, perimeter_km: float) -> float:
    if perimeter_km < 1e-10:
        return 1.0
    return min(1.0, (4.0 * math.pi * area_km2) / (perimeter_km**2))


def _elongation(rows: np.ndarray, cols: np.ndarray) -> float:
    if rows.size < 3:
        return 1.0
    coords = np.column_stack([cols, rows]).astype(np.float64)
    centered = coords - coords.mean(axis=0)
    cov = np.cov(centered.T)
    eigenvalues = np.sort(np.abs(np.linalg.eigvalsh(cov)))[::-1]
    if eigenvalues[1] < 1e-10:
        return 1.0
    return float(np.sqrt(eigenvalues[0] / eigenvalues[1]))


def _convexity(rows: np.ndarray, cols: np.ndarray) -> float:
    if rows.size < 3:
        return 1.0
    points = np.column_stack([cols, rows]).astype(np.float64)
    try:
        hull = ConvexHull(points)
        hull_area = float(hull.volume)  # 2D: hull.volume = area
        mask_area = float(rows.size)
        return min(1.0, mask_area / hull_area) if hull_area > 0 else 1.0
    except Exception:
        return 1.0


def _orientation(rows: np.ndarray, cols: np.ndarray) -> float:
    if rows.size < 3:
        return 0.0
    coords = np.column_stack([cols, rows]).astype(np.float64)
    centered = coords - coords.mean(axis=0)
    cov = np.cov(centered.T)
    eigenvalues, eigenvectors = np.linalg.eigh(cov)
    major_vec = eigenvectors[:, int(np.argmax(eigenvalues))]
    return float(np.degrees(np.arctan2(major_vec[1], major_vec[0])) % 180.0)


def _texture_glcm_contrast(
    vv_db: np.ndarray,
    mask: np.ndarray,
    d: int = 1,
) -> float:
    """Compute GLCM contrast at vertical offset d within the masked region."""
    finite_vals = vv_db[np.isfinite(vv_db)]
    if finite_vals.size == 0:
        return 0.0
    vmin = float(np.percentile(finite_vals, 2))
    vmax = float(np.percentile(finite_vals, 98))
    if vmax <= vmin:
        return 0.0

    scale = (_N_GLCM_LEVELS - 1) / (vmax - vmin)
    q = np.clip(((vv_db - vmin) * scale).astype(np.int32), 0, _N_GLCM_LEVELS - 1)

    valid = mask[:-d, :] & mask[d:, :] & np.isfinite(vv_db[:-d, :]) & np.isfinite(vv_db[d:, :])
    if not np.any(valid):
        return 0.0

    i_vals = q[:-d, :][valid]
    j_vals = q[d:, :][valid]

    glcm = np.zeros((_N_GLCM_LEVELS, _N_GLCM_LEVELS), dtype=np.float64)
    np.add.at(glcm, (i_vals, j_vals), 1)

    total = glcm.sum()
    if total == 0:
        return 0.0
    glcm /= total

    levels = np.arange(_N_GLCM_LEVELS, dtype=np.float64)
    i_grid, j_grid = np.meshgrid(levels, levels, indexing="ij")
    return float(np.sum(glcm * (i_grid - j_grid) ** 2))
