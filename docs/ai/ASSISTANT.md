# Argus AI Assistant (Tier B)

- **Status:** Specced; Phase 6 implements
- **Last updated:** 2026-06-27
- **Code:** `argus/ai/`
- **Related:** [phase-6.md](../features/phase-6.md) · [ADR-0004](../adr/ADR-0004-prediction-and-ai-layer.md) · [TESTING.md](../standards/TESTING.md) §3.3

---

## Purpose

Turn the platform's structured outputs into plain-language reports and natural-language
answers usable by busy non-specialists (municipal officers, response coordinators, researchers).

The AI assistant reads only from the structured store. It never originates environmental
values. Every factual claim is cited to a record id.

---

## Features

### NL Situation Reports (F-031)

Generate a plain-language situation report for a water body or district.

**Input:** Scope object (target_id, time_window)
**Process:** Build structured context from store (observations, anomalies, forecasts, impact)
→ prompt Claude → validate with grounding guard → return `GroundedText` with citations
**Output:** `AIReport(text_ref, citations, model, scope)`

### NL Query (F-032)

Answer plain-language questions about the platform's records.

**Input:** User question (str), scope (optional)
**Process:** LLM translates to `StoreQuery` → execute → LLM synthesizes answer from rows only
→ grounding guard validates → return `GroundedAnswer` with citations
**Output:** `AIQueryLog(question, resolved_query, answer_ref, citations)`
**Scope:** Read-only (OQ-E default). No write actions via NL.

### Anomaly Explanation (F-033)

Generate a candidate explanation for a flagged anomaly.

**Input:** `AnomalyResult` id + upstream context (weather, land use, recent events)
**Output:** Advisory text with:
- Candidate hypothesis (labeled "hypothesis, not confirmed")
- Suggested actions (labeled "advisory — human review required")
- Confidence: low/medium/high

**Never auto-actioned.** Always advisory.

### Alert Summarization

Rank and summarize the day's alerts for operator review.

**Input:** `Alert[]` records
**Output:** Ranked summary text with links to source records

---

## Guardrails (Binding — ADR-0004 D2)

1. **No invented values.** LLM may summarize, translate, rank, and explain only what is in
   the store. It may never state an environmental measurement that isn't in a record.

2. **Grounded + cited.** Every factual claim references record id(s) in `citations`. The
   grounding guard validates this mechanically, not by style.

3. **Model output is labeled.** All AI-generated text is labeled "AI-generated · Grounded"
   in the UI. The model version is recorded in `AIReport.model`.

4. **Human-in-the-loop for actions.** Explanations and recommended actions are advisory.

5. **Explicit channel consent.** AI-drafted reports are not sent to external channels without
   the operator's configured consent (alert_channels.yaml).

6. **Graceful degradation.** When the Anthropic API is unavailable or over budget:
   the system falls back to templated reports (`argus/ai/fallback.py`). This is not an error;
   it is the designed behavior for cost control.

---

## Grounding Guard

`argus/ai/grounding.py` validates every LLM response before it is stored or returned.

```python
class GroundingGuard:
    def validate(self, response: str, citations: list[str], store: Store) -> GroundedText:
        # 1. Every citation id exists in store
        # 2. Every factual sentence (contains a number, measurement, risk label, or date)
        #    has ≥1 citation in citations list
        # Raises GroundingError if either check fails
```

A `GroundingError` is not surfaced to the end user as a crash — it triggers the templated
fallback with a note: "Full AI report unavailable; templated summary shown."

---

## Testing

**No live Anthropic API calls in the default test suite.** Ever.

All AI tests use recorded responses from `tests/fixtures/ai/`:
- `report_grounded.json` — a valid, fully cited response
- `report_ungrounded.json` — a response with an invented value (for negative testing)
- `query_answer_grounded.json` — a valid NL query answer

Test pattern: `monkeypatch.setattr("argus.ai.client.call_llm", fixture_loader)`

---

## Cost Management

- All calls logged: `AIReport.model`, input/output token counts
- If `ARGUS_AI_OFFLINE=true`: all AI features use templated fallback (zero API cost)
- Model version pinned in `config/settings.yaml: ai.model`; never use unversioned aliases
- OQ-D resolution will set the specific model tier and token budget
