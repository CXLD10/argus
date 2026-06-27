"""F-002 tests: CDSE catalogue client (mocked HTTP only)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import responses

from argus.aoi.loader import load_aoi
from argus.core.models import SourceRef
from argus.ingest.catalogue import CDSE_STAC_URL, CatalogueError, search_s1_grd
from argus.ingest.cdse_auth import CDSE_TOKEN_URL, CdseAuth, CdseAuthError

_FIXTURE = Path(__file__).parent / "fixtures" / "cdse_s1_search_tobago.json"
_TOBAGO = Path(__file__).parent.parent / "config" / "aois" / "tobago.geojson"
_T0 = datetime(2024, 2, 1, tzinfo=UTC)
_T1 = datetime(2024, 2, 28, tzinfo=UTC)


# ── Catalogue search ──────────────────────────────────────────────────────────


@responses.activate
def test_search_returns_source_refs() -> None:
    fixture = json.loads(_FIXTURE.read_text())
    responses.add(responses.POST, CDSE_STAC_URL, json=fixture, status=200)

    aoi = load_aoi(_TOBAGO)
    refs = search_s1_grd(aoi, _T0, _T1)

    assert len(refs) == 2
    assert all(isinstance(r, SourceRef) for r in refs)


@responses.activate
def test_search_results_sorted_by_sensing_time() -> None:
    # Fixture has Feb-14 first, Feb-07 second — result must be ascending
    fixture = json.loads(_FIXTURE.read_text())
    responses.add(responses.POST, CDSE_STAC_URL, json=fixture, status=200)

    aoi = load_aoi(_TOBAGO)
    refs = search_s1_grd(aoi, _T0, _T1)

    times = [r.sensing_time for r in refs]
    assert times == sorted(times)
    assert refs[0].sensing_time < refs[1].sensing_time


@responses.activate
def test_search_source_ref_fields() -> None:
    fixture = json.loads(_FIXTURE.read_text())
    responses.add(responses.POST, CDSE_STAC_URL, json=fixture, status=200)

    aoi = load_aoi(_TOBAGO)
    refs = search_s1_grd(aoi, _T0, _T1)
    ref = refs[0]  # earliest (Feb 07)

    assert ref.source == "cdse"
    assert ref.product_type == "GRD"
    assert ref.sensor_mode == "IW"
    assert "VV" in ref.polarizations
    assert "VH" in ref.polarizations
    assert ref.footprint["type"] in ("Polygon", "MultiPolygon")
    assert ref.product_id.startswith("S1A_IW_GRDH")


@responses.activate
def test_search_sensing_time_is_utc() -> None:
    fixture = json.loads(_FIXTURE.read_text())
    responses.add(responses.POST, CDSE_STAC_URL, json=fixture, status=200)

    aoi = load_aoi(_TOBAGO)
    refs = search_s1_grd(aoi, _T0, _T1)

    for ref in refs:
        assert ref.sensing_time.tzinfo is not None


@responses.activate
def test_empty_result_returns_empty_list() -> None:
    empty: dict[str, object] = {"type": "FeatureCollection", "features": []}
    responses.add(responses.POST, CDSE_STAC_URL, json=empty, status=200)

    aoi = load_aoi(_TOBAGO)
    refs = search_s1_grd(aoi, _T0, _T1)

    assert refs == []


@responses.activate
def test_catalogue_http_error_raises_catalogue_error() -> None:
    responses.add(responses.POST, CDSE_STAC_URL, json={"detail": "forbidden"}, status=403)

    aoi = load_aoi(_TOBAGO)
    with pytest.raises(CatalogueError):
        search_s1_grd(aoi, _T0, _T1)


@responses.activate
def test_search_with_auth_sends_bearer_token() -> None:
    responses.add(
        responses.POST,
        CDSE_TOKEN_URL,
        json={"access_token": "tok123", "expires_in": 600},
        status=200,
    )
    responses.add(
        responses.POST,
        CDSE_STAC_URL,
        json={"type": "FeatureCollection", "features": []},
        status=200,
    )

    auth = CdseAuth("u", "p")
    aoi = load_aoi(_TOBAGO)
    search_s1_grd(aoi, _T0, _T1, auth=auth)

    stac_req = responses.calls[-1].request
    assert stac_req.headers.get("Authorization") == "Bearer tok123"


@responses.activate
def test_search_without_auth_omits_authorization_header() -> None:
    responses.add(
        responses.POST,
        CDSE_STAC_URL,
        json={"type": "FeatureCollection", "features": []},
        status=200,
    )

    aoi = load_aoi(_TOBAGO)
    search_s1_grd(aoi, _T0, _T1, auth=None)

    stac_req = responses.calls[0].request
    assert "Authorization" not in stac_req.headers


# ── Auth ──────────────────────────────────────────────────────────────────────


@responses.activate
def test_auth_failure_raises_cdse_auth_error() -> None:
    responses.add(
        responses.POST,
        CDSE_TOKEN_URL,
        json={"error": "unauthorized", "error_description": "Invalid credentials"},
        status=401,
    )

    auth = CdseAuth("baduser", "badpass")
    with pytest.raises(CdseAuthError):
        auth.get_access_token()


@responses.activate
def test_auth_error_contains_remediation_text() -> None:
    responses.add(
        responses.POST,
        CDSE_TOKEN_URL,
        json={"error": "unauthorized"},
        status=401,
    )

    auth = CdseAuth("u", "p")
    with pytest.raises(CdseAuthError) as exc_info:
        auth.get_access_token()

    msg = str(exc_info.value)
    assert "ARGUS_CDSE_USER" in msg or "dataspace.copernicus.eu" in msg


@responses.activate
def test_auth_error_no_credentials_in_message() -> None:
    responses.add(
        responses.POST,
        CDSE_TOKEN_URL,
        json={"error": "unauthorized"},
        status=401,
    )

    auth = CdseAuth("secret_user", "secret_pass")
    with pytest.raises(CdseAuthError) as exc_info:
        auth.get_access_token()

    msg = str(exc_info.value)
    assert "secret_user" not in msg
    assert "secret_pass" not in msg


@responses.activate
def test_token_cached_between_calls() -> None:
    responses.add(
        responses.POST,
        CDSE_TOKEN_URL,
        json={"access_token": "cached_token", "expires_in": 600},
        status=200,
    )

    auth = CdseAuth("u", "p")
    t1 = auth.get_access_token()
    t2 = auth.get_access_token()  # should hit cache, no second HTTP call

    assert t1 == t2 == "cached_token"
    assert len(responses.calls) == 1
