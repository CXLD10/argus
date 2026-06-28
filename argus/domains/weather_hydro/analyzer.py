"""D3: WeatherHydroDomain — Domain protocol implementation.

search()   Returns SourceRefs for four Open-Meteo data products:
             om_forecast  → precipitation forecast (evidence_class="modeled")
             om_era5      → ERA5 historical precipitation (evidence_class="measured")
             om_glofas    → GloFAS river discharge (evidence_class="modeled")
             om_airq      → SO₂/NO₂ air quality (evidence_class="modeled")

acquire()  Fetches the Open-Meteo JSON response or uses mock data from ref.attrs.
           Each fetch = 1 API call (bytes_estimated = 1 per ref).

analyze()  Converts the fetched series to an Observation with the appropriate
           obs_type and evidence_class.  The full time series is in attrs["series"].

INV-7: pass ref.attrs["mock_response"] to bypass HTTP in offline / test mode.
INV-3: evidence_class matches source honesty rules from D3-weather-hydro.md.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from argus.core.models import MonitorTarget, Observation, SourceRef
from argus.domains.base import Acquisition
from argus.domains.weather_hydro.open_meteo import (
    fetch_air_quality,
    fetch_precip_era5,
    fetch_precip_forecast,
    fetch_river_discharge,
    parse_daily_series,
    parse_hourly_series,
    peak_value,
)

# Maps product suffix → (obs_type, unit, evidence_class, parse_fn, variable_key)
_PRODUCT_META: dict[str, tuple[str, str, str, str, str]] = {
    "om_forecast": ("precip_series", "mm", "modeled", "hourly", "precipitation"),
    "om_era5": ("precip_series", "mm", "measured", "hourly", "precipitation"),
    "om_glofas": ("discharge_series", "m3/s", "modeled", "daily", "river_discharge"),
    "om_airq_so2": ("so2_series", "μg/m3", "modeled", "hourly", "sulphur_dioxide"),
    "om_airq_no2": ("no2_series", "μg/m3", "modeled", "hourly", "nitrogen_dioxide"),
}


class WeatherHydroDomain:
    """D3 Domain: weather & hydro time-series ingestion via Open-Meteo."""

    domain_id: str = "weather_hydro"

    # ── Domain.search ─────────────────────────────────────────────────────────

    def search(
        self,
        target: MonitorTarget,
        t0: datetime,
        t1: datetime,
    ) -> list[SourceRef]:
        """Return one SourceRef per Open-Meteo data product for the AOI centroid.

        Product IDs are deterministic: {prefix}_{target_id}_{date} so the same
        day × target pair is idempotent across re-runs.
        """
        lat, lon = _centroid(target.geometry)
        date_tag = t0.strftime("%Y%m%d")
        start_date = t0.strftime("%Y-%m-%d")
        end_date = t1.strftime("%Y-%m-%d")
        footprint = _point_footprint(lat, lon)

        refs: list[SourceRef] = [
            SourceRef(
                product_id=f"om_forecast_{target.id}_{date_tag}",
                source="open_meteo:forecast",
                collection="OPEN-METEO-FORECAST",
                product_type="precip_forecast",
                sensor_mode="n/a",
                sensing_time=t0,
                footprint=footprint,
                polarizations=[],
                bytes_estimated=1,
                attrs={
                    "product": "om_forecast",
                    "lat": lat,
                    "lon": lon,
                    "aoi_id": target.aoi_id,
                    "t0": t0.isoformat(),
                    "t1": t1.isoformat(),
                },
            ),
            SourceRef(
                product_id=f"om_era5_{target.id}_{date_tag}",
                source="open_meteo:era5",
                collection="OPEN-METEO-ERA5",
                product_type="precip_era5",
                sensor_mode="n/a",
                sensing_time=t0,
                footprint=footprint,
                polarizations=[],
                bytes_estimated=1,
                attrs={
                    "product": "om_era5",
                    "lat": lat,
                    "lon": lon,
                    "start_date": start_date,
                    "end_date": end_date,
                    "aoi_id": target.aoi_id,
                    "t0": t0.isoformat(),
                    "t1": t1.isoformat(),
                },
            ),
            SourceRef(
                product_id=f"om_glofas_{target.id}_{date_tag}",
                source="open_meteo:glofas",
                collection="OPEN-METEO-GLOFAS",
                product_type="river_discharge",
                sensor_mode="n/a",
                sensing_time=t0,
                footprint=footprint,
                polarizations=[],
                bytes_estimated=1,
                attrs={
                    "product": "om_glofas",
                    "lat": lat,
                    "lon": lon,
                    "aoi_id": target.aoi_id,
                    "t0": t0.isoformat(),
                    "t1": t1.isoformat(),
                },
            ),
            SourceRef(
                product_id=f"om_airq_{target.id}_{date_tag}",
                source="open_meteo:air_quality",
                collection="OPEN-METEO-AIRQ",
                product_type="air_quality",
                sensor_mode="n/a",
                sensing_time=t0,
                footprint=footprint,
                polarizations=[],
                bytes_estimated=1,
                attrs={
                    "product": "om_airq",
                    "lat": lat,
                    "lon": lon,
                    "aoi_id": target.aoi_id,
                    "t0": t0.isoformat(),
                    "t1": t1.isoformat(),
                },
            ),
        ]
        return refs

    # ── Domain.acquire ────────────────────────────────────────────────────────

    def acquire(self, ref: SourceRef) -> Acquisition:
        """Fetch the Open-Meteo JSON for this ref.

        Offline / test mode: supply ref.attrs["mock_response"] to bypass HTTP.
        """
        product = ref.attrs.get("product", "")
        mock = ref.attrs.get("mock_response")
        lat: float = float(ref.attrs.get("lat", 0.0))
        lon: float = float(ref.attrs.get("lon", 0.0))

        if product == "om_forecast":
            data = fetch_precip_forecast(lat, lon, mock_response=mock)
        elif product == "om_era5":
            data = fetch_precip_era5(
                lat,
                lon,
                ref.attrs.get("start_date", "2024-01-01"),
                ref.attrs.get("end_date", "2024-01-07"),
                mock_response=mock,
            )
        elif product == "om_glofas":
            data = fetch_river_discharge(lat, lon, mock_response=mock)
        elif product == "om_airq":
            data = fetch_air_quality(lat, lon, mock_response=mock)
        else:
            raise ValueError(f"Unknown weather product: {product!r}")

        return Acquisition(
            scene_id=str(uuid.uuid4()),
            source_ref=ref,
            preprocessed=data,
            attrs=dict(ref.attrs),
        )

    # ── Domain.analyze ────────────────────────────────────────────────────────

    def analyze(self, acq: Acquisition) -> list[Observation]:
        """Convert fetched Open-Meteo JSON to Observation(s).

        The air quality product produces two Observations (so2_series + no2_series).
        All others produce one Observation per Acquisition.

        INV-3: evidence_class is "measured" for ERA5, "modeled" for forecasts/GloFAS/AQ.
        """
        data: dict[str, Any] | None = acq.preprocessed
        if data is None:
            return []

        product: str = acq.attrs.get("product", "")
        lat: float = float(acq.attrs.get("lat", 0.0))
        lon: float = float(acq.attrs.get("lon", 0.0))
        now = datetime.now(UTC)
        analysis_run_id = acq.attrs.get("analysis_run_id", "")

        geometry = {"type": "Point", "coordinates": [lon, lat]}

        if product == "om_forecast":
            return [
                _make_obs(
                    series=parse_hourly_series(data, "precipitation"),
                    obs_type="precip_series",
                    unit="mm",
                    evidence_class="modeled",
                    source="open_meteo:forecast",
                    scene_id=acq.scene_id,
                    analysis_run_id=analysis_run_id,
                    geometry=geometry,
                    now=now,
                )
            ]

        if product == "om_era5":
            return [
                _make_obs(
                    series=parse_hourly_series(data, "precipitation"),
                    obs_type="precip_series",
                    unit="mm",
                    evidence_class="measured",
                    source="open_meteo:era5",
                    scene_id=acq.scene_id,
                    analysis_run_id=analysis_run_id,
                    geometry=geometry,
                    now=now,
                )
            ]

        if product == "om_glofas":
            return [
                _make_obs(
                    series=parse_daily_series(data, "river_discharge"),
                    obs_type="discharge_series",
                    unit="m3/s",
                    evidence_class="modeled",
                    source="open_meteo:glofas",
                    scene_id=acq.scene_id,
                    analysis_run_id=analysis_run_id,
                    geometry=geometry,
                    now=now,
                )
            ]

        if product == "om_airq":
            so2_series = parse_hourly_series(data, "sulphur_dioxide")
            no2_series = parse_hourly_series(data, "nitrogen_dioxide")
            observations: list[Observation] = []
            if so2_series:
                observations.append(
                    _make_obs(
                        series=so2_series,
                        obs_type="so2_series",
                        unit="μg/m3",
                        evidence_class="modeled",
                        source="open_meteo:air_quality",
                        scene_id=acq.scene_id,
                        analysis_run_id=analysis_run_id,
                        geometry=geometry,
                        now=now,
                    )
                )
            if no2_series:
                observations.append(
                    _make_obs(
                        series=no2_series,
                        obs_type="no2_series",
                        unit="μg/m3",
                        evidence_class="modeled",
                        source="open_meteo:air_quality",
                        scene_id=acq.scene_id,
                        analysis_run_id=analysis_run_id,
                        geometry=geometry,
                        now=now,
                    )
                )
            return observations

        return []


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_obs(
    *,
    series: list[dict[str, Any]],
    obs_type: str,
    unit: str,
    evidence_class: str,
    source: str,
    scene_id: str,
    analysis_run_id: str,
    geometry: dict[str, Any],
    now: datetime,
) -> Observation:
    pv = peak_value(series)
    return Observation(
        id=str(uuid.uuid4()),
        analysis_run_id=analysis_run_id,
        scene_id=scene_id,
        obs_type=obs_type,
        evidence_class=evidence_class,  # type: ignore[arg-type]
        geometry=geometry,
        area_km2=0.0,
        confidence=1.0,
        domain="weather_hydro",
        value=pv,
        unit=unit,
        attrs={
            "source": source,
            "series": series,
            "n_points": len(series),
        },
        created_at=now,
    )


def _centroid(geometry: dict[str, Any]) -> tuple[float, float]:
    """Return (lat, lon) centroid from a GeoJSON geometry."""
    gtype = geometry.get("type", "")
    coords: Any = geometry.get("coordinates", [])
    if gtype == "Point":
        return float(coords[1]), float(coords[0])
    flat = _flatten(coords, gtype)
    if not flat:
        return 0.0, 0.0
    lons = [c[0] for c in flat]
    lats = [c[1] for c in flat]
    return sum(lats) / len(lats), sum(lons) / len(lons)


def _flatten(coords: Any, gtype: str) -> list[list[float]]:
    if gtype == "Polygon":
        return [c for ring in coords for c in ring]
    if gtype == "MultiPolygon":
        return [c for poly in coords for ring in poly for c in ring]
    if gtype == "LineString":
        return list(coords)
    return []


def _point_footprint(lat: float, lon: float) -> dict[str, Any]:
    """Return a tiny bounding box GeoJSON polygon around the centroid point."""
    d = 0.01
    return {
        "type": "Polygon",
        "coordinates": [[
            [lon - d, lat - d],
            [lon + d, lat - d],
            [lon + d, lat + d],
            [lon - d, lat + d],
            [lon - d, lat - d],
        ]],
    }
