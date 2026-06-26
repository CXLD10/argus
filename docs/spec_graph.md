# Argus — Specification Graph

- **Owner:** Architecture Governance
- **Last updated:** 2026-06-27
- **Machine-readable version:** docs/spec_graph.yaml
- **Purpose:** Every specification node and its typed relationships. The navigation layer.

---

## Node Type Legend

| Type | Prefix | Example |
|---|---|---|
| Goal | G | G1 |
| Functional Requirement | FR | FR-1 |
| Non-Functional Requirement | NFR | NFR-1 |
| ADR | ADR | ADR-0003 |
| Domain | D | D1 |
| Predictor | PRED | PRED-OilTraj |
| AI Feature | AI | AI-Report |
| Feature | F | F-000 |
| Phase | PH | PH-0 |
| Module | MOD | MOD-core |
| Data Model | DM | DM-Observation |
| API Endpoint | API | API-detections |
| Standard | STD | STD-TESTING |
| Milestone | MIL | MIL-MVP |
| Open Question | OQ | OQ-B |

## Edge Type Legend

| Edge | Meaning |
|---|---|
| `implements` | Feature/module implements a requirement |
| `depends_on` | A must complete before B |
| `defines` | ADR defines an architecture decision |
| `extends` | A adds capability to B |
| `references` | A references B for context |
| `tests` | A validates B |
| `owns` | Module owns a data model |
| `produces` | A produces B as output |
| `consumes` | A takes B as input |
| `validates` | A validates B meets criteria |
| `supersedes` | A replaces B |
| `resolves` | A resolves an open question |

---

## Goals

```
G1 ─── implements ──▶ FR-1, FR-2, FR-3, FR-4, FR-5, FR-6, FR-7
G2 ─── implements ──▶ FR-8, FR-9, FR-10, FR-11, FR-12
G3 ─── implements ──▶ FR-10
G4 ─── implements ──▶ FR-13, FR-14, FR-15
G5 ─── implements ──▶ FR-16, FR-17, FR-18, FR-19
G6 ─── defines ────▶ NFR-8  (Honesty by design)
G7 ─── defines ────▶ NFR-1  (Zero budget)
```

---

## Requirements → Features

```
FR-1  (AOI/target model)     ──▶ F-001, F-024
FR-2  (search/ingest)        ──▶ F-002, F-003, F-025, F-041
FR-3  (store)                ──▶ F-003, F-005, F-010
FR-4  (D1 oil detect)        ──▶ F-004, F-005, F-007, F-008
FR-5  (D2 inland WQ)         ──▶ F-025, F-026
FR-6  (D3 weather/hydro)     ──▶ F-041
FR-7  (D4 choke points)      ──▶ F-040
FR-8  (oil trajectory)       ──▶ F-011, F-012, F-013
FR-9  (WQ forecast)          ──▶ F-028
FR-10 (anomaly detect)       ──▶ F-027
FR-11 (flood/acid risk)      ──▶ F-042, F-043
FR-12 (uncertainty/gate)     ──▶ F-029
FR-13 (NL reports)           ──▶ F-031
FR-14 (NL query)             ──▶ F-032
FR-15 (anomaly explain)      ──▶ F-033
FR-16 (impact)               ──▶ F-014, F-034, F-042
FR-17 (API)                  ──▶ F-015, F-018
FR-18 (viewer)               ──▶ F-016, F-035, F-044, F-045-F-049
FR-19 (alerts/export)        ──▶ F-006, F-017, F-036, F-051
FR-20 (automation)           ──▶ F-037, F-038, F-039
```

---

## ADRs → Decisions

```
ADR-0001 (vertical + pipeline) ──defines──▶ staged pipeline; event-sourced store
         supersedes ────────────────────▶ (nothing; original)
ADR-0002 (data + simulation)   ──defines──▶ SQLite store; OpenDrift isolation; CDSE access
ADR-0003 (platform + domains)  ──defines──▶ Domain abstraction; D1-D4; honesty boundary
         supersedes ────────────────────▶ ADR-0001 framing
ADR-0004 (prediction + AI)     ──defines──▶ Tier A/B split; grounding guardrails
ADR-0005 (MVP redefinition)    ──defines──▶ Full platform MVP; no vertical-slice milestone
         supersedes ────────────────────▶ PRD §5 v1 two-tier milestone model
ADR-0006 (oil type config)     ──defines──▶ oil_types.yaml registry; no default
         resolves ──────────────────────▶ OQ-F
```

---

## Domains → Modules → Data Models

```
D1 marine_oil
  ├── owns ─▶ argus/domains/marine_oil/
  ├── produces ─▶ DM-Observation (obs_type=oil_slick, evidence_class=measured)
  ├── produces ─▶ DM-AnalysisRun
  └── feeds ─▶ PRED-OilTraj

D2 inland_wq
  ├── owns ─▶ argus/domains/inland_wq/
  ├── produces ─▶ DM-Observation (obs_type=chlorophyll_a|turbidity|cdom|surface_temp)
  └── feeds ─▶ PRED-WQForecast, PRED-Anomaly

D3 weather_hydro
  ├── owns ─▶ argus/domains/weather_hydro/
  ├── produces ─▶ DM-WeatherSeries
  └── feeds ─▶ PRED-FloodRisk, PRED-AcidRisk

D4 hydro_chokepoints
  ├── owns ─▶ argus/domains/hydro_chokepoints/
  ├── produces ─▶ DM-ChokePoint
  └── feeds ─▶ PRED-FloodRisk
```

---

## Predictors → Data Models

```
PRED-OilTraj (OilTrajectory)
  ├── consumes ─▶ DM-Observation(oil_slick), DM-WeatherSeries(wind/current)
  ├── produces ─▶ DM-Prediction(kind=trajectory), DM-ForecastFrame
  └── validates ─▶ DM-SkillReport

PRED-WQForecast (WaterQualityForecast)
  ├── consumes ─▶ DM-Observation(chl-a/turbidity), DM-WeatherSeries(temp/precip)
  ├── produces ─▶ DM-Prediction(kind=forecast)
  └── validates ─▶ DM-SkillReport

PRED-Anomaly (AnomalyDetector)
  ├── consumes ─▶ DM-Observation (time series)
  ├── produces ─▶ DM-Prediction(kind=anomaly)
  └── validates ─▶ DM-SkillReport

PRED-FloodRisk (FloodRisk)
  ├── consumes ─▶ DM-WeatherSeries(precip/discharge), DM-ChokePoint
  ├── produces ─▶ DM-Prediction(kind=risk, evidence_class=modeled)
  └── validates ─▶ DM-SkillReport

PRED-AcidRisk (AcidDepositionRisk)
  ├── consumes ─▶ DM-WeatherSeries(so2/no2/precip)
  ├── produces ─▶ DM-Prediction(kind=risk, evidence_class=modeled, LABELED)
  └── validates ─▶ DM-SkillReport
```

---

## AI Layer

```
AI-Report (NL Situation Reports)
  ├── consumes ─▶ DM-Observation, DM-Prediction, DM-ImpactAssessment
  ├── produces ─▶ DM-AIReport (citations required)
  └── tests ─▶ recorded mock LLM responses

AI-Query (NL Query)
  ├── consumes ─▶ user natural language + store
  ├── produces ─▶ DM-AIQueryLog (citations required)
  └── read-only (OQ-E default)

AI-Explain (Anomaly Explanation)
  ├── consumes ─▶ DM-Prediction(anomaly) + DM-WeatherSeries context
  ├── produces ─▶ advisory text (labeled confidence, human-in-the-loop)
  └── NOT auto-actioned

AI-AlertSummary
  ├── consumes ─▶ DM-Alert
  └── produces ─▶ ranked alert summary text
```

---

## Phase → Feature Dependencies

```
PH-0 (F-000–F-006)
  └── depends_on: nothing (first phase)

PH-1 (F-007–F-010)
  └── depends_on: PH-0

PH-2 (F-011–F-013)
  ├── depends_on: PH-1
  └── requires: ADR-0006 (oil type config); OQ-F resolved ✓

PH-3 (F-014–F-017)
  └── depends_on: PH-2

PH-3.5 (F-018–F-023)
  └── depends_on: PH-3

PH-4 (F-024–F-026)
  ├── depends_on: PH-3.5
  └── requires: OQ-A resolved ✓; OQ-C resolved

PH-5 (F-027–F-029)
  └── depends_on: PH-4

PH-6 (F-030–F-033)
  ├── depends_on: PH-5
  └── requires: OQ-D resolved; OQ-E resolved

PH-7 (F-034–F-036)
  └── depends_on: PH-6

PH-8 (F-037–F-039)
  ├── depends_on: PH-7
  └── requires: ADR-0005-scheduler (not yet written)

PH-9 (F-040–F-044)
  ├── depends_on: PH-8
  └── requires: OQ-B resolved

PH-10 (F-045–F-051)
  └── depends_on: PH-9

PH-11 (F-052–F-056)
  └── depends_on: PH-10
```

---

## MVP

```
MIL-MVP
  ├── requires: PH-11 DONE (all 12 phases complete)
  ├── requires: F-056 (MVP validation + sign-off)
  ├── requires: all 22 validators PASS
  └── defined_by: ADR-0005
```

---

## Open Questions

```
OQ-A ── resolves ──▶ ADR-0005 (full platform MVP; resolved 2026-06-27)
OQ-B ── blocks ────▶ F-040 (choke-point definition); OPEN
OQ-C ── blocks ────▶ F-026 calibration_state (in-situ data); OPEN
OQ-D ── blocks ────▶ F-030 (LLM model tier); OPEN
OQ-E ── blocks ────▶ F-032 (NL-query scope); OPEN (default: read-only)
OQ-F ── resolves ──▶ ADR-0006 (configurable oil types; resolved 2026-06-27)
```
