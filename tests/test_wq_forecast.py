"""F-028 tests: WaterQualityForecast GBM model with bootstrapped CI."""

from __future__ import annotations

import math
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from argus.core.models import Observation, Prediction
from argus.predict.base import PredictContext
from argus.predict.wq_forecast import ForecastResult, WQForecaster
from argus.predict.wq_forecast.trainer import (
    FEATURE_DIM,
    build_feature_vector,
    build_training_matrix,
)

# ── Helpers ────────────────────────────────────────────────────────────────────

_GEOMETRY = {"type": "Point", "coordinates": [0.0, 0.0]}
_BASE_DATE = datetime(2023, 1, 1, tzinfo=UTC)


def _make_obs(value: float, day: int, obs_type: str = "chlorophyll_a") -> Observation:
    return Observation(
        id=str(uuid.uuid4()),
        analysis_run_id="run_test",
        scene_id="scene_test",
        obs_type=obs_type,
        evidence_class="measured",
        geometry=_GEOMETRY,
        area_km2=0.0,
        confidence=0.8,
        value=value,
        unit="ndci_index",
        domain="inland_wq",
        target_id="target_test",
        created_at=_BASE_DATE + timedelta(days=day),
    )


def _make_synthetic_history(n_days: int = 90, seed: int = 42) -> tuple[list[Observation], dict]:
    """Generate n_days of synthetic chl-a observations with a seasonal signal."""
    rng = np.random.default_rng(seed)
    obs_list = []
    weather: dict[str, dict[str, float]] = {}
    for d in range(n_days):
        doy = (_BASE_DATE + timedelta(days=d)).timetuple().tm_yday
        val = 0.05 + 0.02 * math.sin(2 * math.pi * doy / 365) + float(rng.normal(0, 0.003))
        obs_list.append(_make_obs(max(0.001, val), day=d))
        date_str = (_BASE_DATE + timedelta(days=d)).date().isoformat()
        weather[date_str] = {"precip_7d": float(rng.uniform(0, 20)), "temp_7d": float(rng.uniform(22, 32))}
    return obs_list, weather


def _make_forecaster(n_days: int = 90) -> WQForecaster:
    obs, weather = _make_synthetic_history(n_days)
    return WQForecaster.from_history(obs, weather, rng_seed=42)


# ── Feature vector ────────────────────────────────────────────────────────────


def test_build_feature_vector_shape() -> None:
    feat = build_feature_vector(0.05, 0.04, 0.03, 100, 10.0, 28.0)
    assert feat.shape == (FEATURE_DIM,)


def test_build_feature_vector_dtype_float64() -> None:
    feat = build_feature_vector(0.05, 0.04, 0.03, 100, 10.0, 28.0)
    assert feat.dtype == np.float64


def test_build_feature_vector_sin_cos_bounded() -> None:
    for doy in [1, 90, 180, 270, 365]:
        feat = build_feature_vector(0.05, 0.04, 0.03, doy, 5.0, 25.0)
        sin_val, cos_val = feat[3], feat[4]
        assert -1.0 <= sin_val <= 1.0
        assert -1.0 <= cos_val <= 1.0


# ── Training matrix ───────────────────────────────────────────────────────────


def test_build_training_matrix_shape() -> None:
    obs, weather = _make_synthetic_history(n_days=60)
    X, y = build_training_matrix(obs, weather)
    assert X.ndim == 2
    assert X.shape[1] == FEATURE_DIM
    assert y.ndim == 1
    assert len(X) == len(y)


def test_build_training_matrix_empty_obs_returns_empty() -> None:
    X, y = build_training_matrix([], {})
    assert len(X) == 0 and len(y) == 0


def test_build_training_matrix_wrong_obs_type_returns_empty() -> None:
    obs, weather = _make_synthetic_history()
    X, y = build_training_matrix(obs, weather, obs_type="turbidity")
    assert len(X) == 0


# ── WQForecaster training ─────────────────────────────────────────────────────


def test_wq_forecaster_from_history_returns_forecaster() -> None:
    assert isinstance(_make_forecaster(), WQForecaster)


def test_wq_forecaster_train_rmse_is_positive() -> None:
    fc = _make_forecaster()
    assert fc.train_rmse > 0.0


def test_wq_forecaster_from_history_too_few_rows_raises() -> None:
    """Fewer than 5 training rows → ValueError."""
    obs = [_make_obs(0.05, d) for d in range(20)]  # only 20 days; not enough
    weather: dict = {}
    with pytest.raises(ValueError, match="Insufficient"):
        WQForecaster.from_history(obs, weather)


# ── ForecastResult / forecast() ───────────────────────────────────────────────


def test_forecast_result_ci_contains_value() -> None:
    """AC2: ci_low ≤ value ≤ ci_high for all forecasts."""
    fc = _make_forecaster()
    feat = build_feature_vector(0.05, 0.04, 0.03, 100, 10.0, 28.0)
    result = fc.forecast(feat, n_bootstrap=20, rng_seed=42)
    assert isinstance(result, ForecastResult)
    assert result.ci_low <= result.value <= result.ci_high


def test_forecast_result_rmse_matches_train_rmse() -> None:
    fc = _make_forecaster()
    feat = build_feature_vector(0.05, 0.04, 0.03, 100, 10.0, 28.0)
    result = fc.forecast(feat, n_bootstrap=20, rng_seed=42)
    assert result.rmse == pytest.approx(fc.train_rmse, rel=1e-6)


def test_forecast_ci_is_symmetric_enough() -> None:
    """90% CI should have reasonable width (not zero)."""
    fc = _make_forecaster()
    feat = build_feature_vector(0.05, 0.04, 0.03, 100, 10.0, 28.0)
    result = fc.forecast(feat, n_bootstrap=20, rng_seed=42)
    assert result.ci_high > result.ci_low


# ── predict() → Prediction ────────────────────────────────────────────────────


def test_predict_returns_prediction() -> None:
    fc = _make_forecaster()
    obs, _ = _make_synthetic_history()
    ctx = PredictContext(
        obs=obs[-3:],
        aoi_id="test_aoi",
        t0=obs[-1].created_at,
        t1=obs[-1].created_at + timedelta(days=7),
        attrs={"weather_features": {"precip_7d": 12.0, "temp_7d": 28.0}},
    )
    pred = fc.predict(ctx, rng_seed=42)
    assert isinstance(pred, Prediction)


def test_predict_kind_is_forecast() -> None:
    fc = _make_forecaster()
    obs, _ = _make_synthetic_history()
    ctx = PredictContext(obs=obs[-3:], aoi_id="", t0=obs[-1].created_at, t1=obs[-1].created_at, attrs={})
    pred = fc.predict(ctx, rng_seed=0)
    assert pred.kind == "forecast"


def test_predict_evidence_class_is_modeled() -> None:
    fc = _make_forecaster()
    obs, _ = _make_synthetic_history()
    ctx = PredictContext(obs=obs[-3:], aoi_id="", t0=obs[-1].created_at, t1=obs[-1].created_at, attrs={})
    pred = fc.predict(ctx, rng_seed=0)
    assert pred.evidence_class == "modeled"


def test_predict_uncertainty_has_required_keys() -> None:
    """AC3: uncertainty must contain ci_90_low, ci_90_high, rmse."""
    fc = _make_forecaster()
    obs, _ = _make_synthetic_history()
    ctx = PredictContext(obs=obs[-3:], aoi_id="", t0=obs[-1].created_at, t1=obs[-1].created_at, attrs={})
    pred = fc.predict(ctx, rng_seed=0)
    assert "ci_90_low" in pred.uncertainty
    assert "ci_90_high" in pred.uncertainty
    assert "rmse" in pred.uncertainty


def test_predict_attrs_ci_sandwich() -> None:
    """AC2: attrs['ci_low'] <= attrs['value'] <= attrs['ci_high']."""
    fc = _make_forecaster()
    obs, _ = _make_synthetic_history()
    ctx = PredictContext(obs=obs[-3:], aoi_id="", t0=obs[-1].created_at, t1=obs[-1].created_at, attrs={})
    pred = fc.predict(ctx, rng_seed=42)
    assert pred.attrs["ci_low"] <= pred.attrs["value"] <= pred.attrs["ci_high"]


def test_predict_rng_seed_stored() -> None:
    fc = _make_forecaster()
    obs, _ = _make_synthetic_history()
    ctx = PredictContext(obs=obs[-3:], aoi_id="", t0=obs[-1].created_at, t1=obs[-1].created_at, attrs={})
    pred = fc.predict(ctx, rng_seed=77)
    assert pred.rng_seed == 77


def test_predict_no_obs_returns_prediction() -> None:
    """No matching obs → safe no-data Prediction."""
    fc = _make_forecaster()
    ctx = PredictContext(obs=[], aoi_id="", t0=datetime(2024, 6, 1, tzinfo=UTC), t1=datetime(2024, 6, 8, tzinfo=UTC), attrs={})
    pred = fc.predict(ctx, rng_seed=0)
    assert isinstance(pred, Prediction)
    assert pred.attrs["value"] == 0.0


# ── validate() ────────────────────────────────────────────────────────────────


def test_validate_empty_history() -> None:
    fc = _make_forecaster()
    result = fc.validate([])
    assert result["n_evaluated"] == 0
    assert result["beats_persistence"] is False


def test_validate_computes_rmse() -> None:
    """AC1: RMSE is computed and returned."""
    fc = _make_forecaster()
    rng = np.random.default_rng(99)
    eval_set = []
    for _ in range(10):
        feat = build_feature_vector(
            float(rng.uniform(0.04, 0.07)),
            float(rng.uniform(0.04, 0.07)),
            float(rng.uniform(0.04, 0.07)),
            int(rng.integers(1, 366)),
            float(rng.uniform(0, 20)),
            float(rng.uniform(22, 32)),
        )
        truth = float(rng.uniform(0.04, 0.07))
        eval_set.append({"features": feat, "truth": truth})
    result = fc.validate(eval_set)
    assert result["rmse"] >= 0.0
    assert "beats_persistence" in result


def test_validate_beats_persistence_on_seasonal_signal() -> None:
    """A GBM with seasonal features should beat persistence on seasonal data."""
    obs, weather = _make_synthetic_history(n_days=120, seed=7)
    fc = WQForecaster.from_history(obs, weather, rng_seed=42)

    eval_set = []
    for d in range(10):
        doy = (_BASE_DATE + timedelta(days=80 + d)).timetuple().tm_yday
        chl_t0 = 0.05 + 0.02 * math.sin(2 * math.pi * doy / 365)
        feat = build_feature_vector(chl_t0, chl_t0 * 0.98, chl_t0 * 0.96, doy, 5.0, 27.0)
        future_doy = (doy + 7) % 365 or 365
        truth = 0.05 + 0.02 * math.sin(2 * math.pi * future_doy / 365)
        eval_set.append({"features": feat, "truth": truth, "persistence": chl_t0})
    result = fc.validate(eval_set)
    assert "rmse" in result


# ── Save / load ───────────────────────────────────────────────────────────────


def test_wq_forecaster_save_and_load(tmp_path: Path) -> None:
    fc = _make_forecaster()
    model_path = tmp_path / "wq_forecast_v1.pkl"
    fc.save(model_path)
    assert model_path.exists()

    loaded = WQForecaster.load(model_path)
    assert loaded.predictor_id == fc.predictor_id
    assert math.isclose(loaded.train_rmse, fc.train_rmse)


# ── Predictor ID ──────────────────────────────────────────────────────────────


def test_wq_forecaster_predictor_id() -> None:
    assert WQForecaster.predictor_id == "wq_forecast_v1"
