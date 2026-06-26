# Phase 6 — AI Layer

- **Status:** Specced; waiting for Phase 5; OQ-D and OQ-E must be resolved
- **Priority:** P0
- **Last updated:** 2026-06-27
- **Features:** F-030–F-033
- **Depends on:** Phase 5 complete; OQ-D (LLM tier) resolved; OQ-E (read-only) resolved
- **Related:** [ASSISTANT.md](../ai/ASSISTANT.md) · [ADR-0004](../adr/ADR-0004-prediction-and-ai-layer.md) · [TESTING.md](../standards/TESTING.md) §3.3

**Goal:** Build the grounded AI layer. All LLM interactions are logged, cited, and bounded
by the grounding guard. No live Anthropic API calls in the default test suite.

---

## F-030 — Assistant Scaffolding + Anthropic Client + Grounding Guard

**Why:** The grounding guard is the safety invariant for all AI features. It must be
implemented and tested before any AI features are built on top of it.

**Depends on:** F-029

**Owns / creates:**
- `argus/ai/__init__.py`
- `argus/ai/base.py` (`Assistant` protocol)
- `argus/ai/client.py` (Anthropic API client: pinned model; logged calls; budget tracking)
- `argus/ai/grounding.py` (grounding guard: validates citations; rejects ungrounded claims)
- `argus/ai/fallback.py` (templated report generator when API unavailable or over budget)
- `tests/test_grounding_guard.py`
- `tests/fixtures/ai/grounded_response.json`
- `tests/fixtures/ai/ungrounded_response.json`

**Grounding guard contract:**
```python
class GroundingGuard:
    def validate(self, response: str, citations: list[str], store: Store) -> GroundedText:
        """
        Raises GroundingError if:
        - Any citation id does not exist in the store
        - Any factual sentence (number, measurement, risk label, date) lacks a citation
        """
```

**No live API in default tests.** Use `tests/fixtures/ai/` recorded responses exclusively.

**Acceptance criteria:**
- Grounded response (fixture): passes validation; returns `GroundedText` with citations
- Ungrounded response (fixture with invented value): raises `GroundingError`
- `APIReport.model` field set to pinned model version; never `latest` or unversioned
- Templated fallback triggered when `ARGUS_AI_OFFLINE=true` env var set

---

## F-031 — NL Situation Reports (Grounded, Cited)

**Why:** Plain-language reports for non-specialists; every claim cites a record.

**Depends on:** F-030

**Owns / creates:**
- `argus/ai/reports.py`
- `argus/api/routers/ai.py` (add `GET /waterbody/{id}/report`)
- `tests/test_nl_reports.py` (mock LLM)
- `tests/fixtures/ai/report_wq_grounded.json`

**Context object built from store (not LLM):**
- Most recent Observations (by type, last 30 days)
- AnomalyResults (flagged, last 30 days)
- Forecasts (next 7 days)
- ImpactAssessments

**Prompt structure:** System prompt encodes honesty rules; context is structured JSON;
instruction: "Produce a 3-paragraph situation report. Every factual claim must end with [record_id]."

**Acceptance criteria:**
- Report generated from fixture context → all factual sentences have citations
- Grounding guard validates every citation against store (mocked)
- `AIReport.citations` non-empty; all IDs exist in mocked store

---

## F-032 — NL Query (Text → Store Query → Grounded Answer)

**Why:** Non-specialists need to ask questions in plain language without knowing the data model.

**Depends on:** F-030; OQ-E resolved (default: read-only)

**Owns / creates:**
- `argus/ai/query.py`
- `argus/api/routers/ai.py` (add `POST /query`)
- `tests/test_nl_query.py` (mock LLM)

**Pipeline:**
1. User question → LLM translates to `StoreQuery` (structured: target_id?, time_window?, obs_type?, status?)
2. Execute `StoreQuery` against store
3. LLM synthesizes answer from returned rows only (not from training data)
4. Grounding guard validates citations

**Read-only:** No write actions. If question implies an action ("delete this", "configure that"):
respond "I can only query records; please use the admin panel for configuration."

**Acceptance criteria:**
- "Which water bodies had anomalies last month?" → structured query → mocked rows → cited answer
- Invented fact in answer → `GroundingError`
- Write-action question → polite refusal (no error)

---

## F-033 — Anomaly Explanation + Triage (Advisory)

**Why:** When an anomaly is flagged, operators need a plausible explanation to guide action.

**Depends on:** F-030, F-027

**Owns / creates:**
- `argus/ai/anomaly_explain.py`
- `argus/api/routers/ai.py` (add `GET /anomaly/{id}/explanation`)
- `tests/test_anomaly_explain.py` (mock LLM)

**Context includes:** AnomalyResult details, nearby weather (WeatherSeries), upstream land use
(from MonitorTarget.attrs), recent observations.

**Output:** Advisory text with:
- Candidate explanation (labeled as "hypothesis")
- Recommended sampling actions (labeled as "advisory")
- Confidence label: low/medium/high
- Human-in-the-loop: text is advisory only; never auto-actioned

**Acceptance criteria:**
- Explanation generated from fixture context; contains candidate hypothesis + recommended action
- Confidence label present and in {low, medium, high}
- Explanation stored in `AIReport` with citations; grounding guard passes

## Phase 6 Definition of Done

- [ ] F-030–F-033 acceptance criteria met
- [ ] Grounding guard rejects ungrounded response in test
- [ ] No live Anthropic API calls in `pytest` default run
- [ ] Templated fallback works when `ARGUS_AI_OFFLINE=true`
- [ ] All `AIReport` records have non-empty `citations`
