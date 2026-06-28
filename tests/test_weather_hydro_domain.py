"""Tests for F-041: D3 Weather & Hydro domain — Open-Meteo ingestion.

All tests are offline (INV-7).  Open-Meteo responses are injected via
ref.attrs["mock_response"] — no real HTTP calls.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from argus.core.models import MonitorTarget
from argus.core.store import Store
from argus.domains.base import Acquisition
from argus.domains.weather_hydro.analyzer import WeatherHydroDomain
from argus.domains.weather_hydro.open_meteo import (
    ATTRIBUTION,
    parse_daily_series,
    parse_hourly_series,
    peak_value,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def domain() -> WeatherHydroDomain:
    return WeatherHydroDomain()


@pytest.fixture()
def target() -> MonitorTarget:
    return MonitorTarget(
        id="test_target",
        aoi_id="tobago",
        kind="region",
        name="Tobago Region",
        geometry={
            "type": "Polygon",
            "coordinates": [
                [
                    [-61.5, 11.0],
                    [-61.0, 11.0],
                    [-61.0, 11.5],
                    [-61.5, 11.5],
                    [-61.5, 11.0],
                ]
            ],
        },
        domains=["weather_hydro"],
    )


@pytest.fixture()
def t0() -> datetime:
    return datetime(2024, 1, 1, tzinfo=UTC)


@pytest.fixture()
def t1() -> datetime:
    return datetime(2024, 1, 7, tzinfo=UTC)


@pytest.fixture()
def mock_precip_forecast() -> dict:
    return {
        "hourly": {
            "time": ["2024-01-01T00:00", "2024-01-01T01:00", "2024-01-01T02:00"],
            "precipitation": [0.0, 5.2, 12.8],
        }
    }


@pytest.fixture()
def mock_era5_response() -> dict:
    return {
        "hourly": {
            "time": ["2024-01-01T00:00", "2024-01-01T01:00"],
            "precipitation": [3.5, 7.1],
        }
    }


@pytest.fixture()
def mock_glofas_response() -> dict:
    return {
        "daily": {
            "time": ["2024-01-01", "2024-01-02"],
            "river_discharge": [45.2, 62.8],
        }
    }


@pytest.fixture()
def mock_airq_response() -> dict:
    return {
        "hourly": {
            "time": ["2024-01-01T00:00", "2024-01-01T01:00"],
            "sulphur_dioxide": [0.5, 1.2],
            "nitrogen_dioxide": [8.4, 9.1],
        }
    }


@pytest.fixture()
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "argus.db")


# ── open_meteo module: parsers ─────────────────────────────────────────────────


def test_attribution_string_present() -> None:
    """CC BY 4.0 attribution must be present in the module."""
    assert "open-meteo.com" in ATTRIBUTION
    assert "CC BY 4.0" in ATTRIBUTION


def test_parse_hourly_series_extracts_values(mock_precip_forecast: dict) -> None:
    series = parse_hourly_series(mock_precip_forecast, "precipitation")
    assert len(series) == 3
    assert series[0]["ts"] == "2024-01-01T00:00"
    assert series[0]["value"] == pytest.approx(0.0)


def test_parse_hourly_series_filters_none() -> None:
    response = {
        "hourly": {
            "time": ["T1", "T2", "T3"],
            "precip": [1.0, None, 3.0],
        }
    }
    series = parse_hourly_series(response, "precip")
    assert len(series) == 2
    assert all(p["value"] is not None for p in series)


def test_parse_hourly_series_missing_variable_returns_empty(mock_precip_forecast: dict) -> None:
    series = parse_hourly_series(mock_precip_forecast, "nonexistent")
    assert series == []


def test_parse_daily_series_extracts_values(mock_glofas_response: dict) -> None:
    series = parse_daily_series(mock_glofas_response, "river_discharge")
    assert len(series) == 2
    assert series[1]["value"] == pytest.approx(62.8)


def test_parse_daily_series_empty_response() -> None:
    series = parse_daily_series({}, "river_discharge")
    assert series == []


def test_peak_value_returns_max(mock_precip_forecast: dict) -> None:
    series = parse_hourly_series(mock_precip_forecast, "precipitation")
    pv = peak_value(series)
    assert pv == pytest.approx(12.8)


def test_peak_value_empty_series() -> None:
    assert peak_value([]) is None


def test_peak_value_all_zeros() -> None:
    series = [{"ts": "T0", "value": 0.0}, {"ts": "T1", "value": 0.0}]
    assert peak_value(series) == pytest.approx(0.0)


# ── Domain.search ─────────────────────────────────────────────────────────────


def test_search_returns_four_refs(
    domain: WeatherHydroDomain, target: MonitorTarget, t0: datetime, t1: datetime
) -> None:
    refs = domain.search(target, t0, t1)
    assert len(refs) == 4


def test_search_product_ids_stable(
    domain: WeatherHydroDomain, target: MonitorTarget, t0: datetime, t1: datetime
) -> None:
    refs1 = domain.search(target, t0, t1)
    refs2 = domain.search(target, t0, t1)
    assert [r.product_id for r in refs1] == [r.product_id for r in refs2]


def test_search_product_ids_distinct(
    domain: WeatherHydroDomain, target: MonitorTarget, t0: datetime, t1: datetime
) -> None:
    refs = domain.search(target, t0, t1)
    ids = [r.product_id for r in refs]
    assert len(set(ids)) == len(ids)


def test_search_forecast_ref_has_bytes_estimated_1(
    domain: WeatherHydroDomain, target: MonitorTarget, t0: datetime, t1: datetime
) -> None:
    refs = domain.search(target, t0, t1)
    for ref in refs:
        assert ref.bytes_estimated == 1


def test_search_refs_have_aoi_id_in_attrs(
    domain: WeatherHydroDomain, target: MonitorTarget, t0: datetime, t1: datetime
) -> None:
    refs = domain.search(target, t0, t1)
    for ref in refs:
        assert ref.attrs.get("aoi_id") == target.aoi_id


def test_search_contains_forecast_ref(
    domain: WeatherHydroDomain, target: MonitorTarget, t0: datetime, t1: datetime
) -> None:
    refs = domain.search(target, t0, t1)
    products = [r.attrs.get("product") for r in refs]
    assert "om_forecast" in products


def test_search_contains_era5_ref(
    domain: WeatherHydroDomain, target: MonitorTarget, t0: datetime, t1: datetime
) -> None:
    refs = domain.search(target, t0, t1)
    products = [r.attrs.get("product") for r in refs]
    assert "om_era5" in products


def test_search_contains_glofas_ref(
    domain: WeatherHydroDomain, target: MonitorTarget, t0: datetime, t1: datetime
) -> None:
    refs = domain.search(target, t0, t1)
    products = [r.attrs.get("product") for r in refs]
    assert "om_glofas" in products


def test_search_contains_airq_ref(
    domain: WeatherHydroDomain, target: MonitorTarget, t0: datetime, t1: datetime
) -> None:
    refs = domain.search(target, t0, t1)
    products = [r.attrs.get("product") for r in refs]
    assert "om_airq" in products


# ── Domain.acquire (offline — mock_response) ──────────────────────────────────


def _get_ref(domain: WeatherHydroDomain, target: MonitorTarget, t0: datetime, t1: datetime, product: str):  # type: ignore[return]
    refs = domain.search(target, t0, t1)
    for r in refs:
        if r.attrs.get("product") == product:
            return r


def test_acquire_forecast_returns_acquisition(
    domain: WeatherHydroDomain,
    target: MonitorTarget,
    t0: datetime,
    t1: datetime,
    mock_precip_forecast: dict,
) -> None:
    ref = _get_ref(domain, target, t0, t1, "om_forecast")
    ref.attrs["mock_response"] = mock_precip_forecast
    acq = domain.acquire(ref)
    assert isinstance(acq, Acquisition)


def test_acquire_forecast_preprocessed_is_dict(
    domain: WeatherHydroDomain,
    target: MonitorTarget,
    t0: datetime,
    t1: datetime,
    mock_precip_forecast: dict,
) -> None:
    ref = _get_ref(domain, target, t0, t1, "om_forecast")
    ref.attrs["mock_response"] = mock_precip_forecast
    acq = domain.acquire(ref)
    assert isinstance(acq.preprocessed, dict)
    assert "hourly" in acq.preprocessed


def test_acquire_era5_preprocessed_is_dict(
    domain: WeatherHydroDomain,
    target: MonitorTarget,
    t0: datetime,
    t1: datetime,
    mock_era5_response: dict,
) -> None:
    ref = _get_ref(domain, target, t0, t1, "om_era5")
    ref.attrs["mock_response"] = mock_era5_response
    acq = domain.acquire(ref)
    assert isinstance(acq.preprocessed, dict)


def test_acquire_glofas_preprocessed_is_dict(
    domain: WeatherHydroDomain,
    target: MonitorTarget,
    t0: datetime,
    t1: datetime,
    mock_glofas_response: dict,
) -> None:
    ref = _get_ref(domain, target, t0, t1, "om_glofas")
    ref.attrs["mock_response"] = mock_glofas_response
    acq = domain.acquire(ref)
    assert isinstance(acq.preprocessed, dict)


def test_acquire_airq_preprocessed_is_dict(
    domain: WeatherHydroDomain,
    target: MonitorTarget,
    t0: datetime,
    t1: datetime,
    mock_airq_response: dict,
) -> None:
    ref = _get_ref(domain, target, t0, t1, "om_airq")
    ref.attrs["mock_response"] = mock_airq_response
    acq = domain.acquire(ref)
    assert isinstance(acq.preprocessed, dict)


def test_acquire_unknown_product_raises(
    domain: WeatherHydroDomain,
    target: MonitorTarget,
    t0: datetime,
    t1: datetime,
) -> None:
    ref = _get_ref(domain, target, t0, t1, "om_forecast")
    ref.attrs["product"] = "om_unknown"
    with pytest.raises(ValueError, match="Unknown weather product"):
        domain.acquire(ref)


# ── Domain.analyze: forecast → precip_series/modeled ─────────────────────────


def test_analyze_forecast_returns_one_observation(
    domain: WeatherHydroDomain,
    target: MonitorTarget,
    t0: datetime,
    t1: datetime,
    mock_precip_forecast: dict,
) -> None:
    ref = _get_ref(domain, target, t0, t1, "om_forecast")
    ref.attrs["mock_response"] = mock_precip_forecast
    acq = domain.acquire(ref)
    obs_list = domain.analyze(acq)
    assert len(obs_list) == 1


def test_analyze_forecast_obs_type_is_precip_series(
    domain: WeatherHydroDomain,
    target: MonitorTarget,
    t0: datetime,
    t1: datetime,
    mock_precip_forecast: dict,
) -> None:
    """F-041 AC: Open-Meteo precip forecast → obs_type='precip_series'."""
    ref = _get_ref(domain, target, t0, t1, "om_forecast")
    ref.attrs["mock_response"] = mock_precip_forecast
    acq = domain.acquire(ref)
    obs = domain.analyze(acq)[0]
    assert obs.obs_type == "precip_series"


def test_analyze_forecast_evidence_class_is_modeled(
    domain: WeatherHydroDomain,
    target: MonitorTarget,
    t0: datetime,
    t1: datetime,
    mock_precip_forecast: dict,
) -> None:
    """F-041 AC: forecast evidence_class must be 'modeled' (INV-3)."""
    ref = _get_ref(domain, target, t0, t1, "om_forecast")
    ref.attrs["mock_response"] = mock_precip_forecast
    acq = domain.acquire(ref)
    obs = domain.analyze(acq)[0]
    assert obs.evidence_class == "modeled"


def test_analyze_forecast_series_in_attrs(
    domain: WeatherHydroDomain,
    target: MonitorTarget,
    t0: datetime,
    t1: datetime,
    mock_precip_forecast: dict,
) -> None:
    ref = _get_ref(domain, target, t0, t1, "om_forecast")
    ref.attrs["mock_response"] = mock_precip_forecast
    acq = domain.acquire(ref)
    obs = domain.analyze(acq)[0]
    assert "series" in obs.attrs
    assert len(obs.attrs["series"]) == 3


def test_analyze_forecast_value_is_peak(
    domain: WeatherHydroDomain,
    target: MonitorTarget,
    t0: datetime,
    t1: datetime,
    mock_precip_forecast: dict,
) -> None:
    ref = _get_ref(domain, target, t0, t1, "om_forecast")
    ref.attrs["mock_response"] = mock_precip_forecast
    acq = domain.acquire(ref)
    obs = domain.analyze(acq)[0]
    assert obs.value == pytest.approx(12.8)


def test_analyze_forecast_unit_is_mm(
    domain: WeatherHydroDomain,
    target: MonitorTarget,
    t0: datetime,
    t1: datetime,
    mock_precip_forecast: dict,
) -> None:
    ref = _get_ref(domain, target, t0, t1, "om_forecast")
    ref.attrs["mock_response"] = mock_precip_forecast
    acq = domain.acquire(ref)
    obs = domain.analyze(acq)[0]
    assert obs.unit == "mm"


# ── Domain.analyze: ERA5 → precip_series/measured ────────────────────────────


def test_analyze_era5_evidence_class_is_measured(
    domain: WeatherHydroDomain,
    target: MonitorTarget,
    t0: datetime,
    t1: datetime,
    mock_era5_response: dict,
) -> None:
    """F-041 AC: ERA5 history → evidence_class='measured' (INV-3 honesty rule)."""
    ref = _get_ref(domain, target, t0, t1, "om_era5")
    ref.attrs["mock_response"] = mock_era5_response
    acq = domain.acquire(ref)
    obs = domain.analyze(acq)[0]
    assert obs.evidence_class == "measured"


def test_analyze_era5_obs_type_is_precip_series(
    domain: WeatherHydroDomain,
    target: MonitorTarget,
    t0: datetime,
    t1: datetime,
    mock_era5_response: dict,
) -> None:
    ref = _get_ref(domain, target, t0, t1, "om_era5")
    ref.attrs["mock_response"] = mock_era5_response
    acq = domain.acquire(ref)
    obs = domain.analyze(acq)[0]
    assert obs.obs_type == "precip_series"


def test_analyze_era5_source_in_attrs(
    domain: WeatherHydroDomain,
    target: MonitorTarget,
    t0: datetime,
    t1: datetime,
    mock_era5_response: dict,
) -> None:
    ref = _get_ref(domain, target, t0, t1, "om_era5")
    ref.attrs["mock_response"] = mock_era5_response
    acq = domain.acquire(ref)
    obs = domain.analyze(acq)[0]
    assert obs.attrs.get("source") == "open_meteo:era5"


# ── Domain.analyze: GloFAS → discharge_series/modeled ────────────────────────


def test_analyze_glofas_obs_type_is_discharge_series(
    domain: WeatherHydroDomain,
    target: MonitorTarget,
    t0: datetime,
    t1: datetime,
    mock_glofas_response: dict,
) -> None:
    ref = _get_ref(domain, target, t0, t1, "om_glofas")
    ref.attrs["mock_response"] = mock_glofas_response
    acq = domain.acquire(ref)
    obs = domain.analyze(acq)[0]
    assert obs.obs_type == "discharge_series"


def test_analyze_glofas_evidence_class_is_modeled(
    domain: WeatherHydroDomain,
    target: MonitorTarget,
    t0: datetime,
    t1: datetime,
    mock_glofas_response: dict,
) -> None:
    ref = _get_ref(domain, target, t0, t1, "om_glofas")
    ref.attrs["mock_response"] = mock_glofas_response
    acq = domain.acquire(ref)
    obs = domain.analyze(acq)[0]
    assert obs.evidence_class == "modeled"


def test_analyze_glofas_unit_is_m3s(
    domain: WeatherHydroDomain,
    target: MonitorTarget,
    t0: datetime,
    t1: datetime,
    mock_glofas_response: dict,
) -> None:
    ref = _get_ref(domain, target, t0, t1, "om_glofas")
    ref.attrs["mock_response"] = mock_glofas_response
    acq = domain.acquire(ref)
    obs = domain.analyze(acq)[0]
    assert obs.unit == "m3/s"


def test_analyze_glofas_value_is_peak(
    domain: WeatherHydroDomain,
    target: MonitorTarget,
    t0: datetime,
    t1: datetime,
    mock_glofas_response: dict,
) -> None:
    ref = _get_ref(domain, target, t0, t1, "om_glofas")
    ref.attrs["mock_response"] = mock_glofas_response
    acq = domain.acquire(ref)
    obs = domain.analyze(acq)[0]
    assert obs.value == pytest.approx(62.8)


# ── Domain.analyze: air quality → so2_series + no2_series/modeled ────────────


def test_analyze_airq_returns_two_observations(
    domain: WeatherHydroDomain,
    target: MonitorTarget,
    t0: datetime,
    t1: datetime,
    mock_airq_response: dict,
) -> None:
    ref = _get_ref(domain, target, t0, t1, "om_airq")
    ref.attrs["mock_response"] = mock_airq_response
    acq = domain.acquire(ref)
    obs_list = domain.analyze(acq)
    assert len(obs_list) == 2


def test_analyze_airq_obs_types(
    domain: WeatherHydroDomain,
    target: MonitorTarget,
    t0: datetime,
    t1: datetime,
    mock_airq_response: dict,
) -> None:
    ref = _get_ref(domain, target, t0, t1, "om_airq")
    ref.attrs["mock_response"] = mock_airq_response
    acq = domain.acquire(ref)
    obs_types = {o.obs_type for o in domain.analyze(acq)}
    assert "so2_series" in obs_types
    assert "no2_series" in obs_types


def test_analyze_airq_evidence_class_is_modeled(
    domain: WeatherHydroDomain,
    target: MonitorTarget,
    t0: datetime,
    t1: datetime,
    mock_airq_response: dict,
) -> None:
    ref = _get_ref(domain, target, t0, t1, "om_airq")
    ref.attrs["mock_response"] = mock_airq_response
    acq = domain.acquire(ref)
    for obs in domain.analyze(acq):
        assert obs.evidence_class == "modeled"


def test_analyze_airq_so2_peak_value(
    domain: WeatherHydroDomain,
    target: MonitorTarget,
    t0: datetime,
    t1: datetime,
    mock_airq_response: dict,
) -> None:
    ref = _get_ref(domain, target, t0, t1, "om_airq")
    ref.attrs["mock_response"] = mock_airq_response
    acq = domain.acquire(ref)
    so2_obs = next(o for o in domain.analyze(acq) if o.obs_type == "so2_series")
    assert so2_obs.value == pytest.approx(1.2)


def test_analyze_airq_empty_so2_omits_observation(
    domain: WeatherHydroDomain,
    target: MonitorTarget,
    t0: datetime,
    t1: datetime,
) -> None:
    ref = _get_ref(domain, target, t0, t1, "om_airq")
    ref.attrs["mock_response"] = {
        "hourly": {
            "time": ["2024-01-01T00:00"],
            "sulphur_dioxide": [],
            "nitrogen_dioxide": [9.0],
        }
    }
    acq = domain.acquire(ref)
    obs_types = {o.obs_type for o in domain.analyze(acq)}
    assert "so2_series" not in obs_types
    assert "no2_series" in obs_types


# ── General Observation properties ───────────────────────────────────────────


def test_analyze_observations_have_geojson_point_geometry(
    domain: WeatherHydroDomain,
    target: MonitorTarget,
    t0: datetime,
    t1: datetime,
    mock_precip_forecast: dict,
) -> None:
    ref = _get_ref(domain, target, t0, t1, "om_forecast")
    ref.attrs["mock_response"] = mock_precip_forecast
    acq = domain.acquire(ref)
    for obs in domain.analyze(acq):
        assert obs.geometry["type"] == "Point"
        assert len(obs.geometry["coordinates"]) == 2


def test_analyze_observations_domain_is_weather_hydro(
    domain: WeatherHydroDomain,
    target: MonitorTarget,
    t0: datetime,
    t1: datetime,
    mock_precip_forecast: dict,
) -> None:
    ref = _get_ref(domain, target, t0, t1, "om_forecast")
    ref.attrs["mock_response"] = mock_precip_forecast
    acq = domain.acquire(ref)
    for obs in domain.analyze(acq):
        assert obs.domain == "weather_hydro"


def test_analyze_null_preprocessed_returns_empty(
    domain: WeatherHydroDomain,
    target: MonitorTarget,
    t0: datetime,
    t1: datetime,
) -> None:
    ref = _get_ref(domain, target, t0, t1, "om_forecast")
    acq = Acquisition(scene_id="s1", source_ref=ref, preprocessed=None, attrs=ref.attrs)
    assert domain.analyze(acq) == []


# ── Quota tracking: bytes_estimated = 1 per ref ──────────────────────────────


def test_bytes_estimated_equals_api_call_count(
    domain: WeatherHydroDomain, target: MonitorTarget, t0: datetime, t1: datetime
) -> None:
    refs = domain.search(target, t0, t1)
    total_estimated = sum(r.bytes_estimated or 0 for r in refs)
    # 4 refs × 1 call each = 4 API calls total
    assert total_estimated == 4


# ── Store: open_meteo_calls_today via RunHistory ──────────────────────────────


def test_open_meteo_calls_today_zero_when_no_history(store: Store) -> None:
    result = store.open_meteo_calls_today(datetime.now(UTC))
    assert result == 0


def test_open_meteo_calls_today_sums_weather_hydro_bytes_used(store: Store) -> None:
    from argus.core.models import RunHistory

    now = datetime.now(UTC)
    store.save_run_history(
        RunHistory(
            id="rh1",
            domain_id="weather_hydro",
            aoi_id="tobago",
            t_start=now,
            t_end=now,
            bytes_used=4,
            status="complete",
        )
    )
    assert store.open_meteo_calls_today(now) == 4


def test_open_meteo_calls_today_ignores_other_domains(store: Store) -> None:
    from argus.core.models import RunHistory

    now = datetime.now(UTC)
    store.save_run_history(
        RunHistory(
            id="rh-oil",
            domain_id="marine_oil",
            aoi_id="tobago",
            t_start=now,
            t_end=now,
            bytes_used=1000000,
            status="complete",
        )
    )
    assert store.open_meteo_calls_today(now) == 0


def test_open_meteo_calls_today_sums_multiple_runs(store: Store) -> None:
    from argus.core.models import RunHistory

    now = datetime.now(UTC)
    for i in range(3):
        store.save_run_history(
            RunHistory(
                id=f"rh-{i}",
                domain_id="weather_hydro",
                aoi_id="tobago",
                t_start=now,
                t_end=now,
                bytes_used=4,
                status="complete",
            )
        )
    assert store.open_meteo_calls_today(now) == 12
