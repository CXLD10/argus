"""Open-Meteo API client for D3 weather & hydro data.

Supports four endpoints:
  - Forecast API: hourly precipitation / temperature / wind (7-day forward)
  - Historical API (ERA5): hourly precipitation / temperature history
  - Marine / Hydro (GloFAS): daily river discharge at a coordinate
  - Air Quality API: hourly SO₂ / NO₂ column concentrations

Each function returns a dict matching the Open-Meteo JSON schema.  In offline / test
mode, callers inject a ``mock_response`` dict to bypass the network (INV-7).

Attribution (CC BY 4.0 required): "Weather data by Open-Meteo (https://open-meteo.com/)"
"""

from __future__ import annotations

from typing import Any

# ── Public endpoint constants ─────────────────────────────────────────────────

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
HISTORICAL_URL = "https://archive-api.open-meteo.com/v1/archive"
GLOFAS_URL = "https://flood-api.open-meteo.com/v1/flood"
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

# Open-Meteo CC BY 4.0 attribution string.
ATTRIBUTION = "Weather data by Open-Meteo (https://open-meteo.com/) — CC BY 4.0"


# ── Fetch functions ───────────────────────────────────────────────────────────


def fetch_precip_forecast(
    lat: float,
    lon: float,
    *,
    mock_response: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Fetch 7-day hourly precipitation forecast from Open-Meteo.

    Returns raw JSON dict with ``hourly.time`` and ``hourly.precipitation``.
    Pass ``mock_response`` in offline / test contexts to avoid network calls (INV-7).
    """
    if mock_response is not None:
        return mock_response

    import urllib.request

    params = (
        f"?latitude={lat}&longitude={lon}"
        "&hourly=precipitation"
        "&forecast_days=7"
        "&timezone=UTC"
    )
    with urllib.request.urlopen(FORECAST_URL + params, timeout=30) as resp:  # noqa: S310
        import json

        return json.loads(resp.read())  # type: ignore[no-any-return]


def fetch_precip_era5(
    lat: float,
    lon: float,
    start_date: str,
    end_date: str,
    *,
    mock_response: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Fetch hourly ERA5 historical precipitation from Open-Meteo archive.

    ``start_date`` / ``end_date`` in YYYY-MM-DD format.
    evidence_class should be "measured" (reanalysis is closest to observation).
    """
    if mock_response is not None:
        return mock_response

    import urllib.request

    params = (
        f"?latitude={lat}&longitude={lon}"
        f"&start_date={start_date}&end_date={end_date}"
        "&hourly=precipitation"
        "&timezone=UTC"
    )
    with urllib.request.urlopen(HISTORICAL_URL + params, timeout=30) as resp:  # noqa: S310
        import json

        return json.loads(resp.read())  # type: ignore[no-any-return]


def fetch_river_discharge(
    lat: float,
    lon: float,
    *,
    mock_response: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Fetch 7-day daily GloFAS river discharge forecast.

    evidence_class should be "modeled" (GloFAS is an ensemble model).
    Requires CC BY 4.0 attribution.
    """
    if mock_response is not None:
        return mock_response

    import urllib.request

    params = f"?latitude={lat}&longitude={lon}&daily=river_discharge&forecast_days=7"
    with urllib.request.urlopen(GLOFAS_URL + params, timeout=30) as resp:  # noqa: S310
        import json

        return json.loads(resp.read())  # type: ignore[no-any-return]


def fetch_air_quality(
    lat: float,
    lon: float,
    *,
    mock_response: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Fetch hourly SO₂ and NO₂ column concentrations from Open-Meteo Air Quality.

    evidence_class is "modeled" — the AQ API uses CAMS reanalysis/forecast.
    """
    if mock_response is not None:
        return mock_response

    import urllib.request

    params = (
        f"?latitude={lat}&longitude={lon}"
        "&hourly=sulphur_dioxide,nitrogen_dioxide"
        "&forecast_days=3"
        "&timezone=UTC"
    )
    with urllib.request.urlopen(AIR_QUALITY_URL + params, timeout=30) as resp:  # noqa: S310
        import json

        return json.loads(resp.read())  # type: ignore[no-any-return]


# ── Response parsers ──────────────────────────────────────────────────────────


def parse_hourly_series(
    response: dict[str, Any],
    variable_key: str,
) -> list[dict[str, Any]]:
    """Extract [{ts, value}] from an Open-Meteo hourly response.

    Returns empty list on missing / malformed data rather than raising.
    """
    hourly = response.get("hourly", {})
    times = hourly.get("time", [])
    values = hourly.get(variable_key, [])
    return [
        {"ts": t, "value": v}
        for t, v in zip(times, values, strict=False)
        if v is not None
    ]


def parse_daily_series(
    response: dict[str, Any],
    variable_key: str,
) -> list[dict[str, Any]]:
    """Extract [{ts, value}] from an Open-Meteo daily response."""
    daily = response.get("daily", {})
    times = daily.get("time", [])
    values = daily.get(variable_key, [])
    return [
        {"ts": t, "value": v}
        for t, v in zip(times, values, strict=False)
        if v is not None
    ]


def peak_value(series: list[dict[str, Any]]) -> float | None:
    """Return the maximum value in the series, or None if empty."""
    vals = [p["value"] for p in series if p.get("value") is not None]
    return max(vals) if vals else None
