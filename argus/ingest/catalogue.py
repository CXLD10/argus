"""CDSE STAC catalogue search for Sentinel-1 GRD, Sentinel-2 L2A, and Sentinel-3 OLCI."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import requests

from argus.core.errors import CatalogueError  # noqa: E402 — re-export for backward compat
from argus.core.models import AOI, SourceRef
from argus.ingest.cdse_auth import CdseAuth

CDSE_STAC_URL = "https://catalogue.dataspace.copernicus.eu/stac/search"

__all__ = ["CatalogueError", "search_s1_grd", "search_s2", "search_s3"]


def search_s1_grd(
    aoi: AOI,
    t0: datetime,
    t1: datetime,
    auth: CdseAuth | None = None,
    *,
    max_results: int = 50,
) -> list[SourceRef]:
    """Search CDSE STAC for Sentinel-1 IW GRD scenes intersecting the AOI.

    Returns an empty list when no products match — never raises for an empty result.
    Results are sorted by sensing_time ascending.
    """
    bbox = list(aoi.bbox)
    payload: dict[str, Any] = {
        "collections": ["SENTINEL-1"],
        "datetime": f"{_iso(t0)}/{_iso(t1)}",
        "bbox": bbox,
        "query": {
            "productType": {"eq": "GRD"},
            "sensorOperationalMode": {"eq": "IW"},
        },
        "limit": max_results,
    }

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if auth is not None:
        headers["Authorization"] = f"Bearer {auth.get_access_token()}"

    try:
        resp = requests.post(CDSE_STAC_URL, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        raise CatalogueError(f"CDSE catalogue search returned HTTP {status}.") from exc
    except requests.RequestException as exc:
        raise CatalogueError(f"CDSE catalogue search failed: {type(exc).__name__}.") from exc

    features: list[dict[str, Any]] = resp.json().get("features", [])
    refs = [_to_source_ref(f) for f in features if _is_usable(f)]
    refs.sort(key=lambda r: r.sensing_time)
    return refs


def search_s2(
    aoi: AOI,
    t0: datetime,
    t1: datetime,
    auth: CdseAuth | None = None,
    *,
    max_cloud_cover: float = 30.0,
    max_results: int = 50,
) -> list[SourceRef]:
    """Search CDSE STAC for Sentinel-2 MSI L2A scenes intersecting the AOI.

    Filters by cloud cover ≤ max_cloud_cover. Results sorted by sensing_time ascending.
    """
    bbox = list(aoi.bbox)
    payload: dict[str, Any] = {
        "collections": ["SENTINEL-2"],
        "datetime": f"{_iso(t0)}/{_iso(t1)}",
        "bbox": bbox,
        "query": {
            "productType": {"eq": "S2MSI2A"},
        },
        "limit": max_results,
    }

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if auth is not None:
        headers["Authorization"] = f"Bearer {auth.get_access_token()}"

    try:
        resp = requests.post(CDSE_STAC_URL, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        raise CatalogueError(f"CDSE S2 catalogue search returned HTTP {status}.") from exc
    except requests.RequestException as exc:
        raise CatalogueError(f"CDSE S2 catalogue search failed: {type(exc).__name__}.") from exc

    features: list[dict[str, Any]] = resp.json().get("features", [])
    refs = [
        _to_s2_source_ref(f)
        for f in features
        if _is_usable(f) and _cloud_cover(f) <= max_cloud_cover
    ]
    refs.sort(key=lambda r: r.sensing_time)
    return refs


def search_s3(
    aoi: AOI,
    t0: datetime,
    t1: datetime,
    auth: CdseAuth | None = None,
    *,
    max_results: int = 50,
) -> list[SourceRef]:
    """Search CDSE STAC for Sentinel-3 OLCI Level-2 water products.

    Returns SourceRef list sorted by sensing_time ascending.
    """
    bbox = list(aoi.bbox)
    payload: dict[str, Any] = {
        "collections": ["SENTINEL-3"],
        "datetime": f"{_iso(t0)}/{_iso(t1)}",
        "bbox": bbox,
        "query": {
            "productType": {"eq": "OL_2_WFR___"},
        },
        "limit": max_results,
    }

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if auth is not None:
        headers["Authorization"] = f"Bearer {auth.get_access_token()}"

    try:
        resp = requests.post(CDSE_STAC_URL, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        raise CatalogueError(f"CDSE S3 catalogue search returned HTTP {status}.") from exc
    except requests.RequestException as exc:
        raise CatalogueError(f"CDSE S3 catalogue search failed: {type(exc).__name__}.") from exc

    features: list[dict[str, Any]] = resp.json().get("features", [])
    refs = [_to_s3_source_ref(f) for f in features if _is_usable(f)]
    refs.sort(key=lambda r: r.sensing_time)
    return refs


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_usable(feature: dict[str, Any]) -> bool:
    props = feature.get("properties") or {}
    return bool(feature.get("id") and props.get("datetime") and feature.get("geometry"))


def _cloud_cover(feature: dict[str, Any]) -> float:
    props = feature.get("properties") or {}
    return float(props.get("eo:cloud_cover", 0.0))


def _to_s2_source_ref(feature: dict[str, Any]) -> SourceRef:
    props: dict[str, Any] = feature.get("properties") or {}
    raw_dt: str = props["datetime"]
    sensing_time = datetime.fromisoformat(raw_dt.replace("Z", "+00:00"))
    s2_attrs = {k: v for k, v in props.items() if k.startswith("s2:") or k.startswith("eo:")}
    return SourceRef(
        product_id=str(feature["id"]),
        source="cdse",
        collection=str(feature.get("collection", "SENTINEL-2")),
        product_type=str(props.get("s2:product_type", "S2MSI2A")),
        sensor_mode=str(props.get("s2:instrument", "MSI")),
        sensing_time=sensing_time,
        footprint=dict(feature["geometry"]),
        polarizations=[],  # optical: no polarizations
        attrs=s2_attrs,
    )


def _to_s3_source_ref(feature: dict[str, Any]) -> SourceRef:
    props: dict[str, Any] = feature.get("properties") or {}
    raw_dt: str = props["datetime"]
    sensing_time = datetime.fromisoformat(raw_dt.replace("Z", "+00:00"))
    s3_attrs = {k: v for k, v in props.items() if k.startswith("s3:") or k.startswith("eo:")}
    return SourceRef(
        product_id=str(feature["id"]),
        source="cdse",
        collection=str(feature.get("collection", "SENTINEL-3")),
        product_type=str(props.get("s3:product_type", "OL_2_WFR___")),
        sensor_mode=str(props.get("s3:instrument", "OLCI")),
        sensing_time=sensing_time,
        footprint=dict(feature["geometry"]),
        polarizations=[],
        attrs=s3_attrs,
    )


def _to_source_ref(feature: dict[str, Any]) -> SourceRef:
    props: dict[str, Any] = feature.get("properties") or {}
    raw_dt: str = props["datetime"]
    sensing_time = datetime.fromisoformat(raw_dt.replace("Z", "+00:00"))
    polarizations: list[str] = props.get("s1:polarizations") or []
    s1_attrs = {k: v for k, v in props.items() if k.startswith("s1:")}
    return SourceRef(
        product_id=str(feature["id"]),
        source="cdse",
        collection=str(feature.get("collection", "SENTINEL-1")),
        product_type=str(props.get("s1:product_type", "GRD")),
        sensor_mode=str(props.get("s1:instrument_mode", "IW")),
        sensing_time=sensing_time,
        footprint=dict(feature["geometry"]),
        polarizations=polarizations,
        attrs=s1_attrs,
    )
