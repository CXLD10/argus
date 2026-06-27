"""NL situation report generator — grounded, cited, 3-paragraph format (F-031).

Context is built from the store (observations + predictions). Every factual
sentence in the LLM response must reference a record id or a GroundingError is
raised. When ARGUS_AI_OFFLINE=true, a deterministic template is used instead.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from argus.ai.base import GroundedText, Scope
from argus.ai.client import ArgusAIClient
from argus.ai.fallback import generate_template_report, is_offline
from argus.ai.grounding import GroundingGuard

if TYPE_CHECKING:
    from argus.core.models import Observation, Prediction
    from argus.core.store import Store

_SYSTEM_PROMPT = (
    "You are the Argus Environmental Intelligence assistant. "
    "Produce a 3-paragraph situation report. Rules:\n"
    "1. Every sentence containing a number, measurement, risk label, or date "
    "must end with [record_id] from the provided context.\n"
    "2. Never invent values — use only data from the context JSON.\n"
    "3. Paragraph 1: current status. Paragraph 2: trends and anomalies. "
    "Paragraph 3: outlook."
)

_LOOKBACK_DAYS = 30


class SituationReporter:
    """Builds a grounded NL situation report for a water body scope."""

    def __init__(
        self,
        client: ArgusAIClient,
        guard: GroundingGuard,
        store: Store,
        *,
        lookback_days: int = _LOOKBACK_DAYS,
    ) -> None:
        self._client = client
        self._guard = guard
        self._store = store
        self._lookback_days = lookback_days

    def report(self, scope: Scope) -> GroundedText:
        """Generate a grounded 3-paragraph situation report.

        Falls back to a deterministic template when ARGUS_AI_OFFLINE=true or
        when no API key is configured, avoiding any live LLM call.
        """
        obs = self._get_recent_obs(scope)

        if is_offline():
            return generate_template_report(scope, obs)

        preds = self._get_relevant_preds()
        context = self._build_context(scope, obs, preds)
        citation_ids = [o.id for o in obs] + [p.id for p in preds]

        prompt = (
            f"Context (JSON):\n{json.dumps(context, indent=2)}\n\n"
            "Produce a 3-paragraph situation report. "
            "Every factual sentence must end with [record_id]."
        )
        response = self._client.complete(prompt, system=_SYSTEM_PROMPT)
        return self._guard.validate(response, citation_ids, self._store)

    # ── private helpers ────────────────────────────────────────────────────────

    def _get_recent_obs(self, scope: Scope) -> list[Observation]:
        since = datetime.now(UTC) - timedelta(days=self._lookback_days)
        if scope.target_id:
            return self._store.get_observations_by_target(
                scope.target_id,
                since=since,
                obs_types=scope.obs_types or None,
            )
        return []

    def _get_relevant_preds(self) -> list[Prediction]:
        return (
            self._store.get_predictions_by_kind("anomaly")
            + self._store.get_predictions_by_kind("forecast")
        )

    def _build_context(
        self,
        scope: Scope,
        obs: list[Observation],
        preds: list[Prediction],
    ) -> dict[str, Any]:
        return {
            "aoi_id": scope.aoi_id,
            "target_id": scope.target_id,
            "observations": [
                {
                    "id": o.id,
                    "obs_type": o.obs_type,
                    "value": o.value,
                    "unit": o.unit,
                    "evidence_class": o.evidence_class,
                    "created_at": o.created_at.isoformat(),
                }
                for o in obs
            ],
            "predictions": [
                {
                    "id": p.id,
                    "kind": p.kind,
                    "attrs": p.attrs,
                    "created_at": p.created_at.isoformat(),
                }
                for p in preds
            ],
        }
