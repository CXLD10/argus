"""Inland water quality anomaly detector — z-score vs. seasonal baseline."""

from __future__ import annotations

import uuid
from typing import Any

from argus.core.models import Observation, Prediction
from argus.predict.anomaly_detector.baseline import SeasonalBaseline, build_baseline
from argus.predict.base import EvalSet, PredictContext

_PREDICTOR_ID = "anomaly_detector_wq"
_DEFAULT_THRESHOLD_SIGMA = 2.5
_DEFAULT_OBS_TYPE = "chlorophyll_a"


class AnomalyDetector:
    """Seasonal-baseline z-score anomaly detector for inland water quality.

    Implements the Predictor protocol (predict + validate). Must be fitted with
    historical Observations via fit() before predict() can be called.
    """

    predictor_id: str = _PREDICTOR_ID

    def __init__(
        self,
        threshold_sigma: float = _DEFAULT_THRESHOLD_SIGMA,
        obs_type: str = _DEFAULT_OBS_TYPE,
    ) -> None:
        self.threshold_sigma = threshold_sigma
        self.obs_type = obs_type
        self._baseline: SeasonalBaseline | None = None

    def fit(self, obs: list[Observation]) -> None:
        """Build the seasonal baseline from historical Observations."""
        self._baseline = build_baseline(obs, obs_type=self.obs_type)

    def predict(self, ctx: PredictContext, rng_seed: int) -> Prediction:
        """Compute z-score for the most recent observation against the seasonal baseline.

        Returns Prediction(kind='anomaly') with:
          - uncertainty: {"sigma": z_score}
          - attrs: {"anomaly_detected": bool, "z_score": float, ...}

        Raises RuntimeError if called before fit().
        """
        if self._baseline is None:
            raise RuntimeError(
                "AnomalyDetector.predict() called before fit(). "
                "Call fit(historical_obs) first."
            )

        matching = [
            o for o in ctx.obs if o.obs_type == self.obs_type and o.value is not None
        ]

        if not matching:
            return Prediction(
                id=str(uuid.uuid4()),
                predictor_id=self.predictor_id,
                source_obs_ids=[],
                kind="anomaly",
                evidence_class="modeled",
                uncertainty={"sigma": 0.0},
                rng_seed=rng_seed,
                attrs={
                    "anomaly_detected": False,
                    "z_score": 0.0,
                    "reason": "no_matching_observations",
                    "threshold_sigma": self.threshold_sigma,
                    "obs_type": self.obs_type,
                },
            )

        obs = max(matching, key=lambda o: o.created_at)
        week = obs.created_at.isocalendar().week
        mean, std = self._baseline.mean_std(week)

        if mean is None or std is None or std == 0.0:
            z_score = 0.0
            anomaly_detected = False
            reason = "insufficient_baseline"
        else:
            z_score = (obs.value - mean) / std  # type: ignore[operator]
            anomaly_detected = abs(z_score) > self.threshold_sigma
            reason = "anomaly" if anomaly_detected else "normal"

        return Prediction(
            id=str(uuid.uuid4()),
            predictor_id=self.predictor_id,
            source_obs_ids=[obs.id],
            kind="anomaly",
            evidence_class="modeled",
            uncertainty={"sigma": round(z_score, 4)},
            rng_seed=rng_seed,
            attrs={
                "anomaly_detected": anomaly_detected,
                "z_score": round(z_score, 4),
                "reason": reason,
                "threshold_sigma": self.threshold_sigma,
                "obs_type": self.obs_type,
                "iso_week": week,
                "baseline_mean": round(mean, 6) if mean is not None else None,
                "baseline_std": round(std, 6) if std is not None else None,
            },
        )

    def validate(self, history: EvalSet) -> dict[str, Any]:
        """Compute false alarm rate on labeled history.

        history: list of {"obs": Observation, "truth_anomaly": bool}
        Returns: {"false_alarm_rate": float, "passed_gate": bool, "n_evaluated": int}
        """
        if not history:
            return {"false_alarm_rate": 0.0, "passed_gate": False, "n_evaluated": 0}

        false_alarms = 0
        total_normals = 0

        for record in history:
            obs: Observation = record["obs"]
            truth_anomaly: bool = record["truth_anomaly"]
            ctx = PredictContext(
                obs=[obs],
                aoi_id="",
                t0=obs.created_at,
                t1=obs.created_at,
                attrs={},
            )
            pred = self.predict(ctx, rng_seed=0)
            predicted_anomaly: bool = pred.attrs.get("anomaly_detected", False)

            if not truth_anomaly:
                total_normals += 1
                if predicted_anomaly:
                    false_alarms += 1

        false_alarm_rate = false_alarms / total_normals if total_normals > 0 else 0.0
        return {
            "false_alarm_rate": round(false_alarm_rate, 4),
            "passed_gate": false_alarm_rate < 0.10,
            "n_evaluated": len(history),
        }
