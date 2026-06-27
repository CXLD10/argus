"""WaterQualityForecast predictor — GBM model with bootstrapped CI."""

from __future__ import annotations

import math
import pickle
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_squared_error

from argus.core.models import Observation, Prediction
from argus.predict.base import EvalSet, PredictContext
from argus.predict.wq_forecast.trainer import (
    build_feature_vector,
    build_training_matrix,
    train_gbm,
)

_PREDICTOR_ID = "wq_forecast_v1"
_HORIZON_DAYS = 7
_N_BOOTSTRAP = 40


@dataclass
class ForecastResult:
    """Point estimate + 90 % CI for a single forecast step."""

    value: float
    ci_low: float
    ci_high: float
    rmse: float


class WQForecaster:
    """GBM-based water quality forecaster implementing the Predictor protocol.

    Produces Prediction(kind='forecast') with bootstrapped 90 % CI bands.
    Must be constructed via from_history() or load().
    """

    predictor_id: str = _PREDICTOR_ID

    def __init__(
        self,
        gbm: GradientBoostingRegressor,
        X_train: np.ndarray,
        y_train: np.ndarray,
        train_rmse: float,
        obs_type: str = "chlorophyll_a",
    ) -> None:
        self._gbm = gbm
        self._X_train = X_train
        self._y_train = y_train
        self.train_rmse = train_rmse
        self.obs_type = obs_type

    # ── Training ──────────────────────────────────────────────────────────────

    @classmethod
    def from_history(
        cls,
        obs_history: list[Observation],
        weather_by_date: dict[str, dict[str, float]],
        *,
        obs_type: str = "chlorophyll_a",
        rng_seed: int = 42,
        holdout_fraction: float = 0.2,
    ) -> WQForecaster:
        """Train a WQForecaster from Observation history and weather features.

        Holds out the last holdout_fraction of rows for RMSE estimation.
        Raises ValueError if fewer than 5 training rows are available.
        """
        X, y = build_training_matrix(obs_history, weather_by_date, obs_type=obs_type)
        if len(X) < 5:
            raise ValueError(
                f"Insufficient training data: need ≥ 5 rows, got {len(X)}. "
                "Ensure obs_history spans at least 4 weeks with daily observations."
            )

        split = max(1, int(len(X) * (1 - holdout_fraction)))
        X_train, X_val = X[:split], X[split:]
        y_train, y_val = y[:split], y[split:]

        gbm = train_gbm(X_train, y_train, rng_seed=rng_seed)

        if len(X_val) > 0:
            y_pred = gbm.predict(X_val)
            rmse = math.sqrt(float(mean_squared_error(y_val, y_pred)))
        else:
            y_pred_train = gbm.predict(X_train)
            rmse = math.sqrt(float(mean_squared_error(y_train, y_pred_train)))

        return cls(gbm=gbm, X_train=X_train, y_train=y_train, train_rmse=rmse, obs_type=obs_type)

    # ── Forecasting ───────────────────────────────────────────────────────────

    def forecast(
        self,
        features: np.ndarray,
        *,
        n_bootstrap: int = _N_BOOTSTRAP,
        rng_seed: int = 42,
    ) -> ForecastResult:
        """Return point estimate and bootstrapped 90 % CI for one feature vector.

        Uses the bootstrap median as the point estimate so that
        ci_low ≤ value ≤ ci_high is always guaranteed.
        """
        rng = np.random.default_rng(rng_seed)
        n = len(self._X_train)
        boot_preds: list[float] = []

        for _ in range(n_bootstrap):
            idx = rng.choice(n, size=n, replace=True)
            m = GradientBoostingRegressor(
                n_estimators=30, max_depth=3, learning_rate=0.1, random_state=int(rng.integers(0, 2**31))
            )
            m.fit(self._X_train[idx], self._y_train[idx])
            boot_preds.append(float(m.predict(features.reshape(1, -1))[0]))

        value = float(np.median(boot_preds))
        ci_low = float(np.quantile(boot_preds, 0.05))
        ci_high = float(np.quantile(boot_preds, 0.95))
        return ForecastResult(value=value, ci_low=ci_low, ci_high=ci_high, rmse=self.train_rmse)

    # ── Predictor protocol ────────────────────────────────────────────────────

    def predict(self, ctx: PredictContext, rng_seed: int) -> Prediction:
        """Generate a t+7 forecast Prediction from ctx.obs and ctx.attrs.

        ctx.attrs must contain 'weather_features': {"precip_7d": float, "temp_7d": float}.
        ctx.obs must contain at least one Observation of self.obs_type.
        """
        matching = sorted(
            [o for o in ctx.obs if o.obs_type == self.obs_type and o.value is not None],
            key=lambda o: o.created_at,
        )
        if not matching:
            return self._no_data_prediction(ctx, rng_seed)

        obs_t0 = matching[-1]
        obs_t_minus_7 = matching[-2] if len(matching) >= 2 else obs_t0
        obs_t_minus_14 = matching[-3] if len(matching) >= 3 else obs_t_minus_7

        weather: dict[str, float] = ctx.attrs.get("weather_features", {"precip_7d": 0.0, "temp_7d": 25.0})
        doy = obs_t0.created_at.timetuple().tm_yday

        features = build_feature_vector(
            chl_t0=float(obs_t0.value),  # type: ignore[arg-type]
            chl_t_minus_7=float(obs_t_minus_7.value),  # type: ignore[arg-type]
            chl_t_minus_14=float(obs_t_minus_14.value),  # type: ignore[arg-type]
            doy=doy,
            precip_7d=weather.get("precip_7d", 0.0),
            temp_7d=weather.get("temp_7d", 25.0),
        )

        result = self.forecast(features, rng_seed=rng_seed)

        return Prediction(
            id=str(uuid.uuid4()),
            predictor_id=self.predictor_id,
            source_obs_ids=[obs_t0.id],
            kind="forecast",
            evidence_class="modeled",
            uncertainty={
                "ci_90_low": round(result.ci_low, 6),
                "ci_90_high": round(result.ci_high, 6),
                "rmse": round(result.rmse, 6),
            },
            rng_seed=rng_seed,
            attrs={
                "value": round(result.value, 6),
                "ci_low": round(result.ci_low, 6),
                "ci_high": round(result.ci_high, 6),
                "obs_type": self.obs_type,
                "horizon_days": _HORIZON_DAYS,
            },
        )

    def validate(self, history: EvalSet) -> dict[str, Any]:
        """Evaluate RMSE and persistence-baseline comparison on labeled history.

        history: list of {"features": np.ndarray, "truth": float}
        Returns: {"rmse": float, "persistence_rmse": float, "beats_persistence": bool}
        """
        if not history:
            return {"rmse": 0.0, "persistence_rmse": 0.0, "beats_persistence": False, "n_evaluated": 0}

        model_preds, persist_preds, truths = [], [], []
        for record in history:
            feat: np.ndarray = record["features"]
            truth: float = record["truth"]
            persistence: float = record.get("persistence", float(feat[0]))  # chl_t0 as baseline

            model_pred = float(self._gbm.predict(feat.reshape(1, -1))[0])
            model_preds.append(model_pred)
            persist_preds.append(persistence)
            truths.append(truth)

        y_true = np.array(truths)
        rmse = math.sqrt(float(mean_squared_error(y_true, np.array(model_preds))))
        persistence_rmse = math.sqrt(float(mean_squared_error(y_true, np.array(persist_preds))))

        return {
            "rmse": round(rmse, 6),
            "persistence_rmse": round(persistence_rmse, 6),
            "beats_persistence": rmse < persistence_rmse,
            "n_evaluated": len(history),
        }

    # ── Persistence ───────────────────────────────────────────────────────────

    def save(self, path: Path) -> None:
        with open(path, "wb") as fh:
            pickle.dump(self, fh)

    @classmethod
    def load(cls, path: Path) -> WQForecaster:
        with open(path, "rb") as fh:
            obj: WQForecaster = pickle.load(fh)  # noqa: S301
        return obj

    # ── Internal ──────────────────────────────────────────────────────────────

    def _no_data_prediction(self, ctx: PredictContext, rng_seed: int) -> Prediction:
        return Prediction(
            id=str(uuid.uuid4()),
            predictor_id=self.predictor_id,
            source_obs_ids=[],
            kind="forecast",
            evidence_class="modeled",
            uncertainty={"ci_90_low": 0.0, "ci_90_high": 0.0, "rmse": self.train_rmse},
            rng_seed=rng_seed,
            attrs={
                "value": 0.0,
                "ci_low": 0.0,
                "ci_high": 0.0,
                "reason": "no_matching_observations",
                "obs_type": self.obs_type,
                "horizon_days": _HORIZON_DAYS,
            },
        )
