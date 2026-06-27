# Phase 11 — System Integration, Validation & MVP Sign-off

- **Status:** Specced; waiting for Phase 10
- **Priority:** P0 (required for MVP)
- **Last updated:** 2026-06-27
- **Features:** F-052–F-056
- **Depends on:** Phase 10 complete (production dashboard built)
- **Related:** [phase-10.md](phase-10.md) · [PRD.md](../product/PRD.md) · [VALIDATORS.md](../governance/VALIDATORS.md)
- **Checkpoint:** Completes CP-4 (production ready) = **MVP**

**Goal:** End-to-end system validation, performance optimization, documentation finalization,
and formal MVP sign-off. The MVP is complete when F-056 passes.

---

## F-052 — End-to-End Integration Test Suite

**Why:** Unit and phase tests prove individual features work; integration tests prove the
whole system works together as specified.

**Depends on:** F-051

**Owns / creates:**
- `tests/integration/test_e2e_oil.py` (D1: detect → trajectory → impact → alert)
- `tests/integration/test_e2e_wq.py` (D2: ingest → analyze → anomaly → forecast → alert)
- `tests/integration/test_e2e_ai.py` (AI: grounded report + NL query end-to-end)
- `tests/integration/test_e2e_full.py` (all domains in one run; all validators pass)
- `scripts/harness/run_integration.sh`

**All integration tests are offline by default** (fixtures); live variant with `--live`.

**Acceptance criteria:**
- `tests/integration/test_e2e_full.py` passes offline
- All 22 validators pass when harness runs against the full codebase
- No VAL-008 violation (GPL isolation intact)
- No VAL-010 violation (no live network in default tests)
- No VAL-017 violation (no hardcoded oil types)

---

## F-053 — Performance Profiling + Optimization

**Why:** MVP requires end-to-end run < 10 min per AOI on a laptop (PRD §5).

**Depends on:** F-052

**Owns / creates:**
- `scripts/benchmark/run_benchmark.sh`
- `docs/status/performance_baseline.md`

**Profile targets:**
- Scene acquisition (mocked): < 1s
- SAR preprocessing: < 30s per scene
- Detection: < 60s per scene
- Trajectory simulation: < 5 min (60 timesteps, 1000 particles)
- WQ analysis: < 30s per water body
- AI report generation: < 30s (Anthropic API; mocked in benchmarks)
- Total pipeline: < 10 min for one AOI with all domains

**Acceptance criteria:**
- Benchmark script runs on laptop; results documented in `performance_baseline.md`
- Any stage > 2× budget: optimized or documented with justification

---

## F-054 — Documentation Finalization

**Why:** The MVP must be usable by someone reading the docs. All docs must be current.

**Depends on:** F-053

**Owns / creates:**
- `docs/USER_GUIDE.md` (how to install, configure, run Argus; AOI setup; first run)
- `docs/api/API_SPEC.md` (finalized; all endpoints documented)
- `docs/DEPLOYMENT.md` (how to deploy on WSL; system requirements; environment setup)
- `scripts/harness/doc_coverage.sh` (implemented; checks all modules have docstrings)

**Acceptance criteria:**
- A new user can follow USER_GUIDE.md to set up and run Argus on a clean WSL install
- All API endpoints in API_SPEC.md match actual FastAPI routes
- `scripts/harness/doc_coverage.sh` reports ≥ 80% module documentation

---

## F-055 — Demo Dataset Preparation + Evaluation Suite

**Why:** The MVP must be demonstrable against real historical events.

**Depends on:** F-054

**Owns / creates:**
- `data/eval/` (complete eval cases for all domains)
  - D1: tobago_2024.json (oil slick — already exists)
  - D2: [reference_lake_bloom_2023.json] (bloom event)
  - D3: [storm_event_2022.json] (flood with known inundation)
  - D4: [choke_point_validation_case.json]
- `docs/status/eval_results.md` (recorded eval metrics for all cases)

**Acceptance criteria:**
- All 4 domain eval cases have product_id refs (no raw imagery)
- Each eval case has been run and results recorded (even if metrics are baseline-only)
- `SkillReport.passed_gate=True` for all production predictors

---

## F-056 — MVP Validation Checklist + Sign-off

**Why:** The MVP must be formally verified against the PRD §5 criteria.

**Depends on:** F-055

**Owns / creates:**
- `docs/status/mvp_checklist.md`

**Checklist (mirrors PRD §5):**

**Observation coverage:**
- [ ] D1 marine oil: detect → trajectory → impact → alert → viewer DONE
- [ ] D2 inland water quality: full pipeline DONE
- [ ] D3 weather/hydro: ingestion → flood risk + acid risk DONE
- [ ] D4 choke points: DEM → network → choke nodes DONE

**Prediction engine:**
- [ ] OilTrajectory: SkillReport.passed_gate = True
- [ ] WaterQualityForecast: SkillReport.passed_gate = True (beats persistence)
- [ ] AnomalyDetector: SkillReport.passed_gate = True
- [ ] FloodRisk: SkillReport exists (baseline)
- [ ] AcidDepositionRisk: implemented and labeled

**AI layer:**
- [ ] NL reports: grounding rate = 100%
- [ ] NL query: grounded, cited, read-only
- [ ] Anomaly explanation: advisory, confidence-labeled

**Infrastructure:**
- [ ] All 22 validators pass
- [ ] End-to-end run < 10 min (F-053 benchmark)
- [ ] Zero recurring cost confirmed
- [ ] USER_GUIDE.md complete
- [ ] All API endpoints documented

**UI/UX:**
- [ ] Production dashboard built and functional
- [ ] All domains visible simultaneously
- [ ] AI assistant interface functional
- [ ] Evidence labels on all modeled/inferred values

**Sign-off:** When all checklist items are checked, Josh signs off on this document.
The project is then in MVP state.

**Acceptance criteria:**
- All checklist items above are marked done
- `docs/status/mvp_checklist.md` exists and is fully checked off
- Josh has reviewed and signed off on this document

## Phase 11 Definition of Done = MVP

Phase 11 is done when F-056 sign-off is complete. That is the MVP.
