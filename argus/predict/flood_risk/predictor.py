"""FloodRisk predictor — rule-based flood risk at DEM-derived choke points.

Method:
  1. Extract peak precipitation and peak river discharge from ctx.obs.
  2. Retrieve ChokePoint(s) from ctx.attrs["choke_points"] (list[ChokePoint]).
  3. Compute a normalised risk score combining precip + discharge + constriction.
  4. Map score to risk_level ∈ {low, medium, high, extreme}.
  5. Return a single Prediction capturing the worst-case risk scenario.

INV-3: evidence_class is always "modeled".
INV-9: uncertainty field is always populated.
Honesty: attrs["label"] explicitly states this is modeled risk, not measured.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from argus.core.models import Observation, Prediction
from argus.predict.base import EvalSet, PredictContext


class FloodRiskPredictor:
    """Rule-based flood risk predictor implementing the Predictor protocol."""

    predictor_id: str = "FloodRisk"

    def predict(self, ctx: PredictContext, rng_seed: int) -> Prediction:
        """Compute flood risk for the AOI based on weather series + choke points.

        Args:
            ctx: PredictContext with:
                obs: list of Observations (precip_series, discharge_series)
                attrs["choke_points"]: list[ChokePoint] for the AOI
                attrs["flood_risk_thresholds"]: optional dict overriding defaults
            rng_seed: Required for INV-8 reproducibility (rule-based, so unused
                      in computation but recorded in the output).

        Returns:
            Prediction(kind="risk", evidence_class="modeled") with:
                attrs["risk_level"]: "low"|"medium"|"high"|"extreme"
                attrs["label"]: honesty label
                uncertainty: discharge percentile + model type + risk score
        """
        thresholds = _merge_thresholds(ctx.attrs.get("flood_risk_thresholds", {}))

        peak_precip = _peak_from_obs(ctx.obs, "precip_series")
        peak_discharge = _peak_from_obs(ctx.obs, "discharge_series")

        choke_points: list[Any] = list(ctx.attrs.get("choke_points", []))
        max_constriction = (
            max(cp.constriction_score for cp in choke_points) if choke_points else 0.0
        )
        n_choke_points = len(choke_points)

        risk_score = _compute_risk_score(
            peak_precip=peak_precip,
            peak_discharge=peak_discharge,
            max_constriction=max_constriction,
            thresholds=thresholds,
        )
        risk_level = _score_to_level(risk_score, thresholds)

        source_obs_ids = [o.id for o in ctx.obs if o.obs_type in {"precip_series", "discharge_series"}]

        return Prediction(
            id=str(uuid.uuid4()),
            predictor_id=self.predictor_id,
            source_obs_ids=source_obs_ids,
            kind="risk",
            evidence_class="modeled",
            uncertainty={
                "model_type": "rule_based",
                "risk_score": round(risk_score, 4),
                "thresholds": {
                    "medium": thresholds["score_medium"],
                    "high": thresholds["score_high"],
                    "extreme": thresholds["score_extreme"],
                },
                "discharge_percentile": 50.0,
            },
            rng_seed=rng_seed,
            created_at=datetime.now(UTC),
            attrs={
                "risk_level": risk_level,
                "label": "modeled flood risk at choke point (not a measured flood)",
                "peak_precip_mm": round(peak_precip, 2) if peak_precip is not None else None,
                "peak_discharge_m3s": round(peak_discharge, 2) if peak_discharge is not None else None,
                "choke_point_count": n_choke_points,
                "max_constriction_score": round(max_constriction, 4),
                "aoi_id": ctx.aoi_id,
                "valid_at": ctx.t1.isoformat(),
            },
        )

    def validate(self, history: EvalSet) -> dict[str, Any]:
        """Score predictor against historical storm → inundation observations.

        history: list of {"precip_mm": float, "discharge_m3s": float,
                           "inundation_observed": bool}

        Returns: hit_rate (fraction of observed inundations with risk ≥ "high")
                 and false_alarm_rate (fraction of non-events predicted high+).
        """
        if not history:
            return {"hit_rate": None, "false_alarm_rate": None, "n_samples": 0}

        thresholds: dict[str, Any] = {}
        hits = 0
        false_alarms = 0
        n_events = 0
        n_non_events = 0

        for record in history:
            precip = float(record.get("precip_mm", 0.0))
            discharge = float(record.get("discharge_m3s", 0.0))
            observed = bool(record.get("inundation_observed", False))

            score = _compute_risk_score(
                peak_precip=precip,
                peak_discharge=discharge,
                max_constriction=float(record.get("constriction_score", 0.5)),
                thresholds=_merge_thresholds(thresholds),
            )
            level = _score_to_level(score, _merge_thresholds(thresholds))
            predicted_high = level in ("high", "extreme")

            if observed:
                n_events += 1
                if predicted_high:
                    hits += 1
            else:
                n_non_events += 1
                if predicted_high:
                    false_alarms += 1

        return {
            "hit_rate": hits / n_events if n_events else None,
            "false_alarm_rate": false_alarms / n_non_events if n_non_events else None,
            "n_samples": len(history),
            "n_events": n_events,
        }


# ── Helpers ───────────────────────────────────────────────────────────────────

_DEFAULT_THRESHOLDS: dict[str, float] = {
    "precip_high_mm": 100.0,
    "precip_extreme_mm": 200.0,
    "discharge_high_m3s": 500.0,
    "discharge_extreme_m3s": 2000.0,
    "score_medium": 0.25,
    "score_high": 0.50,
    "score_extreme": 0.75,
}


def _merge_thresholds(overrides: dict[str, Any]) -> dict[str, float]:
    """Merge override thresholds on top of defaults."""
    merged = dict(_DEFAULT_THRESHOLDS)
    for k, v in overrides.items():
        if k in merged:
            merged[k] = float(v)
    return merged


def _peak_from_obs(obs: list[Observation], obs_type: str) -> float | None:
    """Return the maximum value from all Observations of the given obs_type."""
    values = [o.value for o in obs if o.obs_type == obs_type and o.value is not None]
    return max(values) if values else None


def _compute_risk_score(
    *,
    peak_precip: float | None,
    peak_discharge: float | None,
    max_constriction: float,
    thresholds: dict[str, float],
) -> float:
    """Compute a normalised risk score in [0, 1].

    Components:
      precip_score      = clamp(peak_precip / precip_extreme_mm)
      discharge_score   = clamp(peak_discharge / discharge_extreme_m3s)
      constriction_factor = max_constriction (already in [0,1])

    Weights: precip 0.5, discharge 0.3, constriction 0.2.
    """
    def clamp(v: float) -> float:
        return max(0.0, min(1.0, v))

    precip_score = (
        clamp((peak_precip or 0.0) / thresholds["precip_extreme_mm"])
    )
    discharge_score = (
        clamp((peak_discharge or 0.0) / thresholds["discharge_extreme_m3s"])
    )
    return 0.5 * precip_score + 0.3 * discharge_score + 0.2 * max_constriction


def _score_to_level(score: float, thresholds: dict[str, float]) -> str:
    if score >= thresholds["score_extreme"]:
        return "extreme"
    if score >= thresholds["score_high"]:
        return "high"
    if score >= thresholds["score_medium"]:
        return "medium"
    return "low"
