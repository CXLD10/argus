"""Skill gate — blocks unvalidated predictors from the UI (F-029).

A predictor passes the gate only when its most recent SkillReport has
passed_gate = True.  The API layer calls gate_predictions() to filter
Prediction lists before returning them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from argus.core.models import Prediction

if TYPE_CHECKING:
    from argus.core.store import Store


def check_gate(predictor_id: str, store: Store) -> bool:
    """Return True if the most recent SkillReport for predictor_id has passed_gate=True."""
    reports = store.get_skill_reports_by_predictor(predictor_id)
    if not reports:
        return False
    # Reports are sorted by created_at ascending; last entry is most recent.
    latest = reports[-1]
    return bool(latest.get("passed_gate", False))


def gate_predictions(predictions: list[Prediction], store: Store) -> list[Prediction]:
    """Return only those Predictions whose predictor has passed the skill gate."""
    # Cache check_gate results within this call to avoid repeated DB queries.
    gate_cache: dict[str, bool] = {}

    def _gated(pred: Prediction) -> bool:
        if pred.predictor_id not in gate_cache:
            gate_cache[pred.predictor_id] = check_gate(pred.predictor_id, store)
        return gate_cache[pred.predictor_id]

    return [p for p in predictions if _gated(p)]
