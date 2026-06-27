"""F-012 tests: metocean forcing providers, cache, and fallback logic."""

from __future__ import annotations

import json
import math
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import requests

from argus.predict.oil_trajectory.cache import ForcingCache, _cache_key
from argus.predict.oil_trajectory.forcing import (
    ForcingGrid,
    _parse_open_meteo_winds,
    _wind_components,
    fetch_open_meteo_winds,
    get_forcing,
)

_REPO_ROOT = Path(__file__).parent.parent
_TOBAGO_BBOX = (-61.2, 10.8, -60.3, 11.5)
_T0 = "2024-02-07"
_T1 = "2024-02-07"

_WIND_FIXTURE = json.loads(
    (_REPO_ROOT / "tests" / "fixtures" / "open_meteo_winds_tobago.json").read_text()
)

_CMEMS_FIXTURE = {
    "uo": [0.15, 0.18, 0.12],
    "vo": [-0.08, -0.10, -0.07],
}

_MARINE_FIXTURE = {
    "hourly": {
        "time": ["2024-02-07T00:00", "2024-02-07T01:00", "2024-02-07T02:00"],
        "ocean_current_velocity": [0.2, 0.22, 0.18],
        "ocean_current_direction": [45.0, 50.0, 40.0],
    }
}


def _make_mock_session(wind_data: dict, cmems_data: dict | None = None) -> MagicMock:
    """Return a mock requests.Session whose .get() dispatches by URL."""

    def _get(url: str, **_: object) -> MagicMock:
        resp = MagicMock(spec=requests.Response)
        if "marine-api" in url:
            resp.json.return_value = _MARINE_FIXTURE
        elif "open-meteo" in url:
            resp.json.return_value = wind_data
        elif "cmems" in url:
            if cmems_data is None:
                raise requests.ConnectionError("CMEMS mocked as unavailable")
            resp.json.return_value = cmems_data
        resp.raise_for_status = MagicMock()
        return resp

    session = MagicMock(spec=requests.Session)
    session.get.side_effect = _get
    return session


# ── ForcingGrid ───────────────────────────────────────────────────────────────


def test_forcing_grid_has_all_fields() -> None:
    grid = ForcingGrid(
        times=["2024-02-07T00:00"],
        wind_u=[1.0],
        wind_v=[-0.5],
        current_u=[0.1],
        current_v=[-0.05],
        source="cmems+open_meteo",
    )
    assert grid.source == "cmems+open_meteo"
    assert grid.open_meteo_calls == 0  # default
    assert grid.cmems_bytes == 0


def test_wind_components_northerly() -> None:
    u, v = _wind_components(10.0, 0.0)
    assert math.isclose(u, 0.0, abs_tol=1e-6)
    assert math.isclose(v, -10.0, abs_tol=1e-4)


def test_wind_components_easterly() -> None:
    u, v = _wind_components(10.0, 90.0)
    assert math.isclose(u, -10.0, abs_tol=1e-4)
    assert math.isclose(v, 0.0, abs_tol=1e-4)


# ── _parse_open_meteo_winds ───────────────────────────────────────────────────


def test_parse_open_meteo_winds_returns_three_tuples() -> None:
    times, u, v = _parse_open_meteo_winds(_WIND_FIXTURE)
    assert len(times) == 3
    assert len(u) == 3
    assert len(v) == 3


def test_parse_open_meteo_winds_times_are_strings() -> None:
    times, _, _ = _parse_open_meteo_winds(_WIND_FIXTURE)
    assert all(isinstance(t, str) for t in times)


# ── fetch_open_meteo_winds ────────────────────────────────────────────────────


def test_fetch_open_meteo_winds_calls_api() -> None:
    session = _make_mock_session(_WIND_FIXTURE)
    data = fetch_open_meteo_winds(_TOBAGO_BBOX, _T0, _T1, session=session)
    assert "hourly" in data
    session.get.assert_called_once()


def test_fetch_open_meteo_winds_uses_centre_lat_lon() -> None:
    session = _make_mock_session(_WIND_FIXTURE)
    fetch_open_meteo_winds(_TOBAGO_BBOX, _T0, _T1, session=session)
    call_kwargs = session.get.call_args
    params = call_kwargs[1]["params"]
    assert params["latitude"] == pytest.approx(11.15, abs=0.01)
    assert params["longitude"] == pytest.approx(-60.75, abs=0.01)


# ── get_forcing — primary path ────────────────────────────────────────────────


def test_get_forcing_returns_forcing_grid() -> None:
    session = _make_mock_session(_WIND_FIXTURE, _CMEMS_FIXTURE)
    grid = get_forcing(_TOBAGO_BBOX, _T0, _T1, session=session)
    assert isinstance(grid, ForcingGrid)


def test_get_forcing_primary_source_label() -> None:
    session = _make_mock_session(_WIND_FIXTURE, _CMEMS_FIXTURE)
    grid = get_forcing(_TOBAGO_BBOX, _T0, _T1, session=session)
    assert grid.source == "cmems+open_meteo"


def test_get_forcing_open_meteo_call_counted() -> None:
    session = _make_mock_session(_WIND_FIXTURE, _CMEMS_FIXTURE)
    grid = get_forcing(_TOBAGO_BBOX, _T0, _T1, session=session)
    assert grid.open_meteo_calls >= 1


def test_get_forcing_cmems_bytes_counted() -> None:
    session = _make_mock_session(_WIND_FIXTURE, _CMEMS_FIXTURE)
    grid = get_forcing(_TOBAGO_BBOX, _T0, _T1, session=session)
    assert grid.cmems_bytes > 0


def test_get_forcing_wind_lengths_match_times() -> None:
    session = _make_mock_session(_WIND_FIXTURE, _CMEMS_FIXTURE)
    grid = get_forcing(_TOBAGO_BBOX, _T0, _T1, session=session)
    assert len(grid.wind_u) == len(grid.times)
    assert len(grid.wind_v) == len(grid.times)


def test_get_forcing_current_lengths_match_times() -> None:
    session = _make_mock_session(_WIND_FIXTURE, _CMEMS_FIXTURE)
    grid = get_forcing(_TOBAGO_BBOX, _T0, _T1, session=session)
    assert len(grid.current_u) == len(grid.times)
    assert len(grid.current_v) == len(grid.times)


# ── fallback: CMEMS unavailable → Open-Meteo marine ──────────────────────────


def test_get_forcing_fallback_when_cmems_down() -> None:
    session = _make_mock_session(_WIND_FIXTURE, cmems_data=None)
    grid = get_forcing(_TOBAGO_BBOX, _T0, _T1, session=session)
    assert isinstance(grid, ForcingGrid)


def test_get_forcing_fallback_source_label() -> None:
    session = _make_mock_session(_WIND_FIXTURE, cmems_data=None)
    grid = get_forcing(_TOBAGO_BBOX, _T0, _T1, session=session)
    assert grid.source == "open_meteo_marine"


def test_get_forcing_fallback_two_open_meteo_calls() -> None:
    session = _make_mock_session(_WIND_FIXTURE, cmems_data=None)
    grid = get_forcing(_TOBAGO_BBOX, _T0, _T1, session=session)
    assert grid.open_meteo_calls == 2


def test_get_forcing_fallback_result_valid() -> None:
    session = _make_mock_session(_WIND_FIXTURE, cmems_data=None)
    grid = get_forcing(_TOBAGO_BBOX, _T0, _T1, session=session)
    assert len(grid.current_u) == len(grid.times)


# ── cache ─────────────────────────────────────────────────────────────────────


def test_cache_miss_returns_none(tmp_path: Path) -> None:
    cache = ForcingCache(tmp_path)
    result = cache.load(_TOBAGO_BBOX, _T0, _T1, "cmems+open_meteo")
    assert result is None


def test_cache_save_and_load(tmp_path: Path) -> None:
    grid = ForcingGrid(
        times=["2024-02-07T00:00", "2024-02-07T01:00"],
        wind_u=[2.0, 2.2],
        wind_v=[-1.0, -1.1],
        current_u=[0.1, 0.12],
        current_v=[-0.05, -0.06],
        source="cmems+open_meteo",
    )
    cache = ForcingCache(tmp_path)
    cache.save(_TOBAGO_BBOX, _T0, _T1, "cmems+open_meteo", grid)
    loaded = cache.load(_TOBAGO_BBOX, _T0, _T1, "cmems+open_meteo")
    assert loaded is not None
    assert loaded.times == grid.times
    assert loaded.wind_u == pytest.approx(grid.wind_u)
    assert loaded.current_u == pytest.approx(grid.current_u)


def test_cache_key_is_deterministic() -> None:
    k1 = _cache_key(_TOBAGO_BBOX, _T0, _T1, "cmems+open_meteo")
    k2 = _cache_key(_TOBAGO_BBOX, _T0, _T1, "cmems+open_meteo")
    assert k1 == k2


def test_cache_different_source_different_key() -> None:
    k1 = _cache_key(_TOBAGO_BBOX, _T0, _T1, "cmems+open_meteo")
    k2 = _cache_key(_TOBAGO_BBOX, _T0, _T1, "open_meteo_marine")
    assert k1 != k2


def test_cache_hit_makes_zero_http_calls(tmp_path: Path) -> None:
    """Second call with same params reads from parquet, makes zero HTTP calls."""
    grid = ForcingGrid(
        times=["2024-02-07T00:00"],
        wind_u=[2.0],
        wind_v=[-1.0],
        current_u=[0.1],
        current_v=[-0.05],
        source="cmems+open_meteo",
    )
    cache = ForcingCache(tmp_path)
    cache.save(_TOBAGO_BBOX, _T0, _T1, "cmems+open_meteo", grid)

    session = _make_mock_session(_WIND_FIXTURE, _CMEMS_FIXTURE)
    loaded = get_forcing(_TOBAGO_BBOX, _T0, _T1, cache=cache, session=session)
    assert loaded is not None
    session.get.assert_not_called()


# ── parquet fixture sanity check ──────────────────────────────────────────────


def test_cmems_parquet_fixture_readable() -> None:
    import pyarrow.parquet as pq

    table = pq.read_table(_REPO_ROOT / "tests" / "fixtures" / "cmems_currents_tobago.parquet")
    assert "time" in table.column_names
    assert "current_u" in table.column_names
    assert table.num_rows == 3
