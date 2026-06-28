"""Sentinel-1 inundation confirmation for D3.

Post-event SAR-based inundation mapping requires live CDSE access.
This module is a stub — the analysis logic mirrors D1 dark-spot detection
but is constrained to a prior-flooded mask from GloFAS discharge thresholds.
"""

from __future__ import annotations

from argus.core.models import Observation
from argus.domains.base import Acquisition


def analyze_inundation(acq: Acquisition) -> list[Observation]:
    """Detect inundated areas from a post-event Sentinel-1 acquisition.

    Raises NotImplementedError until live S1 SAR analysis is implemented.
    In the MVP, inundation confirmation is deferred to post-CP3 work.
    """
    raise NotImplementedError(
        "S1 inundation analysis requires live CDSE SAR acquisition. "
        "Inundation confirmation is deferred to post-MVP implementation."
    )
