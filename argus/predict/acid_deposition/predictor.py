"""AcidDepositionRisk predictor — physically-motivated acid-deposition risk index.

Formula:
    acid_index = clamp(SO₂_norm × NO₂_norm × precip_norm × sensitivity × 10, 0, 10)

where each norm value is the observed peak divided by a saturation threshold (clamped [0,1]).
When a variable is absent, its norm is 1.0 (neutral — does not suppress risk, does not amplify).

CRITICAL HONESTY RULES (from AcidDepositionRisk.md):
  1. This is NOT a pH measurement.
  2. evidence_class is always "modeled".
  3. The label string must explicitly state the index is modeled risk, not a measurement.
  4. obs_type is never set to anything implying pH or acid measurement.

INV-3: evidence_class="modeled" enforced.
INV-9: uncertainty field always populated.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from argus.core.models import Observation, Prediction
from argus.predict.base import EvalSet, PredictContext

# Saturation thresholds (concentration at which norm component reaches 1.0)
_SO2_SAT_UG_M3: float = 50.0    # μg/m³
_NO2_SAT_UG_M3: float = 100.0   # μg/m³
_PRECIP_SAT_MM: float = 50.0    # mm


class AcidDepositionRiskPredictor:
    """Physically-motivated acid-deposition risk index (0–10 scale).

    Implements the Predictor protocol.
    """

    predictor_id: str = "AcidDepositionRisk"

    def predict(self, ctx: PredictContext, rng_seed: int) -> Prediction:
        """Compute the acid-deposition risk index for the AOI.

        Args:
            ctx: PredictContext with obs (so2_series, no2_series, precip_series)
                 and optional attrs["acid_sensitivity"] (default 1.0).
            rng_seed: Stored for INV-8 reproducibility (formula is deterministic).

        Returns:
            Prediction(kind="risk", evidence_class="modeled") with:
                attrs["acid_risk_index"]: float in [0, 10]
                attrs["label"]: explicit honesty string
                uncertainty: index_range, sources, methodology
        """
        peak_so2 = _peak_from_obs(ctx.obs, "so2_series")
        peak_no2 = _peak_from_obs(ctx.obs, "no2_series")
        peak_precip = _peak_from_obs(ctx.obs, "precip_series")
        sensitivity: float = float(ctx.attrs.get("acid_sensitivity", 1.0))

        acid_index, components = _compute_acid_index(
            peak_so2=peak_so2,
            peak_no2=peak_no2,
            peak_precip=peak_precip,
            catchment_sensitivity=sensitivity,
        )

        source_obs_ids = [
            o.id for o in ctx.obs
            if o.obs_type in {"so2_series", "no2_series", "precip_series"}
        ]

        return Prediction(
            id=str(uuid.uuid4()),
            predictor_id=self.predictor_id,
            source_obs_ids=source_obs_ids,
            kind="risk",
            evidence_class="modeled",
            uncertainty={
                "index_range": [max(0.0, acid_index - 1.5), min(10.0, acid_index + 1.5)],
                "so2_source": _obs_source(ctx.obs, "so2_series"),
                "precip_source": _obs_source(ctx.obs, "precip_series"),
                "methodology": "SO2 × NO2 × precip × catchment sensitivity index",
            },
            rng_seed=rng_seed,
            created_at=datetime.now(UTC),
            attrs={
                "acid_risk_index": round(acid_index, 3),
                "label": (
                    "modeled acid-deposition risk index (0–10 scale) "
                    "— NOT a pH measurement"
                ),
                "evidence_class": "modeled",
                "methodology": "SO2 × NO2 × precip × catchment sensitivity index",
                "peak_so2_ug_m3": round(peak_so2, 3) if peak_so2 is not None else None,
                "peak_no2_ug_m3": round(peak_no2, 3) if peak_no2 is not None else None,
                "peak_precip_mm": round(peak_precip, 3) if peak_precip is not None else None,
                "catchment_sensitivity": sensitivity,
                "components": components,
                "aoi_id": ctx.aoi_id,
            },
        )

    def validate(self, history: EvalSet) -> dict[str, Any]:
        """Compare predicted index against expert-labeled or sensor data.

        history: list of {"so2_ug_m3": float, "precip_mm": float,
                           "expert_index": float}

        Returns mean absolute error between predicted and expert index.
        """
        if not history:
            return {"mae": None, "n_samples": 0, "note": "no calibration data"}

        errors: list[float] = []
        for record in history:
            peak_so2 = float(record.get("so2_ug_m3", 0.0))
            peak_no2 = float(record.get("no2_ug_m3", 0.0)) or None
            peak_precip = float(record.get("precip_mm", 0.0))
            sensitivity = float(record.get("catchment_sensitivity", 1.0))
            expert = float(record.get("expert_index", 0.0))

            predicted, _ = _compute_acid_index(
                peak_so2=peak_so2,
                peak_no2=peak_no2 if peak_no2 else None,
                peak_precip=peak_precip,
                catchment_sensitivity=sensitivity,
            )
            errors.append(abs(predicted - expert))

        return {
            "mae": sum(errors) / len(errors),
            "n_samples": len(history),
            "note": "informational comparison against expert labels or sensor data",
        }


# ── Helpers ───────────────────────────────────────────────────────────────────


def _compute_acid_index(
    *,
    peak_so2: float | None,
    peak_no2: float | None,
    peak_precip: float | None,
    catchment_sensitivity: float,
) -> tuple[float, dict[str, float]]:
    """Return (acid_index, components) tuple.

    components: individual normalised factors for transparency.
    """
    def clamp(v: float) -> float:
        return max(0.0, min(1.0, v))

    so2_norm = clamp((peak_so2 or 0.0) / _SO2_SAT_UG_M3)
    no2_norm = clamp((peak_no2 or 0.0) / _NO2_SAT_UG_M3) if peak_no2 is not None else 1.0
    precip_norm = clamp((peak_precip or 0.0) / _PRECIP_SAT_MM)
    sens_norm = clamp(catchment_sensitivity)

    raw = so2_norm * no2_norm * precip_norm * sens_norm
    acid_index = min(10.0, raw * 10.0)

    components = {
        "so2_norm": round(so2_norm, 4),
        "no2_norm": round(no2_norm, 4),
        "precip_norm": round(precip_norm, 4),
        "sensitivity_norm": round(sens_norm, 4),
    }
    return acid_index, components


def _peak_from_obs(obs: list[Observation], obs_type: str) -> float | None:
    values = [o.value for o in obs if o.obs_type == obs_type and o.value is not None]
    return max(values) if values else None


def _obs_source(obs: list[Observation], obs_type: str) -> str | None:
    for o in obs:
        if o.obs_type == obs_type:
            return o.attrs.get("source")
    return None
