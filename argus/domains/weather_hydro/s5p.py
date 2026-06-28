"""Sentinel-5P SO₂/NO₂ search and acquisition stubs for D3.

Live acquisition requires CDSE credentials and network access.
These functions are placeholders for post-MVP implementation.
"""

from __future__ import annotations

from datetime import datetime

from argus.core.models import MonitorTarget, SourceRef


def search_s5p(
    target: MonitorTarget,
    t0: datetime,
    t1: datetime,
    *,
    variable: str = "SO2",
) -> list[SourceRef]:
    """Search CDSE for Sentinel-5P L2 products covering *target* in [t0, t1].

    Raises NotImplementedError until live CDSE acquisition is implemented (post-MVP).
    """
    raise NotImplementedError(
        "Sentinel-5P acquisition requires live CDSE credentials. "
        "Use Open-Meteo Air Quality endpoint for offline/MVP mode."
    )
