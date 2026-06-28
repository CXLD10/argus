"""Evaluation helpers for the FloodRisk predictor.

Builds EvalSet records from stored Predictions and Observations for
backtesting against historical storm events.
"""

from __future__ import annotations

from typing import Any

from argus.predict.base import EvalSet


def build_eval_set(
    storm_records: list[dict[str, Any]],
) -> EvalSet:
    """Convert raw storm records to the EvalSet format expected by validate().

    Each storm record should have:
      precip_mm: float  — 7-day cumulative precipitation
      discharge_m3s: float  — peak river discharge
      inundation_observed: bool  — was inundation confirmed (e.g. by SAR)?
      constriction_score: float (optional, default 0.5)
    """
    return [
        {
            "precip_mm": float(r.get("precip_mm", 0.0)),
            "discharge_m3s": float(r.get("discharge_m3s", 0.0)),
            "inundation_observed": bool(r.get("inundation_observed", False)),
            "constriction_score": float(r.get("constriction_score", 0.5)),
        }
        for r in storm_records
    ]
