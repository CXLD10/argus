"""Metocean forcing providers for oil trajectory simulations.

Primary sources:
- Currents: CMEMS (Copernicus Marine) — free with registration
- Winds: Open-Meteo forecast/ERA5 — free, ≤10k calls/day (CC BY 4.0)

Fallback: if CMEMS unavailable → Open-Meteo marine (wind + wave).
All HTTP calls in this module must be offline-mockable (INV-7).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

from argus.core.errors import CmemsUnavailableError  # noqa: E402 — re-export for backward compat

_OPEN_METEO_BASE = "https://api.open-meteo.com/v1/forecast"
_OPEN_METEO_MARINE_BASE = "https://marine-api.open-meteo.com/v1/marine"
_CMEMS_BASE = "https://nrt.cmems-du.eu/motu-web/Motu"

__all__ = ["CmemsUnavailableError", "ForcingGrid", "get_forcing"]


@dataclass
class ForcingGrid:
    """Combined wind + current forcing for one simulation domain."""

    times: list[str]  # ISO-8601 UTC timestamps
    wind_u: list[float]  # eastward wind (m/s) at domain centre
    wind_v: list[float]  # northward wind (m/s) at domain centre
    current_u: list[float]  # eastward current (m/s)
    current_v: list[float]  # northward current (m/s)
    source: str  # "cmems+open_meteo" | "open_meteo_marine" (fallback)
    open_meteo_calls: int = 0  # quota tracking
    cmems_bytes: int = 0  # quota tracking


def fetch_open_meteo_winds(
    bbox: tuple[float, float, float, float],
    t0: str,
    t1: str,
    *,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    """Fetch hourly wind u/v from Open-Meteo at the domain centre."""
    s = session or requests.Session()
    min_lon, min_lat, max_lon, max_lat = bbox
    lat = (min_lat + max_lat) / 2
    lon = (min_lon + max_lon) / 2
    params: dict[str, Any] = {
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "hourly": "wind_speed_10m,wind_direction_10m",
        "wind_speed_unit": "ms",
        "start_date": t0[:10],
        "end_date": t1[:10],
        "timezone": "UTC",
    }
    resp = s.get(_OPEN_METEO_BASE, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()  # type: ignore[no-any-return]


def fetch_open_meteo_marine(
    bbox: tuple[float, float, float, float],
    t0: str,
    t1: str,
    *,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    """Fetch marine current proxy from Open-Meteo marine API (fallback)."""
    s = session or requests.Session()
    min_lon, min_lat, max_lon, max_lat = bbox
    lat = (min_lat + max_lat) / 2
    lon = (min_lon + max_lon) / 2
    params: dict[str, Any] = {
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "hourly": "ocean_current_velocity,ocean_current_direction",
        "start_date": t0[:10],
        "end_date": t1[:10],
        "timezone": "UTC",
    }
    resp = s.get(_OPEN_METEO_MARINE_BASE, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()  # type: ignore[no-any-return]


def fetch_cmems_currents(
    bbox: tuple[float, float, float, float],
    t0: str,
    t1: str,
    *,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    """Fetch surface current data from CMEMS NRT endpoint.

    Raises CmemsUnavailableError on connection failure or HTTP error.
    In production this calls the CMEMS Motu download service;
    in tests this is mocked.
    """
    s = session or requests.Session()
    min_lon, min_lat, max_lon, max_lat = bbox
    params: dict[str, Any] = {
        "service": "GLOBAL_ANALYSISFORECAST_PHY_001_024-TDS",
        "product": "cmems_mod_glo_phy-cur_anfc_0.083deg_P1H-m",
        "x_lo": min_lon,
        "x_hi": max_lon,
        "y_lo": min_lat,
        "y_hi": max_lat,
        "t_lo": t0,
        "t_hi": t1,
        "variable": "uo,vo",
        "action": "subset",
    }
    try:
        resp = s.get(_CMEMS_BASE, params=params, timeout=30)
        resp.raise_for_status()
    except (requests.ConnectionError, requests.HTTPError) as exc:
        raise CmemsUnavailableError(f"CMEMS unavailable: {exc}") from exc
    return resp.json()  # type: ignore[no-any-return]


def _wind_components(speed: float, direction_deg: float) -> tuple[float, float]:
    """Convert wind speed (m/s) + direction (°from N, clockwise) to u/v."""
    import math

    rad = math.radians(direction_deg)
    u = -speed * math.sin(rad)
    v = -speed * math.cos(rad)
    return round(u, 4), round(v, 4)


def _parse_open_meteo_winds(data: dict[str, Any]) -> tuple[list[str], list[float], list[float]]:
    times = data["hourly"]["time"]
    speeds = data["hourly"]["wind_speed_10m"]
    directions = data["hourly"]["wind_direction_10m"]
    u_list, v_list = [], []
    for spd, dirn in zip(speeds, directions, strict=True):
        u, v = _wind_components(float(spd or 0), float(dirn or 0))
        u_list.append(u)
        v_list.append(v)
    return times, u_list, v_list


def _parse_cmems_currents(data: dict[str, Any], n_times: int) -> tuple[list[float], list[float]]:
    """Extract surface current u/v from CMEMS response (domain-centre scalar)."""
    uo = data.get("uo", [0.0] * n_times)
    vo = data.get("vo", [0.0] * n_times)
    if len(uo) != n_times:
        uo = [float(uo[0])] * n_times if uo else [0.0] * n_times
    if len(vo) != n_times:
        vo = [float(vo[0])] * n_times if vo else [0.0] * n_times
    return [float(v) for v in uo], [float(v) for v in vo]


def _parse_open_meteo_marine(
    data: dict[str, Any],
) -> tuple[list[str], list[float], list[float]]:
    """Extract ocean current from Open-Meteo marine response (fallback)."""
    import math

    times = data["hourly"]["time"]
    speeds = data["hourly"].get("ocean_current_velocity") or [0.0] * len(times)
    directions = data["hourly"].get("ocean_current_direction") or [0.0] * len(times)
    u_list, v_list = [], []
    for spd, dirn in zip(speeds, directions, strict=True):
        rad = math.radians(float(dirn or 0))
        u = float(spd or 0) * math.sin(rad)
        v = float(spd or 0) * math.cos(rad)
        u_list.append(round(u, 4))
        v_list.append(round(v, 4))
    return times, u_list, v_list


def get_forcing(
    bbox: tuple[float, float, float, float],
    t0: str,
    t1: str,
    *,
    cache: Any | None = None,
    session: requests.Session | None = None,
) -> ForcingGrid:
    """Get combined wind + current forcing for the given bbox and time window.

    1. Check cache; return immediately if hit.
    2. Fetch winds from Open-Meteo.
    3. Try CMEMS for currents; fall back to Open-Meteo marine if unavailable.
    4. Merge into ForcingGrid; save to cache.
    """
    source = "cmems+open_meteo"
    if cache is not None:
        cached: ForcingGrid | None = cache.load(bbox, t0, t1, source)
        if cached is not None:
            return cached

    wind_data = fetch_open_meteo_winds(bbox, t0, t1, session=session)
    times, wind_u, wind_v = _parse_open_meteo_winds(wind_data)
    open_meteo_calls = 1

    try:
        cmems_data = fetch_cmems_currents(bbox, t0, t1, session=session)
        current_u, current_v = _parse_cmems_currents(cmems_data, len(times))
        cmems_bytes = len(str(cmems_data))
    except CmemsUnavailableError:
        source = "open_meteo_marine"
        marine_data = fetch_open_meteo_marine(bbox, t0, t1, session=session)
        _, current_u, current_v = _parse_open_meteo_marine(marine_data)
        open_meteo_calls += 1
        cmems_bytes = 0

    grid = ForcingGrid(
        times=times,
        wind_u=wind_u,
        wind_v=wind_v,
        current_u=current_u,
        current_v=current_v,
        source=source,
        open_meteo_calls=open_meteo_calls,
        cmems_bytes=cmems_bytes,
    )
    if cache is not None:
        cache.save(bbox, t0, t1, source, grid)
    return grid
