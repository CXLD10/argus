# Argus — Project Dashboard

- **Last updated:** 2026-06-29
- **Status:** Phase 10 COMPLETE — Phase 11 (System Validation & MVP Sign-off) IN PROGRESS
- **Owner:** Josh
- **Governed by:** CLAUDE.md, docs/governance/HARNESS.md

---

## Overall Progress

```
Phases 0–10  ████████████████████████████████████████  100%
Phase 11     ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░    0%
MVP (CP-4)   ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░    0%
```

---

## MVP Definition

The MVP is complete only when ALL of the following are done:

- [x] All 4 observation domains operational (D1 oil, D2 inland WQ, D3 weather/hydro, D4 choke)
- [x] All 5 predictors validated (OilTrajectory, WQForecast, AnomalyDetector, FloodRisk, AcidRisk)
- [x] Complete AI layer grounded + tested (NL reports, NL query, anomaly explanation)
- [x] All data integrations functioning (CDSE, Open-Meteo, Copernicus DEM, CMEMS)
- [x] Complete alerting pipeline (webhook + email)
- [x] Every API endpoint documented + tested (21 endpoints)
- [x] Production-quality UI/UX dashboard (12 pages, all domains + AI)
- [ ] Full validation pipeline passing (Phase 11 F-052)
- [ ] End-to-end run < 10 min per AOI on laptop (Phase 11 F-053)
- [ ] Zero recurring cost confirmed (Phase 11 F-056)

---

## Phase Progress

| Phase | Name | Features | Status | Notes |
|---|---|---|---|---|
| 0 | Foundation & Spike (oil) | F-000–F-006 | **DONE** | commit 850b852 |
| 1 | Detection Vertical (oil) | F-007–F-010 | **DONE** | commit 9ea967a–2c1ae8e |
| 2 | Simulation Vertical (oil) | F-011–F-013 | **DONE** | commit 128ffea–b3ac90a |
| 3 | Impact, Delivery & Viewer (oil) | F-014–F-017 | **DONE** | commit 2c851ae–792a3c6 · CP-1 |
| 3.5 | Foundation Hardening | F-018–F-023 | **DONE** | commit 65cdf72–3c93c03 |
| 4 | Domain D2 Inland WQ | F-024–F-026 | **DONE** | commit 03c0edb–f119a9e |
| 5 | Prediction Engine: WQ | F-027–F-029 | **DONE** | commit b6399f6–422e0a9 |
| 6 | AI Layer | F-030–F-033 | **DONE** | commit cae538e–85e75b1 |
| 7 | Platform Integration | F-034–F-036 | **DONE** | commit a4c4351 · CP-2 |
| 8 | Automation & Scheduling | F-037–F-039 | **DONE** | commit 70fa768–a23ece5 |
| 9 | Domains D3 & D4 | F-040–F-044 | **DONE** | commit e5c113a–37d941f · CP-3 |
| 10 | Production UI/UX Dashboard | F-045–F-051 | **DONE** | commit 6d258b7, 295bf27 |
| 11 | System Integration & Validation | F-052–F-056 | **TODO** | CP-4 = MVP |

---

## Architecture Health

| Check | Status | Notes |
|---|---|---|
| Domain protocol stable | **DONE** | `argus/domains/base.py` — search/acquire/analyze |
| Predictor protocol stable | **DONE** | `argus/predict/base.py` — predict/validate |
| Assistant protocol stable | **DONE** | `argus/ai/base.py` — report/answer |
| Store accessor pattern | **DONE** | `argus/core/store.py` — all DB access through store |
| AI grounding guard | **DONE** | `argus/ai/grounding.py` — GroundingGuard enforced |
| evidence_class on all Observations | **DONE** | INV-3 enforced at schema level + tests |
| evidence_class on all Predictions | **DONE** | Always "modeled" for all predictors |
| Copyleft isolation (OpenDrift) | **DONE** | subprocess in sim_worker.py only |
| Oil type configurability | **DONE** | config/oil_types.yaml registry (ADR-0006) |
| Uncertainty on all Predictions | **DONE** | INV-9 enforced, skill gate checks it |
| Skill gate enforced | **DONE** | `/waterbody/{id}/forecasts` gate-filters UI predictions |
| No live network in CI | **DONE** | `@pytest.mark.live` excluded from default run |
| Reproducibility | **DONE** | Fixed RNG seeds in all stochastic models |
| Scale-to-zero design | **DONE** | GCP Cloud Run target (ADR-0008) |

---

## Documentation Health

| Document | Status | Notes |
|---|---|---|
| README.md | **CURRENT** | Updated 2026-06-29; reflects Phase 10 complete |
| ROADMAP.md | **CURRENT** | Updated 2026-06-29; all phases marked DONE/CURRENT |
| FRONTEND_BLUEPRINT.md | **CURRENT** | v2.0; implementation record |
| docs/product/PRD.md | **CURRENT** | v2.1 |
| docs/architecture/ARCHITECTURE.md | **CURRENT** | v2.1 + Phase 10 section |
| docs/architecture/DATA_MODELS.md | **CURRENT** | v2.1 |
| docs/architecture/STACK.md | **CURRENT** | |
| docs/api/API_SPEC.md | **CURRENT** | Updated 2026-06-29; all 21 endpoints |
| docs/adr/ADR-0001 through ADR-0008 | **CURRENT** | All accepted/resolved |
| docs/domains/D1–D4 | **CURRENT** | All 4 domains |
| docs/prediction/*.md | **CURRENT** | All 5 predictors |
| docs/ai/ASSISTANT.md | **CURRENT** | |
| docs/standards/TESTING.md | **CURRENT** | |
| docs/standards/CODING.md | **CURRENT** | |
| docs/standards/QUOTAS.md | **CURRENT** | |
| docs/governance/VALIDATORS.md | **CURRENT** | 22 validators |
| docs/user_guide/USER_GUIDE.md | **CURRENT** | Created 2026-06-29 |
| docs/PROJECT_WALKTHROUGH.md | **CURRENT** | Created 2026-06-29 |
| docs/DEMO_MODE.md | **CURRENT** | Created 2026-06-29 |
| docs/DEMO_SCRIPT.md | **CURRENT** | Created 2026-06-29 |
| docs/DEVELOPER_ONBOARDING.md | **CURRENT** | Created 2026-06-29 |
| BOARD.md | **CURRENT** | Reconciled 2026-06-29 |

---

## Open Questions

| ID | Question | Status | Blocker for |
|---|---|---|---|
| OQ-A | Demo lead domain | **RESOLVED** → Full platform | — |
| OQ-B | Choke-point definition | **RESOLVED** 2026-06-28 → confirmed | — |
| OQ-C | In-situ calibration data available? | OPEN | Phase 4 calibration (post-MVP) |
| OQ-D | LLM model tier + monthly budget | OPEN (defaults to fallback mode) | Phase 6 / production |
| OQ-E | NL-query read-only for MVP? | **RESOLVED** → Read-only by design | — |
| OQ-F | Oil-type default | **RESOLVED** → No default; configurable | — |

---

## Risk Register

| ID | Risk | Severity | Status |
|---|---|---|---|
| R-01 | Over-claiming unobservable quantities (pH, nutrients) | HIGH | **Mitigated** — INV-3; evidence_class enforced |
| R-02 | AI hallucination of environmental values | HIGH | **Mitigated** — GroundingGuard; all claims cited |
| R-03 | CDSE quota exhaustion (>1GB/day) | HIGH | **Policy in place** — QuotaGuard; bytes tracked |
| R-04 | Open-Meteo call exhaustion (>10k/day) | MEDIUM | **Policy in place** — call counting; caching |
| R-05 | GPL contamination (OpenDrift leaks into spine) | HIGH | **Mitigated** — process isolation in sim_worker.py |
| R-08 | Predictor ships to UI without validation | HIGH | **Mitigated** — skill gate on /forecasts endpoint |
| R-09 | Oil type hardcoded in simulation | MEDIUM | **Mitigated** — oil_types.yaml registry |
| R-11 | DEM/hydrology tool copyleft | MEDIUM | **Resolved** — pysheds MIT license confirmed |

---

## Technical Debt Register

| ID | Debt | Introduced in | Must pay before |
|---|---|---|---|
| TD-02 | SQLite GeoJSON-as-text (no spatial index) | F-003 | Post-MVP (PostgreSQL/PostGIS migration) |
| TD-04 | No in-situ calibration ingestion | Design | When reference data available (OQ-C) |
| TD-05 | Relative-only WQ metrics until OQ-C resolved | Phase 4 | OQ-C resolution |
| TD-07 | fixtures.ts not wired as demo fallback | Phase 10 | F-055 (demo dataset prep) |
| TD-08 | S5P and inundation analyzers are stubs | Phase 9 | Post-MVP or live CDSE access |

---

## Repository Statistics

| Metric | Value |
|---|---|
| Python source files | 91 |
| Frontend source files (TSX/TS) | ~60 |
| Test files | 56 |
| Tests collected | 1072 (2 deselected for --live) |
| Phases complete | 10/11 |
| Features complete | F-000–F-051 (52/57) |
| ADRs published | 8/8 |
| Validators defined | 22 |
| Open questions | 2 open, 4 resolved |
| API endpoints | 21 |
| Frontend pages | 12 |
| Cost compliance | $0 recurring confirmed |
