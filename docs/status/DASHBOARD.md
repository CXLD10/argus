# Argus — Project Dashboard

- **Last updated:** 2026-06-27
- **Status:** Pre-implementation (documentation phase)
- **Owner:** Josh
- **Governed by:** CLAUDE.md, docs/governance/HARNESS.md

---

## Overall Progress

```
Pre-implementation ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  20%
Phase 0            ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   0%
MVP Complete       ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   0%
```

The pre-implementation score counts: docs structure, spec completeness, governance.

---

## MVP Definition

The MVP is complete only when ALL of the following are done:

- [ ] All 4 observation domains operational (D1 oil, D2 inland WQ, D3 weather/hydro, D4 choke)
- [ ] All 5 predictors validated (OilTrajectory, WQForecast, AnomalyDetector, FloodRisk, AcidRisk)
- [ ] Complete AI layer grounded + tested (NL reports, NL query, anomaly explanation)
- [ ] All data integrations functioning (CDSE, Open-Meteo, Copernicus DEM, CMEMS)
- [ ] Complete alerting pipeline (webhook + email)
- [ ] Every API endpoint documented + tested
- [ ] Production-quality UI/UX dashboard (all domains + AI)
- [ ] Full validation pipeline passing
- [ ] End-to-end run < 10 min per AOI on laptop
- [ ] Zero recurring cost confirmed

---

## Phase Progress

| Phase | Name | Features | Status | Notes |
|---|---|---|---|---|
| 0 | Foundation & Spike (oil) | F-000–F-006 | TODO | First build task |
| 1 | Detection Vertical (oil) | F-007–F-010 | TODO | Dep Phase 0 |
| 2 | Simulation Vertical (oil) | F-011–F-013 | TODO | Dep Phase 1 + OQ-F resolved ✓ |
| 3 | Impact, Delivery & Viewer (oil) | F-014–F-017 | TODO | Dep Phase 2 |
| 3.5 | Foundation Hardening | F-018–F-023 | TODO | Dep Phase 3 |
| 4 | Domain D2 Inland WQ | F-024–F-026 | TODO | Dep Phase 3.5 + OQ-A resolved ✓ |
| 5 | Prediction Engine: WQ | F-027–F-029 | TODO | Dep Phase 4 |
| 6 | AI Layer | F-030–F-033 | TODO | Dep Phase 5 + OQ-D,E |
| 7 | Platform Integration | F-034–F-036 | TODO | Dep Phase 6 |
| 8 | Automation & Scheduling | F-037–F-039 | TODO | Dep ADR-0005 + Phase 7 |
| 9 | Domains D3 & D4 | F-040–F-044 | TODO | Dep OQ-B + Phase 8 |
| 10 | Production UI/UX Dashboard | F-045–F-051 | TODO | Dep Phase 9 |
| 11 | System Integration & Validation | F-052–F-056 | TODO | Dep Phase 10 |

---

## Architecture Health

| Check | Status | Notes |
|---|---|---|
| Domain protocol stable | PENDING | F-005 will fix it |
| Predictor protocol stable | PENDING | F-029 will fix it |
| Store accessor pattern | PENDING | F-003 establishes it |
| AI grounding guard | PENDING | F-030 establishes it |
| Evidence_class on all Observations | PENDING | F-005 begins enforcement |
| Copyleft isolation (OpenDrift) | PENDING | F-011 implements it |
| Oil type configurability | PENDING | F-011 must implement config registry |

---

## Documentation Health

| Document | Status | Notes |
|---|---|---|
| docs/product/PRD.md | ✓ Current | v2.1; MVP definition updated |
| docs/architecture/ARCHITECTURE.md | ✓ Current | v2.1 (updated from v2.0) |
| docs/architecture/DATA_MODELS.md | ✓ Current | v2.1 (oil_type field + migration table) |
| docs/architecture/STACK.md | ✓ Current | new |
| docs/adr/ADR-0001 | STUB | Reconstructed; original lost |
| docs/adr/ADR-0002 | STUB | Reconstructed; original lost |
| docs/adr/ADR-0003 | ✓ Current | v2.0 |
| docs/adr/ADR-0004 | ✓ Current | v2.0 |
| docs/adr/ADR-0005 | ✓ Current | MVP redefinition |
| docs/adr/ADR-0006 | ✓ Current | Oil type configurability |
| docs/adr/ADR-0007 | DRAFT | Scheduler — needs Josh decision before Phase 8 |
| docs/adr/ADR-0008 | ✓ Accepted | Deployment: Vercel + GCP Cloud Run + GCS |
| docs/features/phase-0.md | ✓ CORRECTED | v2.0 entities fixed |
| docs/features/phase-1.md through 11.md | ✓ Created | Varying detail |
| docs/domains/D1–D4 | ✓ Created | All 4 domains |
| docs/prediction/*.md | ✓ Created | All 5 predictors |
| docs/ai/ASSISTANT.md | ✓ Created | |
| docs/standards/TESTING.md | ✓ Created | |
| docs/standards/CODING.md | ✓ Created | |
| docs/standards/QUOTAS.md | ✓ Created | |
| docs/governance/VALIDATORS.md | ✓ Created | 22 validators |
| docs/governance/HARNESS.md | ✓ Created | |
| docs/spec_graph.md | ✓ Created | |
| docs/spec_graph.yaml | ✓ Created | |
| CLAUDE.md | ✓ Created | Agent operating guide |
| config/oil_types.yaml | ✓ Created | Oil type registry (ADR-0006) |
| config/settings.yaml | ✓ Created | Platform settings template |
| scripts/harness/ | ✓ Scaffolded | Stub scripts; implement in F-019 |
| README.md | ✓ Updated | v2.1 map; retired old MVP terms |
| BOARD.md | ✓ Updated | All 12 phases; correct milestone labels |
| ROADMAP.md | ✓ Updated | v2.1; all phases; internal checkpoints |

---

## Open Questions

| ID | Question | Status | Blocker for |
|---|---|---|---|
| OQ-A | Demo lead domain | **RESOLVED** → Full platform | — |
| OQ-B | Choke-point definition | OPEN | Phase 9 (F-040) |
| OQ-C | In-situ calibration data available? | OPEN | Phase 4 (F-026) |
| OQ-D | LLM model tier + monthly budget | OPEN | Phase 6 (F-030) |
| OQ-E | NL-query read-only for MVP? | OPEN (default yes) | Phase 6 (F-032) |
| OQ-F | Oil-type default | **RESOLVED** → No default; configurable | — |

---

## Risk Register

| ID | Risk | Severity | Mitigation | Status |
|---|---|---|---|---|
| R-01 | Over-claiming unobservable quantities (pH, nutrients) | HIGH | Honesty invariant INV-3; evidence_class schema enforcement | Mitigated by design |
| R-02 | AI hallucination of environmental values | HIGH | Grounding guard (F-030); no live LLM in default tests | Mitigated by design |
| R-03 | CDSE quota exhaustion (>1GB/day) | HIGH | Subset-first policy; bytes_or_calls tracking; refuse oversized | Policy in place |
| R-04 | Open-Meteo call exhaustion (>10k/day) | MEDIUM | Call counting; caching; backoff | Policy in place |
| R-05 | GPL contamination (OpenDrift leaks into spine) | HIGH | Process isolation (ADR-0002, F-011) | ADR in place |
| R-06 | phase-0.md v1.0 entity names used by agent | CRITICAL | FIXED in this session | Resolved |
| R-07 | ADR-0001 + ADR-0002 permanently lost | MEDIUM | Reconstructed as stubs; decisions preserved in ADR-0003/0004 refs | Mitigated |
| R-08 | Predictor ships to UI without validation | HIGH | Skill gate (F-029); SkillReport.passed_gate enforced | Design pattern |
| R-09 | Oil type hardcoded in simulation | MEDIUM | INV-5; ADR-0006; oil_types.yaml registry | ADR in place |
| R-10 | Scope sprawl (all domains at once) | MEDIUM | Phase sequencing; interface gates | Phased roadmap |
| R-11 | DEM/hydrology tool copyleft (pysheds/WhiteboxTools) | MEDIUM | License check required before F-040 | OPEN |
| R-12 | No TESTING.md → agents skip tests | HIGH | FIXED in this session | Resolved |

---

## Technical Debt Register

| ID | Debt | Introduced in | Must pay before |
|---|---|---|---|
| TD-01 | Naive dark-spot detector (F-005) | Phase 0 | Phase 1 (F-007 replaces internals) |
| TD-02 | SQLite GeoJSON-as-text (no spatial index) | F-003 | post-MVP (PostgreSQL/PostGIS migration) |
| TD-03 | No scheduler (manual per-event run) | Design | Phase 8 (F-037) |
| TD-04 | No in-situ calibration ingestion | Design | when reference data available (OQ-C) |
| TD-05 | Relative-only WQ metrics until OQ-C resolved | Phase 4 | OQ-C resolution |
| TD-06 | ADR-0001 + ADR-0002 are reconstructed stubs | Session 1 | If original docs are recovered |

---

## Repository Statistics

| Metric | Value | Target |
|---|---|---|
| Total markdown files | 4 (root) + 56 (docs/) | 60 |
| Implementation files | 0 | ~80 |
| Test files | 0 | ~25 |
| Phases specced | 12/12 | 12/12 |
| Features specced | 57/57 | 57/57 |
| ADRs published | 7/8 (ADR-0007 draft, ADR-0008 accepted) | 8/8 |
| Validators defined | 22 | 22 |
| Open questions | 4 open, 2 resolved | 6 resolved |
| Cost compliance | $0 confirmed | $0 |
