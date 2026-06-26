# Argus — Task Board

- **This file is the single source of truth for progress.** Every agent updates it.
- **Status values:** `TODO` · `IN_PROGRESS` · `BLOCKED` · `IN_REVIEW` · `DONE`
- **Rule:** at the end of every session, set statuses honestly (reconcile against git reality)
  and append a HANDOFF note at the bottom.

Last reconciled: 2026-06-27 · by: governance session (architecture / spec build)
Scope: **v2.1 Environmental Intelligence Platform** — MVP = CP-4 (Phase 11 complete, Josh sign-off).
See [`docs/adr/ADR-0005-mvp-redefinition.md`](docs/adr/ADR-0005-mvp-redefinition.md).

Open questions blocking code: OQ-B (choke-point definition), OQ-C (calibration source),
OQ-D (LLM tier/budget), OQ-E (NL-query read-only). See [`docs/product/OPEN_QUESTIONS.md`](docs/product/OPEN_QUESTIONS.md).

---

## Phase 0 — Foundation & spike (D1 oil) *(P0)*

Detailed specs: [`docs/features/phase-0.md`](docs/features/phase-0.md)

| ID | Feature | Status | Owner | Notes |
|---|---|---|---|---|
| F-000 | Repo & tooling scaffold | TODO | — | start here |
| F-001 | Config + AOI/target model & loader | TODO | — | dep F-000 |
| F-002 | CDSE catalogue client (auth + search) | TODO | — | dep F-001 · creds via env |
| F-003 | Scene acquisition + persistence | TODO | — | dep F-002 · prefer subset |
| F-004 | SAR preprocessing (masked σ⁰ dB) | TODO | — | dep F-003 |
| F-005 | Naive dark-spot detector + Observation(obs_type="oil_slick") | TODO | — | dep F-004 · fixes Domain interface |
| F-006 | Static product export — spike close | TODO | — | dep F-005 |

## Phase 1 — Detection vertical (oil) *(P0)*

Detailed specs: [`docs/features/phase-1.md`](docs/features/phase-1.md)

| ID | Feature | Status | Owner | Notes |
|---|---|---|---|---|
| F-007 | Robust dark-spot segmentation + features | TODO | — | dep F-006 |
| F-008 | Look-alike rejection + confidence | TODO | — | dep F-007 |
| F-009 | Eval harness + labeled dataset + P/R | TODO | — | dep F-008 |
| F-010 | Detection characterization & schema finalize | TODO | — | dep F-008 |

## Phase 2 — Simulation vertical (oil) *(P0)*

Detailed specs: [`docs/features/phase-2.md`](docs/features/phase-2.md)

| ID | Feature | Status | Owner | Notes |
|---|---|---|---|---|
| F-011 | OpenOil sim service (isolated subprocess) + seeding | TODO | — | dep F-010 · GPL isolation (ADR-0002 D2) |
| F-012 | Metocean forcing providers + cache + fallback | TODO | — | dep F-011 |
| F-013 | ForecastFrames + trajectory eval | TODO | — | dep F-012 |

## Phase 3 — Impact, delivery & viewer (oil) *(P0)* — CP-1

Detailed specs: [`docs/features/phase-3.md`](docs/features/phase-3.md)

| ID | Feature | Status | Owner | Notes |
|---|---|---|---|---|
| F-014 | Exposure layers + impact + ETA | TODO | — | dep F-013 |
| F-015 | FastAPI service | TODO | — | dep F-014 |
| F-016 | Web viewer | TODO | — | dep F-015 |
| F-017 | Alert delivery + product export — **CP-1 close** | TODO | — | dep F-016 |

## Phase 3.5 — Foundation Hardening *(P0)*

Detailed specs: [`docs/features/phase-3.5.md`](docs/features/phase-3.5.md)

| ID | Feature | Status | Owner | Notes |
|---|---|---|---|---|
| F-018 | API contract finalization (OpenAPI spec + versioning) | TODO | — | dep F-015 |
| F-019 | Integration test framework + harness scripts | TODO | — | dep F-017 |
| F-020 | Structured error handling (error catalog + codes) | TODO | — | dep F-015 |
| F-021 | Structured logging (JSON log format + trace IDs) | TODO | — | dep F-000 |
| F-022 | Config management (settings.yaml schema + env override) | TODO | — | dep F-001 |
| F-023 | Health checks + readiness endpoints | TODO | — | dep F-015 |

## Phase 4 — Domain D2: Inland Water Quality *(P0)*

Detailed specs: [`docs/features/phase-4.md`](docs/features/phase-4.md)

| ID | Feature | Status | Owner | Notes |
|---|---|---|---|---|
| F-024 | Water-body model + targets + resolution gate | TODO | — | `below_resolution` policy |
| F-025 | Sentinel-2/3 optical ingestion | TODO | — | dep F-024 |
| F-026 | `inland_wq` analyzer (chl-a/turbidity/CDOM/temp) + calibration state | TODO | — | dep F-025 · measured-proxy tag |

## Phase 5 — Prediction Engine: Water Quality *(P0)*

Detailed specs: [`docs/features/phase-5.md`](docs/features/phase-5.md)

| ID | Feature | Status | Owner | Notes |
|---|---|---|---|---|
| F-027 | Seasonal baseline + AnomalyDetector | TODO | — | dep F-026 |
| F-028 | WaterQualityForecast (+ CI) | TODO | — | dep F-026 · Open-Meteo drivers |
| F-029 | Predictor interface + validation/skill gate | TODO | — | dep F-028 · beat persistence |

## Phase 6 — AI Layer *(P0)*

Detailed specs: [`docs/features/phase-6.md`](docs/features/phase-6.md)

| ID | Feature | Status | Owner | Notes |
|---|---|---|---|---|
| F-030 | Assistant scaffolding + grounding/citation guards | TODO | — | dep F-027/F-028 · no invented values |
| F-031 | NL situation reports (grounded, cited) | TODO | — | dep F-030 |
| F-032 | NL query (read-only; OQ-E resolved) | TODO | — | dep F-030 |
| F-033 | Anomaly explanation / triage (advisory) | TODO | — | dep F-030, F-027 |

## Phase 7 — Platform Integration *(P0)* — CP-2

Detailed specs: [`docs/features/phase-7.md`](docs/features/phase-7.md)

| ID | Feature | Status | Owner | Notes |
|---|---|---|---|---|
| F-034 | WQ exposure (intakes/recreation) + impact | TODO | — | dep F-026 |
| F-035 | Viewer + API extended to D2 | TODO | — | dep F-034, F-016 |
| F-036 | Alerting + products for D2 — **CP-2 close** | TODO | — | dep F-035 · HAB early-warning |

## Phase 8 — Automation & Scheduling *(P1)*

Detailed specs: [`docs/features/phase-8.md`](docs/features/phase-8.md)
Note: requires ADR-0007 (scheduler) before F-037 starts.

| ID | Feature | Status | Owner | Notes |
|---|---|---|---|---|
| F-037 | Per-domain tasking + scheduler (quota-aware) | TODO | — | ADR-0007 required first |
| F-038 | Incremental ingestion + idempotency + run history | TODO | — | dep F-037 |
| F-039 | Observability (metrics + run dashboard) | TODO | — | dep F-038 |

## Phase 9 — Domains D3 (weather/hydro) & D4 (choke points) *(P1)* — CP-3

Detailed specs: [`docs/features/phase-9.md`](docs/features/phase-9.md)

| ID | Feature | Status | Owner | Notes |
|---|---|---|---|---|
| F-040 | D4 choke points (DEM flow-accumulation) | BLOCKED | — | BLOCKED: OQ-B unresolved |
| F-041 | D3 ingestion (Open-Meteo + SO₂/NO₂ + S1 inundation) | TODO | — | dep F-040 |
| F-042 | FloodRisk predictor + hydro impact | TODO | — | dep F-041 |
| F-043 | AcidDepositionRisk index (modeled; never a measurement) | TODO | — | dep F-041 |
| F-044 | Hydro viewer + alerting + generalization pass — **CP-3 close** | TODO | — | dep F-042, F-043 |

## Phase 10 — Production Dashboard *(P0)* — MVP prerequisite

Detailed specs: [`docs/features/phase-10.md`](docs/features/phase-10.md)

| ID | Feature | Status | Owner | Notes |
|---|---|---|---|---|
| F-045 | React + Vite + Tailwind frontend scaffold | TODO | — | dep F-015 |
| F-046 | Overview dashboard (system health, all domains) | TODO | — | dep F-045 |
| F-047 | WQ monitoring panel (trends, anomalies, forecasts) | TODO | — | dep F-045, F-027/F-028 |
| F-048 | Hazard prediction panel (trajectory player, flood risk) | TODO | — | dep F-045, F-013/F-042 |
| F-049 | AI assistant interface with citation viewer | TODO | — | dep F-045, F-031/F-032 |
| F-050 | Admin panel (AOI/target management, config) | TODO | — | dep F-045 |
| F-051 | Export + reporting UI (PDF/GeoJSON/CSV) | TODO | — | dep F-046 |

## Phase 11 — System Validation & MVP Sign-off *(P0)* — CP-4 = MVP

Detailed specs: [`docs/features/phase-11.md`](docs/features/phase-11.md)

| ID | Feature | Status | Owner | Notes |
|---|---|---|---|---|
| F-052 | End-to-end integration tests (all 4 domains) | TODO | — | dep all phases |
| F-053 | Performance profiling (< 10min/AOI target) | TODO | — | dep F-052 |
| F-054 | Documentation finalization (USER_GUIDE, API_SPEC, DEPLOYMENT) | TODO | — | dep F-052 |
| F-055 | Demo dataset preparation (all 4 domain eval cases) | TODO | — | dep F-052 |
| F-056 | MVP validation checklist + Josh sign-off — **CP-4 = MVP** | TODO | — | dep F-052–F-055 |

---

## HANDOFF Log

> Append a short entry every session. Newest on top.

```
### YYYY-MM-DD — <agent> — <feature ids>
- Did: <what landed + file paths>
- State: <acceptance criteria pass/fail; tests green?>
- Git: <branch / commit>
- Quota: <CDSE bytes / Open-Meteo calls used, if any live fetch>
- Next: <single next action>
- Blockers/decisions: <anything needing a human or ADR>
```

### 2026-06-27 — governance — deployment strategy + git init + repo finalization (Session 3)

- Did: ADR-0008 (deployment: Vercel + Cloud Run + GCS), INV-10 (scale-to-zero), §13/§14 in
  CLAUDE.md (git identity: CXLD10/no AI co-author, deployment constraints). Cleaned root
  duplicate files, fixed broken links, rewrote README.md, created .gitignore/.gitattributes/
  .editorconfig, added config/oil_types.yaml + config/settings.yaml. Git initialized.
- State: Docs complete; 0 code; initial commit pending email confirmation from Josh.
- Git: initialized; not yet committed. Josh must confirm GitHub no-reply email before first commit.
- Quota: Zero.
- Next: Confirm `git config user.email "{id}+CXLD10@users.noreply.github.com"`, make initial
  commit (`chore: initialize repository`), connect remote, then begin **F-000**.
- Blockers: Josh needs to provide exact GitHub no-reply email (`! git config user.email` in
  chat to set it; find ID at github.com/settings/emails).

### 2026-06-27 — governance — full spec/docs build (Sessions 2–3)

- Did: Complete repository transformation. Created 47+ new files across docs/ hierarchy:
  all governance (VALIDATORS, HARNESS, spec_graph), all status logs (DASHBOARD, program_log,
  decision_log, change_log), PRD v2.1, OPEN_QUESTIONS, ADR-0001–0006, CLAUDE.md, all 3
  standards (TESTING, CODING, QUOTAS), all 12 phase specs (phase-0 through phase-11 incl. 3.5,
  10, 11), all 4 domain specs (D1–D4), all 5 predictor specs, AI assistant spec, ARCHITECTURE.md
  (docs/architecture/), DATA_MODELS.md (docs/architecture/), STACK.md, and updated root files
  (README, BOARD, ROADMAP with stub pointers).
- State: Docs only; zero code. All phase specs v2.0 names (AnalysisRun/Observation/Domain).
  Root ARCHITECTURE.md/DATA_MODELS.md/PRD.md/ROADMAP.md are stubs pointing to docs/.
  Config templates created (oil_types.yaml, settings.yaml). Harness scripts scaffolded.
- Git: Not committed yet.
- Quota: Zero (no live network calls).
- Next: **F-000** — repo & tooling scaffold. Read CLAUDE.md, then docs/features/phase-0.md.
- Blockers/decisions: OQ-B (choke points, blocks F-040); OQ-C (calibration, blocks F-026
  absolute metrics); OQ-D (LLM tier/budget, blocks F-030); OQ-E (NL-query read-only = default
  yes, but needs Josh confirmation to close). ADR-0007 (scheduler) required before F-037.

### 2026-06-26 — planning — scope v1.0 → v2.0

- Did: Reframed Argus to water-health intelligence platform (PRD/ARCHITECTURE/ROADMAP/
  DATA_MODELS → v2.0; added ADR-0003 domains + ADR-0004 prediction/AI). Phases 4–9 added.
- State: Docs only; no code. Phase 0 specs (features/phase-0.md) v1.0 — superseded by
  docs/features/phase-0.md v2.0 with corrected entity names.
- Next: F-000 is the first build task. Before Phase 4, resolve OQ-A (now resolved: ADR-0005).
- Blockers/decisions: OQ-A (RESOLVED→ADR-0005); OQ-B, OQ-C, OQ-D, OQ-E remain open.
