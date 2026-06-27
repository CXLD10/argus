"""Open-Meteo ERA5 weather feature fetching for WQ forecast drivers."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import requests

_OPEN_METEO_BASE = "https://api.open-meteo.com/v1/era5"
_REQUEST_TIMEOUT = 30


def fetch_weather_features(
    lon: float,
    lat: float,
    target_date: datetime,
    *,
    days_back: int = 7,
) -> dict[str, float]:
    """Fetch 7-day rolling precipitation and temperature from Open-Meteo ERA5.

    Returns {"precip_7d": float (mm), "temp_7d": float (°C mean)}.
    Raises requests.RequestException on network failure.
    """
    end_date = target_date.date()
    start_date = end_date - timedelta(days=days_back - 1)

    params: dict[str, Any] = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "daily": "precipitation_sum,temperature_2m_mean",
    }

    resp = requests.get(_OPEN_METEO_BASE, params=params, timeout=_REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()

    daily = data.get("daily", {})
    precip_series: list[float | None] = daily.get("precipitation_sum", [])
    temp_series: list[float | None] = daily.get("temperature_2m_mean", [])

    precip_7d = sum(v for v in precip_series if v is not None)
    temp_vals = [v for v in temp_series if v is not None]
    temp_7d = sum(temp_vals) / len(temp_vals) if temp_vals else 25.0

    return {"precip_7d": precip_7d, "temp_7d": temp_7d}
