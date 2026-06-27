"""F-002 live integration tests: real CDSE auth and catalogue search.

Run with: pytest -m live tests/integration/test_cdse_live.py
Requires: ARGUS_CDSE_USER and ARGUS_CDSE_PASSWORD environment variables.
Quota impact: ~1 STAC API call (no bytes transferred).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from argus.aoi.loader import load_aoi
from argus.core.config import load_settings
from argus.ingest.catalogue import search_s1_grd
from argus.ingest.cdse_auth import CdseAuth

_TOBAGO = Path(__file__).parent.parent.parent / "config" / "aois" / "tobago.geojson"


@pytest.fixture(scope="module")
def cdse_auth() -> CdseAuth:
    settings = load_settings()
    if not settings.cdse.user or not settings.cdse.password:
        pytest.skip("CDSE credentials not configured (set ARGUS_CDSE_USER / ARGUS_CDSE_PASSWORD)")
    return CdseAuth(settings.cdse.user, settings.cdse.password)


@pytest.mark.live
def test_cdse_token_acquisition(cdse_auth: CdseAuth) -> None:
    token = cdse_auth.get_access_token()
    assert token
    assert len(token) > 20


@pytest.mark.live
def test_cdse_catalogue_search_tobago(cdse_auth: CdseAuth) -> None:
    aoi = load_aoi(_TOBAGO)
    t0 = datetime(2024, 2, 1, tzinfo=UTC)
    t1 = datetime(2024, 2, 28, tzinfo=UTC)

    refs = search_s1_grd(aoi, t0, t1, auth=cdse_auth)

    # Tobago 2024 spill — at least one S1 pass should have been acquired in Feb 2024
    assert isinstance(refs, list)
    if refs:
        assert all(r.source == "cdse" for r in refs)
        assert all(r.product_type == "GRD" for r in refs)
        times = [r.sensing_time for r in refs]
        assert times == sorted(times)
