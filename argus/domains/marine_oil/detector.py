"""Marine oil domain: Otsu-based SAR dark-spot detector (Phase 1).

Detection pipeline: preprocess → segment → label → feature extraction →
Observation records. Implements the v2.0 Domain protocol (INV-2: stable interface).
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import numpy as np
import shapely
from scipy.ndimage import label
from shapely.geometry import MultiPoint

from argus.core.models import AnalysisRun, MonitorTarget, Observation, SourceRef
from argus.domains.base import Acquisition
from argus.domains.marine_oil.features import extract_features
from argus.domains.marine_oil.segmentor import segment
from argus.preprocess.landmask import GeoTransform
from argus.preprocess.sar import PreprocessedScene

_MIN_AREA_KM2: float = 0.05  # discard components smaller than one resolution cell
_CONFIDENCE_SCALE_DB: float = 10.0  # 10 dB contrast → confidence = 1.0


@dataclass
class _RunContext:
    analysis_run_id: str
    scene_id: str
    transform: GeoTransform
    background_mean_db: float


class MarineOilDomain:
    """SAR dark-spot detector implementing the v2.0 Domain protocol.

    Replaces OilDomainV0 internals with Otsu segmentation and full feature
    extraction while keeping the Domain interface unchanged (INV-2).
    """

    domain_id: str = "marine_oil"

    def search(self, target: MonitorTarget, t0: datetime, t1: datetime) -> list[SourceRef]:
        raise NotImplementedError(
            "MarineOilDomain.search() requires live CDSE access; "
            "use argus.ingest.catalogue directly."
        )

    def acquire(self, ref: SourceRef) -> Acquisition:
        raise NotImplementedError(
            "MarineOilDomain.acquire() requires live CDSE access; call acquire_scene() directly."
        )

    def analyze(self, acq: Acquisition) -> list[Observation]:
        """Detect dark spots in the preprocessed VV dB raster.

        Returns Observation(obs_type='oil_slick', evidence_class='measured') records.
        Returns [] when preprocessing is absent or no dark spots pass the area gate.
        """
        prep: PreprocessedScene | None = acq.preprocessed
        if prep is None:
            return []

        water_px = prep.vv_db[np.isfinite(prep.vv_db)]
        background_mean_db = float(np.mean(water_px)) if water_px.size > 0 else 0.0

        ctx = _RunContext(
            analysis_run_id=acq.attrs.get("analysis_run_id", ""),
            scene_id=acq.scene_id,
            transform=prep.transform,
            background_mean_db=background_mean_db,
        )
        return _detect(prep.vv_db, ctx)


def _detect(vv_db: np.ndarray, ctx: _RunContext) -> list[Observation]:
    dark = segment(vv_db)
    labeled, n_comp = label(dark)
    if n_comp == 0:
        return []

    observations: list[Observation] = []
    for comp_id in range(1, n_comp + 1):
        comp_mask = labeled == comp_id
        obs = _component_to_observation(comp_mask, vv_db, ctx)
        if obs is not None:
            observations.append(obs)
    return observations


def _component_to_observation(
    mask: np.ndarray,
    vv_db: np.ndarray,
    ctx: _RunContext,
) -> Observation | None:
    feats = extract_features(mask, vv_db, ctx.background_mean_db, ctx.transform)
    area_km2 = feats["area_km2"]
    if area_km2 < _MIN_AREA_KM2:
        return None

    rows, cols_idx = np.where(mask)
    tr = ctx.transform
    lons = tr.min_lon + (cols_idx + 0.5) * tr.lon_res
    lats = tr.max_lat - (rows + 0.5) * tr.lat_res

    geom = MultiPoint(list(zip(lons.tolist(), lats.tolist(), strict=True))).convex_hull
    geojson_str: str = shapely.to_geojson(geom)
    geometry: dict[str, Any] = json.loads(geojson_str)

    contrast = feats["contrast_vs_background_db"]
    confidence = min(1.0, max(0.0, float(contrast) / _CONFIDENCE_SCALE_DB))

    return Observation(
        id=str(uuid.uuid4()),
        analysis_run_id=ctx.analysis_run_id,
        scene_id=ctx.scene_id,
        obs_type="oil_slick",
        evidence_class="measured",
        geometry=geometry,
        area_km2=round(float(area_km2), 4),
        confidence=round(confidence, 4),
        status="candidate",
        features=feats,
        attrs={"features": feats},  # keep for backward compat
    )


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


# Backward-compatible alias; import MarineOilDomain directly in new code.
OilDomainV0 = MarineOilDomain
