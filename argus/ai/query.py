"""NL query pipeline — question → StoreQuery → grounded answer (F-032).

The pipeline is read-only by design (OQ-E resolved). Write-action questions
("delete", "configure", etc.) are refused before any LLM call. Every factual
sentence in the synthesized answer must cite a record id (INV-4).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, fields
from datetime import UTC, datetime, timedelta
from typing import Any

from argus.ai.base import GroundedAnswer
from argus.ai.client import ArgusAIClient
from argus.ai.fallback import is_offline
from argus.ai.grounding import GroundingGuard
from argus.core.store import Store

# Keywords whose presence signals a write-action question.
_WRITE_KEYWORDS: frozenset[str] = frozenset(
    {"delete", "remove", "configure", "update", "create", "set", "modify", "add", "change"}
)

_REFUSAL_TEXT = (
    "I can only query records; please use the admin panel for configuration."
)

_TRANSLATE_SYSTEM = (
    "Translate the user's question to a JSON StoreQuery object. "
    "Output only valid JSON — no prose, no markdown fences. "
    "Schema: "
    '{"target_id": null, "aoi_id": null, "obs_type": null, "kind": null, '
    '"since_iso": null, "status": null}. '
    "Use null for fields not mentioned. "
    '"kind" must be "anomaly", "forecast", or null. '
    '"obs_type" must be one of: chlorophyll_a, turbidity, cdom, oil_slick, bloom_presence, or null. '
    '"since_iso" should be an ISO-8601 UTC timestamp if a time window is mentioned '
    "(e.g. 'last month' → 30 days ago)."
)

_SYNTHESIZE_SYSTEM = (
    "You are the Argus Environmental Intelligence assistant. "
    "Answer the question using only the provided store records. "
    "Rules: "
    "1. Every sentence with a number, measurement, or risk label must end with [record_id]. "
    "2. Only reference IDs from the provided records. "
    "3. Never invent values from training data."
)


@dataclass
class StoreQuery:
    """Structured query extracted from a natural-language question."""

    target_id: str | None = None
    aoi_id: str | None = None
    obs_type: str | None = None
    kind: str | None = None  # "anomaly" | "forecast" | None
    since_iso: str | None = None
    status: str | None = None


class QueryPipeline:
    """Two-step NL query: question → StoreQuery → answer grounded in store records."""

    def __init__(
        self,
        client: ArgusAIClient,
        guard: GroundingGuard,
        store: Store,
    ) -> None:
        self._client = client
        self._guard = guard
        self._store = store

    def answer(self, question: str) -> GroundedAnswer:
        """Answer a natural-language question from store records.

        Returns a GroundedAnswer with every factual claim cited.
        Returns a polite refusal for write-action questions without any LLM call.
        """
        if self._is_write_action(question):
            return GroundedAnswer(
                answer=_REFUSAL_TEXT,
                citations=[],
                model=self._client.model,
            )

        if is_offline():
            return GroundedAnswer(
                answer="I am currently offline and unable to query records.",
                citations=[],
                model=f"{self._client.model}:template",
            )

        # Step 1: translate question to StoreQuery.
        sq_json = self._client.complete(question, system=_TRANSLATE_SYSTEM)
        store_query = _parse_store_query(sq_json)

        # Execute query.
        rows = self._execute_query(store_query)
        citation_ids = [r.id for r in rows]

        # Step 2: synthesize grounded answer.
        rows_context = json.dumps(_rows_to_context(rows), indent=2)
        prompt = (
            f"Question: {question}\n\n"
            f"Store records:\n{rows_context}\n\n"
            "Answer the question using only these records."
        )
        response = self._client.complete(prompt, system=_SYNTHESIZE_SYSTEM)
        grounded = self._guard.validate(response, citation_ids, self._store)

        return GroundedAnswer(
            answer=grounded.text,
            citations=grounded.citations,
            model=grounded.model,
        )

    # ── private helpers ────────────────────────────────────────────────────────

    def _is_write_action(self, question: str) -> bool:
        words = set(re.findall(r"\w+", question.lower()))
        return bool(words & _WRITE_KEYWORDS)

    def _execute_query(self, sq: StoreQuery) -> list[Any]:
        """Execute StoreQuery against the store; returns Observations or Predictions."""
        results: list[Any] = []

        if sq.kind:
            results.extend(self._store.get_predictions_by_kind(sq.kind))
            return results

        if sq.target_id:
            obs_types = [sq.obs_type] if sq.obs_type else None
            since = _parse_since(sq.since_iso)
            results.extend(
                self._store.get_observations_by_target(
                    sq.target_id, since=since, obs_types=obs_types
                )
            )
        else:
            # Broad query: return anomaly predictions as the default.
            since = _parse_since(sq.since_iso)
            preds = self._store.get_predictions_by_kind("anomaly")
            if since:
                preds = [p for p in preds if p.created_at >= since]
            results.extend(preds)

        return results


# ── module-level helpers ──────────────────────────────────────────────────────


def _parse_store_query(json_text: str) -> StoreQuery:
    """Parse LLM JSON output → StoreQuery, tolerating extra prose around the JSON."""
    match = re.search(r"\{[^{}]*\}", json_text, re.DOTALL)
    if not match:
        return StoreQuery()
    try:
        data = json.loads(match.group())
        valid_keys = {f.name for f in fields(StoreQuery)}
        return StoreQuery(**{k: v for k, v in data.items() if k in valid_keys and v is not None})
    except (json.JSONDecodeError, TypeError):
        return StoreQuery()


def _parse_since(since_iso: str | None) -> datetime | None:
    if since_iso is None:
        return None
    try:
        return datetime.fromisoformat(since_iso)
    except ValueError:
        return datetime.now(UTC) - timedelta(days=30)


def _rows_to_context(rows: list[Any]) -> list[dict[str, Any]]:
    """Convert mixed Observation/Prediction rows to a JSON-serialisable list."""
    out: list[dict[str, Any]] = []
    for r in rows:
        entry: dict[str, Any] = {"id": r.id, "created_at": r.created_at.isoformat()}
        if hasattr(r, "obs_type"):
            entry["obs_type"] = r.obs_type
            entry["value"] = r.value
            entry["evidence_class"] = r.evidence_class
        if hasattr(r, "kind"):
            entry["kind"] = r.kind
            entry["attrs"] = r.attrs
        out.append(entry)
    return out
