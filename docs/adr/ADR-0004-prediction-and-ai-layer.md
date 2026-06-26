# ADR-0004 — Prediction engine and AI layer

- **Status:** Accepted
- **Date:** 2026-06-26
- **Deciders:** Josh
- **Related:** [ADR-0003](ADR-0003-water-health-platform-and-domains.md) · [ADR-0002](ADR-0002-data-and-simulation-stack.md) · [ARCHITECTURE.md](../architecture/ARCHITECTURE.md)

## Context

The platform needs a "prediction engine" and "AI features." Those phrases cover two very
different things, and conflating them is how AI products lose credibility. This ADR separates
them, defines each, and binds the AI layer with guardrails so it can never fabricate
environmental facts.

## Decisions

### D1 — Two distinct layers

**Tier A — Prediction engine (numerical/ML).** Turns observation time series + weather
drivers into forecasts and risk, with uncertainty. A `Predictor` interface; multiple
implementations:

| Predictor | Inputs | Output | Method |
| --- | --- | --- | --- |
| `OilTrajectory` | oil detection + metocean forcing | drift footprint per timestep | OpenOil (ADR-0002), isolated process |
| `WaterQualityForecast` | per-water-body index history + weather (temp, precip) | n-day chlorophyll-a / turbidity / **bloom-risk** forecast + CI | gradient-boosted trees or temporal model; CPU-trainable |
| `FloodRisk` | Open-Meteo precip forecast + GloFAS discharge + DEM choke points | near-term overflow/inundation **risk** at choke points | rules + discharge thresholds + (optional) learned model |
| `AcidDepositionRisk` | SO₂/NO₂ (Sentinel-5P / Open-Meteo) × precip forecast | acid-deposition **risk index** (modeled, not measured) | physically-motivated index |
| `AnomalyDetector` | per-water-body seasonal baseline of indices | statistically significant departures (early pollution/discharge warning) | unsupervised/statistical (z-score vs. climatology, STL residuals) |

Rules for Tier A:
- Every output carries **uncertainty** (interval/probability) and a **provenance** chain to
  the observations and forcing it used.
- Every model is **validated against history** with a reported skill metric before it is
  trusted in the UI (see PRD success metrics).
- Risk indices (flood, acid) are labeled **modeled risk**, never measurements.
- Stochastic models use a **fixed RNG seed** for reproducibility (NFR-3).
- Training/inference must run **free on CPU** (zero-budget). Heavy deep models are deferred.

**Tier B — AI layer (LLM / generative).** Uses Claude via the Anthropic API to make the
platform's structured outputs usable by busy non-specialists. Features:

| Feature | What it does | Grounding |
| --- | --- | --- |
| **NL situation reports** | Draft a plain-language status/incident report from detections + forecasts + impact for a water body or district | Reads only structured records; every sentence traces to a record id |
| **NL query** | "Which water bodies in my district have rising algae this month?" → structured query → grounded answer | Translates to a store query; answers only from returned rows, with citations |
| **Anomaly explanation / triage** | Given an anomaly + context (weather, upstream, recent events), draft a candidate explanation + recommended action | Advisory only; human-in-the-loop; labels confidence |
| **Alert summarization** | Rank + summarize the day's alerts for an operator | Operates over alert/impact records |

### D2 — AI guardrails (binding)
1. **No invented measurements or facts.** The LLM may summarize, translate, rank, and explain
   **only** structured records produced by the spine/prediction engine. It never originates an
   environmental value.
2. **Grounded + cited.** Every factual claim in generated text references the record(s) it
   came from (id/provenance). Ungrounded claims are a defect.
3. **Model output is labeled.** Forecasts/risk are presented as predictions with uncertainty,
   never as observations.
4. **Human-in-the-loop for action.** Explanations and recommended actions are advisory; the
   platform never auto-acts on an LLM suggestion.
5. **Outbound messages need explicit config.** AI-drafted reports/alerts are not sent without
   the operator's configured channel + consent (consistent with the alerting policy).
6. **Reproducibility & cost.** API calls are logged; prompts/versions are pinned; usage stays
   within free/educational limits; the platform degrades gracefully (templated reports) if the
   API is unavailable.

### D3 — Separation of concerns
- Tier A lives in `argus.predict.*` behind the `Predictor` interface.
- Tier B lives in `argus.ai.*` behind an `assistant` service; it depends on the store and on
  Tier A outputs, never the reverse. Tiers are independently testable (Tier B tested with
  recorded/mock LLM responses; no live API in the default suite — see TESTING).

## Consequences

**Positive**
- Clear, defensible AI story: a validated numerical prediction engine + a *grounded*
  assistant — not "AI" as decoration.
- Guardrails make the generative layer safe to demo to domain experts: it cannot hallucinate
  a pollutant reading.

**Negative / costs**
- Grounding + citation plumbing is real work. Accepted: it is the credibility moat.
- Validating each predictor against history takes labeled/historical data. Mitigated by
  Open-Meteo ERA5 history + the eval harness.

## Alternatives considered
- **One "AI" blob doing prediction and narration.** Rejected: conflates measurement, modeling,
  and language; un-validatable; the failure mode this ADR exists to prevent.
- **LLM reads raw imagery to "find pollution."** Rejected for MVP: not reliable, not
  grounded, not cheap; detection stays in the deterministic/ML domains.

## Open questions
- **OQ-D:** Which model tier for the LLM features and what monthly call budget? *(default: a
  cost-efficient Claude model; templated fallback when over budget)*
- **OQ-E:** Is the NL-query feature read-only for MVP? *(default: yes — read/query only, no
  write actions)*

## Cost Validation

Tier A (prediction engine): scikit-learn / gradient boosting are open-source; CPU-only training is free; Open-Meteo ERA5 history is free. Tier B (AI layer): Anthropic API usage must stay within free/educational limits; templated fallback when over budget ensures zero mandatory cost. The grounding architecture is software design with zero cost.
