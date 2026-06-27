"""Predictor protocol scaffold (frozen at F-029).

Do not add methods or change signatures without an ADR.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from argus.core.models import Observation, Prediction

# Labeled eval records: list of {id, truth, prediction, ...}
EvalSet = list[dict[str, Any]]


@dataclass
class PredictContext:
    """Input context for a Predictor.predict() call."""

    obs: list[Observation]
    aoi_id: str
    t0: datetime
    t1: datetime
    attrs: dict[str, Any] = field(default_factory=dict)


class Predictor(Protocol):
    """Stable protocol for all Tier-A predictors. Frozen at F-029; do not extend here."""

    predictor_id: str

    def predict(self, ctx: PredictContext, rng_seed: int) -> Prediction: ...

    def validate(self, history: EvalSet) -> dict[str, Any]: ...
