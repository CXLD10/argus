"""F-025 tests: Sentinel-3 OLCI catalogue search."""

from __future__ import annotations

from datetime import UTC, datetime

import responses as resp_lib

from argus.core.models import AOI, SourceRef
from argus.ingest.catalogue import CDSE_STAC_URL, search_s3

_LAKE_AOI = AOI(
    id="reference_region",
    name="Reference Region",
    geometry={
        "type": "Polygon",
        "coordinates": [
            [[-60.6, 10.4], [-60.4, 10.4], [-60.4, 10.6], [-60.6, 10.6], [-60.6, 10.4]]
        ],
    },
    domains=["inland_wq"],
)

_T0 = datetime(2024, 2, 7, tzinfo=UTC)
_T1 = datetime(2024, 2, 9, tzinfo=UTC)

_S3_FIXTURE = {
    "type": "FeatureCollection",
    "features": [
        {
            "id": "S3B_OL_2_WFR____20240208T143012_20240208T143312_20240208T161823_0179_089_181_3060_PS2_O_NR_003.SEN3",
            "collection": "SENTINEL-3",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [[-62.0, 9.0], [-59.0, 9.0], [-59.0, 12.0], [-62.0, 12.0], [-62.0, 9.0]]
                ],
            },
            "properties": {
                "datetime": "2024-02-08T14:30:12Z",
                "s3:product_type": "OL_2_WFR___",
                "s3:instrument": "OLCI",
                "eo:cloud_cover": 12.0,
            },
        },
        {
            "id": "S3A_OL_2_WFR____20240207T144100_20240207T144400_20240207T162800_0179_089_181_3060_PS2_O_NR_003.SEN3",
            "collection": "SENTINEL-3",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [[-62.0, 9.0], [-59.0, 9.0], [-59.0, 12.0], [-62.0, 12.0], [-62.0, 9.0]]
                ],
            },
            "properties": {
                "datetime": "2024-02-07T14:41:00Z",
                "s3:product_type": "OL_2_WFR___",
                "s3:instrument": "OLCI",
                "eo:cloud_cover": 5.0,
            },
        },
    ],
}


@resp_lib.activate
def test_search_s3_returns_source_refs() -> None:
    resp_lib.add(resp_lib.POST, CDSE_STAC_URL, json=_S3_FIXTURE, status=200)
    refs = search_s3(_LAKE_AOI, _T0, _T1)
    assert len(refs) == 2
    assert all(isinstance(r, SourceRef) for r in refs)


@resp_lib.activate
def test_search_s3_sorted_by_sensing_time() -> None:
    resp_lib.add(resp_lib.POST, CDSE_STAC_URL, json=_S3_FIXTURE, status=200)
    refs = search_s3(_LAKE_AOI, _T0, _T1)
    times = [r.sensing_time for r in refs]
    assert times == sorted(times)


@resp_lib.activate
def test_search_s3_collection_is_sentinel3() -> None:
    resp_lib.add(resp_lib.POST, CDSE_STAC_URL, json=_S3_FIXTURE, status=200)
    refs = search_s3(_LAKE_AOI, _T0, _T1)
    assert all(r.collection == "SENTINEL-3" for r in refs)


@resp_lib.activate
def test_search_s3_product_type_is_ol_2_wfr() -> None:
    resp_lib.add(resp_lib.POST, CDSE_STAC_URL, json=_S3_FIXTURE, status=200)
    refs = search_s3(_LAKE_AOI, _T0, _T1)
    assert all(r.product_type == "OL_2_WFR___" for r in refs)


@resp_lib.activate
def test_search_s3_sensor_mode_is_olci() -> None:
    resp_lib.add(resp_lib.POST, CDSE_STAC_URL, json=_S3_FIXTURE, status=200)
    refs = search_s3(_LAKE_AOI, _T0, _T1)
    assert all(r.sensor_mode == "OLCI" for r in refs)


@resp_lib.activate
def test_search_s3_empty_returns_empty() -> None:
    resp_lib.add(
        resp_lib.POST, CDSE_STAC_URL, json={"type": "FeatureCollection", "features": []}, status=200
    )
    refs = search_s3(_LAKE_AOI, _T0, _T1)
    assert refs == []


@resp_lib.activate
def test_search_s3_attrs_include_s3_fields() -> None:
    resp_lib.add(resp_lib.POST, CDSE_STAC_URL, json=_S3_FIXTURE, status=200)
    refs = search_s3(_LAKE_AOI, _T0, _T1)
    assert all("s3:product_type" in r.attrs for r in refs)
