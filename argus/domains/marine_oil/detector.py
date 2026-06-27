"""OilDomainV0: naive SAR dark-spot detector for Phase 0 spike.

Detection method: adaptive threshold (mean − k·σ) on VV dB → binary mask →
morphological clean-up → connected-component labelling → convex-hull polygons.

TD-01: intentionally naive; Phase 1 (F-007) replaces internals with the robust
segmentation pipeline while keeping the Domain interface unchanged.
"""

from __future__ import annotations

import json
import math
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import numpy as np
import shapely
from scipy.ndimage import binary_dilation, binary_erosion, label
from shapely.geometry import MultiPoint

from argus.core.models import AnalysisRun, MonitorTarget, Observation, SourceRef
from argus.domains.base import Acquisition
from argus.preprocess.landmask import GeoTransform
from argus.preprocess.sar import PreprocessedScene

# Adaptive threshold: flag pixels more than K sigma below the water mean.
_K_SIGMA: float = 2.0
_MIN_SIGMA_DB: float = 1.0  # noise floor: never use std < 1 dB
_MIN_AREA_KM2: float = 0.05  # discard sub-pixel noise blobs
_CONFIDENCE_SCALE_DB: float = 10.0  # 10 dB contrast → 100% confidence


@dataclass
class _RunContext:
    analysis_run_id: str
    scene_id: str
    transform: GeoTransform


class OilDomainV0:
    """Naive dark-spot detector implementing the v2.0 Domain protocol.

    Satisfies the Domain Protocol defined in argus.domains.base.
    """

    domain_id: str = "marine_oil"

    def search(self, target: MonitorTarget, t0: datetime, t1: datetime) -> list[SourceRef]:
        raise NotImplementedError(
            "OilDomainV0.search() requires live CDSE access; use argus.ingest.catalogue directly."
        )

    def acquire(self, ref: SourceRef) -> Acquisition:
        raise NotImplementedError(
            "OilDomainV0.acquire() requires live CDSE access; call acquire_scene() directly."
        )

    def analyze(self, acq: Acquisition) -> list[Observation]:
        """Detect dark spots in the preprocessed VV dB raster.

        Returns a list of Observation(obs_type='oil_slick', evidence_class='measured').
        Returns an empty list if no dark spots meet the minimum area threshold.
        """
        prep: PreprocessedScene | None = acq.preprocessed
        if prep is None:
            return []

        ctx = _RunContext(
            analysis_run_id=acq.attrs.get("analysis_run_id", ""),
            scene_id=acq.scene_id,
            transform=prep.transform,
        )
        return _detect(prep.vv_db, ctx)


def _detect(vv_db: np.ndarray, ctx: _RunContext) -> list[Observation]:
    water_px = vv_db[np.isfinite(vv_db)]
    if water_px.size < 10:
        return []

    mean_db = float(np.mean(water_px))
    std_db = float(np.std(water_px))
    threshold = mean_db - _K_SIGMA * max(std_db, _MIN_SIGMA_DB)

    dark = np.isfinite(vv_db) & (vv_db < threshold)
    dark = binary_erosion(dark, iterations=1)
    dark = binary_dilation(dark, iterations=1)

    labeled, n_comp = label(dark)
    if n_comp == 0:
        return []

    observations: list[Observation] = []
    for comp_id in range(1, n_comp + 1):
        mask = labeled == comp_id
        obs = _component_to_observation(mask, vv_db, threshold, ctx)
        if obs is not None:
            observations.append(obs)
    return observations


def _component_to_observation(
    mask: np.ndarray,
    vv_db: np.ndarray,
    threshold: float,
    ctx: _RunContext,
) -> Observation | None:
    rows, cols = np.where(mask)
    tr = ctx.transform
    lons = tr.min_lon + (cols + 0.5) * tr.lon_res
    lats = tr.max_lat - (rows + 0.5) * tr.lat_res

    geom = MultiPoint(list(zip(lons.tolist(), lats.tolist(), strict=True))).convex_hull
    area_km2 = _approx_area_km2(geom)
    if area_km2 < _MIN_AREA_KM2:
        return None

    comp_mean = float(np.mean(vv_db[mask]))
    contrast = abs(threshold - comp_mean)
    confidence = min(1.0, contrast / _CONFIDENCE_SCALE_DB)

    geojson_str: str = shapely.to_geojson(geom)
    geometry: dict[str, Any] = json.loads(geojson_str)

    return Observation(
        id=str(uuid.uuid4()),
        analysis_run_id=ctx.analysis_run_id,
        scene_id=ctx.scene_id,
        obs_type="oil_slick",
        evidence_class="measured",
        geometry=geometry,
        area_km2=round(area_km2, 4),
        confidence=round(confidence, 4),
        status="candidate",
    )


def _approx_area_km2(geom: Any) -> float:
    """Approximate geodesic area in km² using centroid-latitude scaling."""
    if geom.is_empty:
        return 0.0
    bounds = geom.bounds
    center_lat = (bounds[1] + bounds[3]) / 2
    km_per_deg_lon = 111.32 * math.cos(math.radians(center_lat))
    km_per_deg_lat = 111.32
    return float(geom.area * km_per_deg_lon * km_per_deg_lat)


def make_analysis_run(aoi_id: str, scene_id: str) -> AnalysisRun:
    """Create a fresh AnalysisRun for the marine_oil domain."""
    return AnalysisRun(
        id=str(uuid.uuid4()),
        aoi_id=aoi_id,
        domain_id="marine_oil",
        scene_id=scene_id,
        started_at=datetime.now(UTC),
        status="running",
    )
