"""CDSE Sentinel Hub Process API — calibrated σ⁰ raster extraction."""

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


__all__ = ["ProcessApiError", "fetch_s1_subset"]


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


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
