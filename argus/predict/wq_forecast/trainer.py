"""Feature engineering and GBM training for WaterQualityForecast."""

from __future__ import annotations

import math
from datetime import timedelta

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor

from argus.core.models import Observation

_FEATURE_NAMES = [
    "chl_t0",
    "chl_t_minus_7",
    "chl_t_minus_14",
    "sin_doy",
    "cos_doy",
    "precip_7d",
    "temp_7d",
]
FEATURE_DIM = len(_FEATURE_NAMES)


def build_feature_vector(
    chl_t0: float,
    chl_t_minus_7: float,
    chl_t_minus_14: float,
    doy: int,
    precip_7d: float,
    temp_7d: float,
) -> np.ndarray:
    """Build a (7,) float64 feature vector for one forecast step."""
    angle = 2.0 * math.pi * doy / 365.0
    return np.array(
        [chl_t0, chl_t_minus_7, chl_t_minus_14, math.sin(angle), math.cos(angle), precip_7d, temp_7d],
        dtype=np.float64,
    )


def build_training_matrix(
    obs_history: list[Observation],
    weather_by_date: dict[str, dict[str, float]],
    obs_type: str = "chlorophyll_a",
    horizon_days: int = 7,
) -> tuple[np.ndarray, np.ndarray]:
    """Build (X, y) training arrays from Observation history and weather features.

    weather_by_date: {date_iso (YYYY-MM-DD) → {"precip_7d": float, "temp_7d": float}}
    Only includes rows where all lag values and the t+7 target are available.
    """
    filtered = sorted(
        [o for o in obs_history if o.obs_type == obs_type and o.value is not None],
        key=lambda o: o.created_at,
    )
    if not filtered:
        return np.empty((0, FEATURE_DIM), dtype=np.float64), np.empty(0, dtype=np.float64)

    by_date = {o.created_at.date(): o for o in filtered}

    rows_X: list[np.ndarray] = []
    rows_y: list[float] = []

    for obs in filtered:
        t0 = obs.created_at.date()
        target_date = t0 + timedelta(days=horizon_days)
        lag7_date = t0 - timedelta(days=horizon_days)
        lag14_date = t0 - timedelta(days=horizon_days * 2)

        target_obs = by_date.get(target_date)
        lag7_obs = by_date.get(lag7_date)
        lag14_obs = by_date.get(lag14_date)

        if target_obs is None or lag7_obs is None or lag14_obs is None:
            continue

        weather = weather_by_date.get(t0.isoformat(), {"precip_7d": 0.0, "temp_7d": 25.0})

        feat = build_feature_vector(
            chl_t0=float(obs.value),  # type: ignore[arg-type]
            chl_t_minus_7=float(lag7_obs.value),  # type: ignore[arg-type]
            chl_t_minus_14=float(lag14_obs.value),  # type: ignore[arg-type]
            doy=obs.created_at.timetuple().tm_yday,
            precip_7d=weather["precip_7d"],
            temp_7d=weather["temp_7d"],
        )
        rows_X.append(feat)
        rows_y.append(float(target_obs.value))  # type: ignore[arg-type]

    if not rows_X:
        return np.empty((0, FEATURE_DIM), dtype=np.float64), np.empty(0, dtype=np.float64)

    return np.stack(rows_X, axis=0), np.array(rows_y, dtype=np.float64)


def train_gbm(X: np.ndarray, y: np.ndarray, *, rng_seed: int = 42) -> GradientBoostingRegressor:
    """Train a GradientBoostingRegressor on (X, y)."""
    gbm = GradientBoostingRegressor(
        n_estimators=50,
        max_depth=3,
        learning_rate=0.1,
        random_state=rng_seed,
    )
    gbm.fit(X, y)
    return gbm
