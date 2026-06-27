"""CDSE Sentinel Hub Process API — S1 σ⁰, S2 surface reflectance, and S3 OLCI."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import requests

from argus.core.errors import ProcessApiError  # noqa: E402 — re-export for backward compat
from argus.core.models import AOI, SourceRef
from argus.ingest.cdse_auth import CdseAuth

CDSE_PROCESS_API_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"

# ~20 m at tropical latitudes (0.0002° ≈ 22 m)
DEFAULT_RESOLUTION_DEG: float = 0.0002

# Two-band (VV, VH) FLOAT32 evalscript; returns a single multi-band GeoTIFF.
_S1_EVALSCRIPT = (
    "//VERSION=3\n"
    "function setup() {\n"
    "  return {\n"
    "    input: [{bands: ['VV', 'VH'], units: 'LINEARPOWER'}],\n"
    "    output: {bands: 2, sampleType: 'FLOAT32'}\n"
    "  };\n"
    "}\n"
    "function evaluatePixel(s) { return [s.VV, s.VH]; }"
)


__all__ = ["ProcessApiError", "fetch_s1_subset", "fetch_s2_subset", "fetch_s3_olci_subset"]


def fetch_s1_subset(
    ref: SourceRef,
    aoi: AOI,
    auth: CdseAuth,
    *,
    resolution_deg: float = DEFAULT_RESOLUTION_DEG,
) -> tuple[bytes, int]:
    """Request a 2-band (VV, VH) σ⁰ GeoTIFF for the AOI from the CDSE Process API.

    Returns ``(tiff_bytes, byte_count)`` where *byte_count* is taken from the
    ``Content-Length`` response header (or the actual body length as fallback).
    """
    bbox = list(aoi.bbox)
    t0 = ref.sensing_time
    t1 = t0 + timedelta(seconds=90)

    payload: dict[str, Any] = {
        "input": {
            "bounds": {
                "bbox": bbox,
                "properties": {"crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84"},
            },
            "data": [
                {
                    "type": "S1GRD",
                    "dataFilter": {
                        "timeRange": {"from": _iso(t0), "to": _iso(t1)},
                        "mosaickingOrder": "mostRecent",
                        "resolution": "HIGH",
                        "polarization": "DV",
                    },
                    "processing": {
                        "orthorectify": True,
                        "backCoeff": "SIGMA0_ELLIPSOID",
                    },
                }
            ],
        },
        "output": {
            "resx": resolution_deg,
            "resy": resolution_deg,
            "responses": [{"identifier": "default", "format": {"type": "image/tiff"}}],
        },
        "evalscript": _S1_EVALSCRIPT,
    }

    token = auth.get_access_token()
    try:
        resp = requests.post(
            CDSE_PROCESS_API_URL,
            json=payload,
            headers={"Authorization": f"Bearer {token}", "Accept": "image/tiff"},
            timeout=120,
        )
        resp.raise_for_status()
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        raise ProcessApiError(
            f"Process API returned HTTP {status}. "
            "Check evalscript, bbox extent, and processing-unit quota."
        ) from exc
    except requests.RequestException as exc:
        raise ProcessApiError(f"Process API request failed: {type(exc).__name__}.") from exc

    content = resp.content
    byte_count = int(resp.headers.get("Content-Length", len(content)))
    return content, byte_count


# S2 L2A: 6 bands covering water-quality-relevant spectral range.
# B2=Blue, B3=Green, B4=Red, B5=RedEdge, B8A=NIR, B11=SWIR (20m resampled to 10m).
_S2_EVALSCRIPT = (
    "//VERSION=3\n"
    "function setup() {\n"
    "  return {\n"
    "    input: [{bands: ['B02','B03','B04','B05','B8A','B11'], units: 'REFLECTANCE'}],\n"
    "    output: {bands: 6, sampleType: 'FLOAT32'}\n"
    "  };\n"
    "}\n"
    "function evaluatePixel(s) { return [s.B02, s.B03, s.B04, s.B05, s.B8A, s.B11]; }"
)

# S3 OLCI: bands Oa03–Oa12 (visible + NIR; adequate for NDCI / chl-a fluorescence).
_S3_EVALSCRIPT = (
    "//VERSION=3\n"
    "function setup() {\n"
    "  return {\n"
    "    input: [{bands: ['B03','B04','B05','B06','B07','B08','B09','B10','B11','B12']}],\n"
    "    output: {bands: 10, sampleType: 'FLOAT32'}\n"
    "  };\n"
    "}\n"
    "function evaluatePixel(s) {\n"
    "  return [s.B03,s.B04,s.B05,s.B06,s.B07,s.B08,s.B09,s.B10,s.B11,s.B12];\n"
    "}"
)

# S2 band names in order (matches _S2_EVALSCRIPT output order)
S2_BAND_NAMES: list[str] = ["B2", "B3", "B4", "B5", "B8A", "B11"]

# S3 OLCI band names in order
S3_BAND_NAMES: list[str] = [
    "Oa03",
    "Oa04",
    "Oa05",
    "Oa06",
    "Oa07",
    "Oa08",
    "Oa09",
    "Oa10",
    "Oa11",
    "Oa12",
]


def fetch_s2_subset(
    ref: SourceRef,
    aoi: AOI,
    auth: CdseAuth,
    *,
    resolution_deg: float = 0.0001,  # ~10 m at tropical latitudes
) -> tuple[bytes, int]:
    """Request a 6-band (B2/B3/B4/B5/B8A/B11) L2A reflectance GeoTIFF from the Process API.

    Returns ``(tiff_bytes, byte_count)``.
    """
    bbox = list(aoi.bbox)
    t0 = ref.sensing_time
    t1 = t0 + timedelta(seconds=600)

    payload: dict[str, Any] = {
        "input": {
            "bounds": {
                "bbox": bbox,
                "properties": {"crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84"},
            },
            "data": [
                {
                    "type": "S2L2A",
                    "dataFilter": {
                        "timeRange": {"from": _iso(t0), "to": _iso(t1)},
                        "mosaickingOrder": "leastCC",
                        "maxCloudCoverage": 30,
                    },
                }
            ],
        },
        "output": {
            "resx": resolution_deg,
            "resy": resolution_deg,
            "responses": [{"identifier": "default", "format": {"type": "image/tiff"}}],
        },
        "evalscript": _S2_EVALSCRIPT,
    }

    token = auth.get_access_token()
    try:
        resp = requests.post(
            CDSE_PROCESS_API_URL,
            json=payload,
            headers={"Authorization": f"Bearer {token}", "Accept": "image/tiff"},
            timeout=120,
        )
        resp.raise_for_status()
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        raise ProcessApiError(
            f"S2 Process API returned HTTP {status}. "
            "Check evalscript, bbox, and cloud cover filter."
        ) from exc
    except requests.RequestException as exc:
        raise ProcessApiError(f"S2 Process API request failed: {type(exc).__name__}.") from exc

    content = resp.content
    byte_count = int(resp.headers.get("Content-Length", len(content)))
    return content, byte_count


def fetch_s3_olci_subset(
    ref: SourceRef,
    aoi: AOI,
    auth: CdseAuth,
    *,
    resolution_deg: float = 0.003,  # ~300 m at tropical latitudes
) -> tuple[bytes, int]:
    """Request a 10-band OLCI (Oa03–Oa12) GeoTIFF from the Process API.

    Returns ``(tiff_bytes, byte_count)``.
    """
    bbox = list(aoi.bbox)
    t0 = ref.sensing_time
    t1 = t0 + timedelta(seconds=600)

    payload: dict[str, Any] = {
        "input": {
            "bounds": {
                "bbox": bbox,
                "properties": {"crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84"},
            },
            "data": [
                {
                    "type": "S3OLCI",
                    "dataFilter": {
                        "timeRange": {"from": _iso(t0), "to": _iso(t1)},
                        "mosaickingOrder": "mostRecent",
                    },
                }
            ],
        },
        "output": {
            "resx": resolution_deg,
            "resy": resolution_deg,
            "responses": [{"identifier": "default", "format": {"type": "image/tiff"}}],
        },
        "evalscript": _S3_EVALSCRIPT,
    }

    token = auth.get_access_token()
    try:
        resp = requests.post(
            CDSE_PROCESS_API_URL,
            json=payload,
            headers={"Authorization": f"Bearer {token}", "Accept": "image/tiff"},
            timeout=120,
        )
        resp.raise_for_status()
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        raise ProcessApiError(f"S3 Process API returned HTTP {status}.") from exc
    except requests.RequestException as exc:
        raise ProcessApiError(f"S3 Process API request failed: {type(exc).__name__}.") from exc

    content = resp.content
    byte_count = int(resp.headers.get("Content-Length", len(content)))
    return content, byte_count


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
