"""Inland water quality domain (D2) — spectral index analysis from Sentinel-2 L2A."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import numpy as np

from argus.aoi.loader import require_eligible
from argus.core.models import AOI, MonitorTarget, Observation, SourceRef
from argus.domains.base import Acquisition
from argus.domains.inland_wq.indices import (
    BLOOM_NDCI_THRESHOLD,
    BLOOM_PIXEL_FRACTION,
    compute_cdom,
    compute_ndci,
    compute_ndti,
    detect_bloom_presence,
)
from argus.ingest.catalogue import search_s2
from argus.preprocess.optical import OpticalScene


class InlandWqDomain:
    """Inland water quality domain (D2), implementing the v2.0 Domain protocol.

    Computes NDCI (chlorophyll-a proxy), NDTI (turbidity), and CDOM from
    Sentinel-2 L2A reflectance, and infers algal bloom presence when NDCI
    exceeds the bloom threshold over a sufficient pixel fraction.
    """

    domain_id: str = "inland_wq"

    def __init__(self, auth: Any = None) -> None:
        self._auth = auth  # CdseAuth | None; None = offline / test mode

    def search(
        self,
        target: MonitorTarget,
        t0: datetime,
        t1: datetime,
    ) -> list[SourceRef]:
        """Return S2 SourceRefs for the target's AOI.

        Raises BelowResolutionError before any network call if the target is below
        the minimum water body area threshold.  Returns [] in offline mode (no auth).
        """
        require_eligible(target)
        aoi = AOI(
            id=target.aoi_id,
            name=target.name,
            geometry=target.geometry,
            domains=["inland_wq"],
        )
        if self._auth is None:
            return []
        return search_s2(aoi, t0, t1, auth=self._auth)

    def acquire(self, ref: SourceRef) -> Acquisition:
        raise NotImplementedError(
            "InlandWqDomain.acquire() requires live CDSE access. "
            "Use argus.ingest.process_api.fetch_s2_subset() directly."
        )

    def analyze(self, acq: Acquisition) -> list[Observation]:
        """Compute spectral indices from an OpticalScene and return Observations.

        Expects acq.preprocessed to be an OpticalScene with at least B2/B3/B4/B5
        bands.  acq.attrs may carry 'target' (MonitorTarget) and
        'analysis_run_id' (str).
        """
        optical: OpticalScene | None = acq.preprocessed
        if optical is None:
            return []

        bands = optical.bands
        target: MonitorTarget | None = acq.attrs.get("target")
        calibration_state: str | None = target.calibration_state if target else None
        target_id: str = target.id if target else ""
        run_id: str = str(acq.attrs.get("analysis_run_id", ""))
        geometry: dict[str, Any] = (
            target.geometry if target else {"type": "Point", "coordinates": [0.0, 0.0]}
        )

        observations: list[Observation] = []
        base_attrs: dict[str, Any] = {"calibration_state": calibration_state}

        ndci: np.ndarray | None = None

        if "B4" in bands and "B5" in bands:
            ndci = compute_ndci(bands["B5"], bands["B4"])
            observations.append(
                Observation(
                    id=str(uuid.uuid4()),
                    analysis_run_id=run_id,
                    scene_id=acq.scene_id,
                    obs_type="chlorophyll_a",
                    evidence_class="measured",
                    geometry=geometry,
                    area_km2=0.0,
                    confidence=0.8,
                    value=round(float(np.nanmean(ndci)), 6),
                    unit="ndci_index",
                    domain="inland_wq",
                    target_id=target_id,
                    attrs={**base_attrs, "index": "ndci"},
                )
            )

        if "B3" in bands and "B4" in bands:
            ndti = compute_ndti(bands["B4"], bands["B3"])
            observations.append(
                Observation(
                    id=str(uuid.uuid4()),
                    analysis_run_id=run_id,
                    scene_id=acq.scene_id,
                    obs_type="turbidity",
                    evidence_class="measured",
                    geometry=geometry,
                    area_km2=0.0,
                    confidence=0.8,
                    value=round(float(np.nanmean(ndti)), 6),
                    unit="ndti_index",
                    domain="inland_wq",
                    target_id=target_id,
                    attrs={**base_attrs, "index": "ndti"},
                )
            )

        if "B2" in bands and "B3" in bands:
            cdom = compute_cdom(bands["B2"], bands["B3"])
            observations.append(
                Observation(
                    id=str(uuid.uuid4()),
                    analysis_run_id=run_id,
                    scene_id=acq.scene_id,
                    obs_type="cdom",
                    evidence_class="measured",
                    geometry=geometry,
                    area_km2=0.0,
                    confidence=0.8,
                    value=round(float(np.nanmean(cdom)), 6),
                    unit="cdom_ratio",
                    domain="inland_wq",
                    target_id=target_id,
                    attrs={**base_attrs, "index": "cdom"},
                )
            )

        if ndci is not None and detect_bloom_presence(ndci):
            observations.append(
                Observation(
                    id=str(uuid.uuid4()),
                    analysis_run_id=run_id,
                    scene_id=acq.scene_id,
                    obs_type="bloom_presence",
                    evidence_class="inferred",
                    geometry=geometry,
                    area_km2=0.0,
                    confidence=0.7,
                    value=None,
                    unit=None,
                    domain="inland_wq",
                    target_id=target_id,
                    attrs={
                        **base_attrs,
                        "bloom_threshold": BLOOM_NDCI_THRESHOLD,
                        "pixel_fraction": BLOOM_PIXEL_FRACTION,
                    },
                )
            )

        return observations
