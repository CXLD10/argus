"""Anomaly explanation and triage — advisory text, grounded, human-in-the-loop (F-033).

When an anomaly is flagged the operator needs a plausible hypothesis and a
recommended sampling action. All output is explicitly labeled advisory and is
never auto-actioned (INV-4, human-in-the-loop by design).

Output always contains three labeled sections:
    HYPOTHESIS: <candidate explanation, factual claims cite [record_id]>
    ADVISORY:   <recommended sampling actions>
    CONFIDENCE: <low|medium|high>
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from argus.ai.base import AIReport, GroundedText
from argus.ai.client import ArgusAIClient
from argus.ai.fallback import is_offline
from argus.ai.grounding import GroundingGuard

if TYPE_CHECKING:
    from argus.core.models import Observation, Prediction
    from argus.core.store import Store

import uuid
from datetime import UTC, datetime

_VALID_CONFIDENCE: frozenset[str] = frozenset({"low", "medium", "high"})

_SYSTEM_PROMPT = (
    "You are the Argus Environmental Intelligence assistant. "
    "Produce an anomaly explanation in exactly this format:\n"
    "HYPOTHESIS: <one or two sentences explaining the candidate cause. "
    "Every sentence with a number or risk label must end with [record_id].>\n"
    "ADVISORY: <one or two sentences recommending sampling or follow-up actions. "
    "This is advisory only — never an automatic action.>\n"
    "CONFIDENCE: <low|medium|high>\n"
    "Rules: never invent values; only use data from the provided context."
)

_TEMPLATE_HYPOTHESIS = (
    "The anomaly detector flagged an elevated z-score [PREDICTION_ID], "
    "suggesting a statistically significant deviation from the seasonal baseline."
)
_TEMPLATE_ADVISORY = (
    "Collect a water sample from the affected monitoring point and "
    "test for cyanobacteria and nutrient loading. This is advisory only."
)
_TEMPLATE_CONFIDENCE = "low"


@dataclass
class AnomalyExplanation:
    """Advisory explanation for one anomaly prediction."""

    hypothesis: str
    advisory: str
    confidence: str  # "low" | "medium" | "high"
    citations: list[str]
    model: str
    report: AIReport


class AnomalyExplainer:
    """Generates a grounded advisory explanation for an anomaly Prediction."""

    def __init__(
        self,
        client: ArgusAIClient,
        guard: GroundingGuard,
        store: Store,
    ) -> None:
        self._client = client
        self._guard = guard
        self._store = store

    def explain(self, prediction_id: str) -> AnomalyExplanation:
        """Generate a grounded hypothesis and advisory for the given anomaly prediction.

        Falls back to a deterministic template when ARGUS_AI_OFFLINE=true.

        Raises:
            ValueError: if prediction_id is not found in the store.
            GroundingError: if the LLM response contains ungrounded claims.
        """
        pred = self._store.get_prediction(prediction_id)
        if pred is None:
            raise ValueError(
                f"Prediction {prediction_id!r} not found in store. "
                "Check the prediction_id and ensure the anomaly has been saved."
            )

        obs = self._get_source_obs(pred)

        if is_offline():
            return self._template_explanation(pred, obs)

        context = _build_context(pred, obs)
        citation_ids = [prediction_id] + [o.id for o in obs]

        prompt = (
            f"Anomaly context:\n{context}\n\n"
            "Produce a HYPOTHESIS, ADVISORY, and CONFIDENCE label."
        )
        response = self._client.complete(prompt, system=_SYSTEM_PROMPT)
        grounded = self._guard.validate(response, citation_ids, self._store)

        return _parse_explanation(grounded, citation_ids, self._client.model, pred)

    # ── private ────────────────────────────────────────────────────────────────

    def _get_source_obs(self, pred: Prediction) -> list[Observation]:
        obs: list[Observation] = []
        for obs_id in pred.source_obs_ids:
            o = self._store.get_observation(obs_id)
            if o is not None:
                obs.append(o)
        return obs

    def _template_explanation(
        self, pred: Prediction, obs: list[Observation]
    ) -> AnomalyExplanation:
        hyp = _TEMPLATE_HYPOTHESIS.replace("PREDICTION_ID", pred.id)
        report_text = f"{hyp}\n{_TEMPLATE_ADVISORY}\n{_TEMPLATE_CONFIDENCE}"
        report = _make_report(
            text=report_text,
            citations=[pred.id],
            model=f"{self._client.model}:template",
            pred=pred,
        )
        return AnomalyExplanation(
            hypothesis=hyp,
            advisory=_TEMPLATE_ADVISORY,
            confidence=_TEMPLATE_CONFIDENCE,
            citations=[pred.id],
            model=f"{self._client.model}:template",
            report=report,
        )


# ── module-level helpers ──────────────────────────────────────────────────────


def _build_context(pred: Prediction, obs: list[Observation]) -> str:
    lines = [
        f"prediction_id: {pred.id}",
        f"kind: {pred.kind}",
        f"attrs: {pred.attrs}",
        f"created_at: {pred.created_at.isoformat()}",
    ]
    for o in obs:
        lines.append(
            f"observation: id={o.id} obs_type={o.obs_type} "
            f"value={o.value} evidence_class={o.evidence_class}"
        )
    return "\n".join(lines)


def _parse_explanation(
    grounded: GroundedText,
    citation_ids: list[str],
    model: str,
    pred: Prediction,
) -> AnomalyExplanation:
    """Extract HYPOTHESIS / ADVISORY / CONFIDENCE from the grounded LLM response."""
    text = grounded.text

    hyp_match = re.search(r"HYPOTHESIS:\s*(.*?)(?=\nADVISORY:|$)", text, re.DOTALL | re.IGNORECASE)
    adv_match = re.search(r"ADVISORY:\s*(.*?)(?=\nCONFIDENCE:|$)", text, re.DOTALL | re.IGNORECASE)
    conf_match = re.search(r"CONFIDENCE:\s*(\w+)", text, re.IGNORECASE)

    hypothesis = hyp_match.group(1).strip() if hyp_match else text
    advisory = adv_match.group(1).strip() if adv_match else "See full response."
    confidence_raw = conf_match.group(1).strip().lower() if conf_match else "low"
    confidence = confidence_raw if confidence_raw in _VALID_CONFIDENCE else "low"

    report = _make_report(text=text, citations=citation_ids, model=model, pred=pred)
    return AnomalyExplanation(
        hypothesis=hypothesis,
        advisory=advisory,
        confidence=confidence,
        citations=citation_ids,
        model=model,
        report=report,
    )


def _make_report(
    text: str,
    citations: list[str],
    model: str,
    pred: Prediction,
) -> AIReport:
    return AIReport(
        id=str(uuid.uuid4()),
        kind="explanation",
        text=text,
        citations=citations,
        model=model,
        scope_aoi_id=pred.attrs.get("aoi_id", "unknown"),
        scope_target_id=pred.attrs.get("target_id"),
        created_at=datetime.now(UTC),
    )
