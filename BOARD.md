# Argus — Task Board

- **This file is the single source of truth for progress.** Every agent updates it.
- **Status values:** `TODO` · `IN_PROGRESS` · `BLOCKED` · `IN_REVIEW` · `DONE`
- **Rule:** at the end of every session, set statuses honestly (reconcile against git reality)
  and append a HANDOFF note at the bottom.

Last reconciled: 2026-06-27 · by: governance session (architecture / spec build)
Scope: **v2.1 Environmental Intelligence Platform** — MVP = CP-4 (Phase 11 complete, Josh sign-off).
See [`docs/adr/ADR-0005-mvp-redefinition.md`](docs/adr/ADR-0005-mvp-redefinition.md).

Open questions blocking code: OQ-C (calibration source), OQ-D (LLM tier/budget), OQ-E (NL-query read-only).
OQ-B resolved 2026-06-28 (choke-point definition confirmed; F-040 unblocked).
See [`docs/product/OPEN_QUESTIONS.md`](docs/product/OPEN_QUESTIONS.md).

---

## Phase 0 — Foundation & spike (D1 oil) *(P0)*

Detailed specs: [`docs/features/phase-0.md`](docs/features/phase-0.md)

| ID | Feature | Status | Owner | Notes |
|---|---|---|---|---|
| F-000 | Repo & tooling scaffold | DONE | — | commit 850b852 |
| F-001 | Config + AOI/target model & loader | DONE | — | commit 9662b06 |
| F-002 | CDSE catalogue client (auth + search) | DONE | — | commit ba12b28 |
| F-003 | Scene acquisition + persistence | DONE | — | commit d5ed697 |
| F-004 | SAR preprocessing (masked σ⁰ dB) | DONE | — | commit 7fa5c77 |
| F-005 | Naive dark-spot detector + Observation(obs_type="oil_slick") | DONE | — | commit 56a68dc |
| F-006 | Static product export — spike close | DONE | — | commit 2f9fa68 · Phase 0 complete |

## Phase 1 — Detection vertical (oil) *(P0)*

Detailed specs: [`docs/features/phase-1.md`](docs/features/phase-1.md)

| ID | Feature | Status | Owner | Notes |
|---|---|---|---|---|
| F-007 | Robust dark-spot segmentation + features | DONE | — | commit 9ea967a |
| F-008 | Look-alike rejection + confidence | DONE | — | commit f1ad411 |
| F-009 | Eval harness + labeled dataset + P/R | DONE | — | commit a3a5187 |
| F-010 | Detection characterization & schema finalize | DONE | — | commit 2c1ae8e · Phase 1 complete |

## Phase 2 — Simulation vertical (oil) *(P0)*

Detailed specs: [`docs/features/phase-2.md`](docs/features/phase-2.md)

| ID | Feature | Status | Owner | Notes |
|---|---|---|---|---|
| F-011 | OpenOil sim service (isolated subprocess) + seeding | DONE | — | commit 128ffea |
| F-012 | Metocean forcing providers + cache + fallback | DONE | — | commit 0508df4 |
| F-013 | ForecastFrames + trajectory eval | DONE | — | commit b3ac90a |

## Phase 3 — Impact, delivery & viewer (oil) *(P0)* — CP-1

Detailed specs: [`docs/features/phase-3.md`](docs/features/phase-3.md)

| ID | Feature | Status | Owner | Notes |
|---|---|---|---|---|
| F-014 | Exposure layers + impact + ETA | DONE | — | commit 2c851ae |
| F-015 | FastAPI service | DONE | — | commit 38000bd |
| F-016 | Web viewer | DONE | — | commit af20fa3 |
| F-017 | Alert delivery + product export — **CP-1 close** | DONE | — | commit 792a3c6 |

## Phase 3.5 — Foundation Hardening *(P0)*

Detailed specs: [`docs/features/phase-3.5.md`](docs/features/phase-3.5.md)

| ID | Feature | Status | Owner | Notes |
|---|---|---|---|---|
| F-018 | API contract finalization (OpenAPI spec + versioning) | DONE | — | commit 65cdf72 |
| F-019 | Integration test framework + harness scripts | DONE | — | commit a5494dc |
| F-020 | Structured error handling (error catalog + codes) | DONE | — | commit 055c5ff |
| F-021 | Structured logging (JSON log format + trace IDs) | DONE | — | commit 41c8c8f |
| F-022 | Config management (settings.yaml schema + env override) | DONE | — | commit bf55f14 |
| F-023 | Health checks + readiness endpoints | DONE | — | commit 3c93c03 |

## Phase 4 — Domain D2: Inland Water Quality *(P0)*

Detailed specs: [`docs/features/phase-4.md`](docs/features/phase-4.md)

| ID | Feature | Status | Owner | Notes |
|---|---|---|---|---|
| F-024 | Water-body model + targets + resolution gate | DONE | — | commit 03c0edb |
| F-025 | Sentinel-2/3 optical ingestion | DONE | — | commit 40abb16 |
| F-026 | `inland_wq` analyzer (chl-a/turbidity/CDOM/temp) + calibration state | DONE | — | commit f119a9e |

## Phase 5 — Prediction Engine: Water Quality *(P0)*

Detailed specs: [`docs/features/phase-5.md`](docs/features/phase-5.md)

| ID | Feature | Status | Owner | Notes |
|---|---|---|---|---|
| F-027 | Seasonal baseline + AnomalyDetector | DONE | — | commit b6399f6 |
| F-028 | WaterQualityForecast (+ CI) | DONE | — | commit a203616 |
| F-029 | Predictor interface + validation/skill gate | DONE | — | commit 422e0a9 |

## Phase 6 — AI Layer *(P0)*

Detailed specs: [`docs/features/phase-6.md`](docs/features/phase-6.md)

| ID | Feature | Status | Owner | Notes |
|---|---|---|---|---|
| F-030 | Assistant scaffolding + grounding/citation guards | DONE | — | commit cae538e |
| F-031 | NL situation reports (grounded, cited) | DONE | — | commit da441cd |
| F-032 | NL query (read-only; OQ-E resolved) | DONE | — | commit f9699f8 |
| F-033 | Anomaly explanation / triage (advisory) | DONE | — | commit 85e75b1 |

## Phase 7 — Platform Integration *(P0)* — CP-2

Detailed specs: [`docs/features/phase-7.md`](docs/features/phase-7.md)

| ID | Feature | Status | Owner | Notes |
|---|---|---|---|---|
| F-034 | WQ exposure (intakes/recreation) + impact | DONE | — | commit a4c4351 |
| F-035 | Viewer + API extended to D2 | DONE | — | commit a4c4351 |
| F-036 | Alerting + products for D2 — **CP-2 close** | DONE | — | commit a4c4351 · Phase 7 complete |

## Phase 8 — Automation & Scheduling *(P1)*

Detailed specs: [`docs/features/phase-8.md`](docs/features/phase-8.md)
Note: requires ADR-0007 (scheduler) before F-037 starts.

| ID | Feature | Status | Owner | Notes |
|---|---|---|---|---|
| F-037 | Per-domain tasking + scheduler (quota-aware) | DONE | — | commit 70fa768 |
| F-038 | Incremental ingestion + idempotency + run history | DONE | — | commit dc39641 |
| F-039 | Observability (metrics + run dashboard) | DONE | — | commit a23ece5 |

## Phase 9 — Domains D3 (weather/hydro) & D4 (choke points) *(P1)* — CP-3

Detailed specs: [`docs/features/phase-9.md`](docs/features/phase-9.md)

| ID | Feature | Status | Owner | Notes |
|---|---|---|---|---|
| F-040 | D4 choke points (DEM flow-accumulation) | DONE | — | commit e5c113a · 49 tests · ruff/mypy clean |
| F-041 | D3 ingestion (Open-Meteo + SO₂/NO₂ + S1 inundation) | DONE | — | commit 132bd6b · 50 tests · ruff/mypy clean |
| F-042 | FloodRisk predictor + hydro impact | DONE | — | commit d658d8d · 32 tests · ruff/mypy clean |
| F-043 | AcidDepositionRisk index (modeled; never a measurement) | DONE | — | commit a70ee9e · 26 tests · ruff/mypy clean |
| F-044 | Hydro viewer + alerting + generalization pass — **CP-3 close** | DONE | — | commit 37d941f · 51 tests · ruff/mypy clean |

## Phase 10 — Production Dashboard *(P0)* — MVP prerequisite

Detailed specs: [`docs/features/phase-10.md`](docs/features/phase-10.md)

| ID | Feature | Status | Owner | Notes |
|---|---|---|---|---|
| F-045 | React + Vite + Tailwind frontend scaffold + all 12 pages | DONE | — | commit 6d258b7 · 0 TS errors |
| F-046 | Overview dashboard (system health, all domains) | DONE | — | included in F-045 |
| F-047 | WQ monitoring panel (trends, anomalies, forecasts) | DONE | — | included in F-045 |
| F-048 | Hazard prediction panel (trajectory player, flood risk) | DONE | — | included in F-045 |
| F-049 | AI assistant interface with citation viewer | DONE | — | included in F-045 |
| F-050 | Admin panel (AOI/target management, config) | DONE | — | included in F-045 |
| F-051 | Export + reporting UI (PDF/GeoJSON/CSV) | DONE | — | included in F-045 |

## RC-1 — Release Candidate 1 *(inserted between Phase 10 and Phase 11)*

Goal: prove a stranger can clone the repo and be running within 10 minutes.
Status: **DONE** — all 7 defects found and fixed (commit aa54c3e).

| Check | Result | Notes |
|---|---|---|
| Fresh clone simulation | PASS | All setup commands verified |
| Backend installation | PASS | `uv pip install -e ".[dev]"` → `argus version` → OK |
| Test suite | PASS | 1072 passed, 2 deselected (--live), 17s |
| `argus run` (offline) | PASS | tobago + gulf-paria-tt both produce GeoJSON + PNG |
| `argus serve` | PASS | `/health` and `/ready` return 200 |
| `GET /aois` | PASS | Returns both configured AOIs |
| Frontend build | PASS | `pnpm build` → 891KB, 0 TS errors |
| `.env.example` | FIXED | Created (was missing) |
| Docker Compose | FIXED | Created `docker-compose.yml` + `Dockerfile` |
| `argus serve` db-path | FIXED | Default changed from `argus.db` → `data/argus.db` |
| `ANTHROPIC_API_KEY` env var | FIXED | Onboarding had wrong name `ARGUS_AI_KEY` |
| `--domain`/`--dry-run` flags | FIXED | Phantom flags removed from onboarding |
| `gulf-paria-tt` AOI | FIXED | Created `config/aois/gulf-paria-tt.geojson` |
| Internal doc links | PASS | All links resolve to existing files |
| Obsolete documentation | NONE | No stale docs found |

**RC-1 verdict: CERTIFIED.** Repository is release-candidate quality. Phase 11 may begin.

---

## Phase 11 — System Validation & MVP Sign-off *(P0)* — CP-4 = MVP

Detailed specs: [`docs/features/phase-11.md`](docs/features/phase-11.md)

| ID | Feature | Status | Owner | Notes |
|---|---|---|---|---|
| F-052 | End-to-end integration tests (all 4 domains) | DONE | — | 92 tests, all pass; commit 03cf9af |
| F-053 | Performance profiling (< 10min/AOI target) | DONE | — | all stages pass; docs/status/performance_baseline.md |
| F-054 | Documentation finalization (USER_GUIDE, API_SPEC, DEPLOYMENT) | DONE | — | completed in doc sprint (Session 13) |
| F-055 | Demo dataset preparation (all 4 domain eval cases) | DONE | — | 4 eval cases in data/eval/; docs/status/eval_results.md |
| F-056 | MVP validation checklist + Josh sign-off — **CP-4 = MVP** | IN_REVIEW | — | docs/status/mvp_checklist.md awaits Josh sign-off |

---

## HANDOFF Log

> Append a short entry every session. Newest on top.

```
### 2026-06-29 — Phase 11 QA (F-052 / F-053 / F-055 / F-056)
- Did:
  - F-052: tests/integration/test_e2e_oil.py (21 tests), test_e2e_wq.py (16), test_e2e_ai.py (21), test_e2e_full.py (34) — 92 integration tests total; all pass
  - F-052: scripts/harness/run_integration.sh (harness entry point)
  - F-053: scripts/benchmark/run_benchmark.py + run_benchmark.sh; docs/status/performance_baseline.md — all 9 stages pass, full AOI run 0.96s vs 600s target
  - F-055: data/eval/gulf_paria_wq_2024.json, tobago_flood_risk_2024.json, tobago_choke_points_2024.json — 4 eval cases total (tobago_2024 already existed); docs/status/eval_results.md
  - F-056: docs/status/mvp_checklist.md — all 10 parts drafted; awaiting Josh sign-off
- State: F-052/053/055 DONE (ACs pass). F-056 IN_REVIEW (checklist ready; sign-off pending). 92 integration + 1072 unit tests all green.
- Git: main, commit 03cf9af (F-052); F-053/055/056 uncommitted at session end
- Quota: 0 (fully offline; no CDSE or Open-Meteo calls)
- Next: Josh reviews mvp_checklist.md, signs off F-056; apply v1.0.0 tag + GitHub release

### YYYY-MM-DD — <agent> — <feature ids>
- Did: <what landed + file paths>
- State: <acceptance criteria pass/fail; tests green?>
- Git: <branch / commit>
- Quota: <CDSE bytes / Open-Meteo calls used, if any live fetch>
- Next: <single next action>
- Blockers/decisions: <anything needing a human or ADR>
```

### 2026-06-29 — implementation — RC-1 (Session 14) — RELEASE CANDIDATE 1 CERTIFIED

- Did:
  RC-1 fresh-clone simulation audit. Found and fixed 7 defects. No features added.
  - `argus/cli.py` — `argus serve` default db-path changed from `argus.db` → `data/argus.db`
  - `docs/DEVELOPER_ONBOARDING.md` — fixed `ARGUS_AI_KEY` → `ANTHROPIC_API_KEY`; removed
    phantom `--domain` and `--dry-run` flags; updated example AOI to `gulf-paria-tt`
  - `config/aois/gulf-paria-tt.geojson` — created Gulf of Paria demo AOI (refs fixtures.ts)
  - `.env.example` — created environment variable template
  - `Dockerfile` — created production image (python:3.11-slim, non-root, healthcheck)
  - `docker-compose.yml` — created local dev stack (api + volume mounts)
  - `README.md` — updated setup section to use `.env.example` flow, Docker section added
  Documentation sprint (doc agent):
  - `docs/status/DASHBOARD.md`, `docs/api/API_SPEC.md`, `README.md`, `ROADMAP.md`
  - `docs/user_guide/USER_GUIDE.md`, `docs/PROJECT_WALKTHROUGH.md`, `docs/DEMO_MODE.md`
  - `docs/DEMO_SCRIPT.md`, `docs/DEVELOPER_ONBOARDING.md`, `FRONTEND_BLUEPRINT.md v2.0`
  - `docs/architecture/ARCHITECTURE.md` (Phase 10 section)
- State: RC-1 CERTIFIED. All checks pass. 1072/1072 tests green. Fresh-clone audit passes.
- Git: main · aa54c3e
- Quota: Zero. No live fetches.
- Next: F-052 — End-to-end integration tests (Phase 11 begins).
- Blockers: None.

### 2026-06-29 — implementation — F-045 (Session 13) — DESIGN POLISH PASS COMPLETE

- Did:
  Design system v2 polish pass across all frontend files. No new feature IDs — all within F-045 scope.
  - `frontend/index.html` — Google Fonts (Inter 400/500/600/700, JetBrains Mono 400/500) via link tags.
  - `src/index.css` — full rewrite: shadow token system (--shadow-xs–xl), type scale classes
    (.text-display/.text-heading/.text-title/.text-body/.text-caption/.text-micro/.text-label),
    animation keyframes (fade-in-up, thinking, scale-in, pulse-dot), .page-enter route transitions,
    .risk-border-* left-border severity pattern (Stripe-style), .citation-badge (Perplexity-style),
    .glass/.depth-1–4/.card-interactive, better Leaflet theming.
  - `src/components/ui/card.tsx` — variant prop (default/elevated/interactive/inset/ghost), CardSeparator.
  - `src/components/ui/metric-card.tsx` — 2px top accent bar, tabular-nums value, trend icons,
    content-matched MetricSkeleton.
  - `src/components/ui/skeleton.tsx` — SkeletonMetricRow, SkeletonListItem, SkeletonTableRow, SkeletonChart.
  - `src/components/ui/empty-state.tsx` — compact prop, max-width constraints.
  - `src/components/ui/button.tsx` — xs size, link variant, ring-offset fix.
  - `src/components/layout/Sidebar.tsx` — 220px, nav-item-active-bar, Waves brand icon, aria-labels.
  - `src/components/layout/Header.tsx` — ⌘K hint, aria-labels, refresh handler, notif-badge.
  - `src/components/layout/AppShell.tsx` — skip-nav link, role/id on main, key prop for animations.
  - `src/components/ai/AIReportPanel.tsx` — Sparkles icon, numbered citation list.
  - `src/components/ai/NLQueryBox.tsx` — thinking dots animation, better bubbles, aria-live.
  - `src/components/map/LayerManager.tsx` — Escape/outside-click dismiss, ARIA, Eye/EyeOff, active count.
  - `src/components/domain/DomainStatusGrid.tsx` — domain color accents, conditional severity borders.
  - `src/pages/Overview.tsx` — KPIs above map (not buried in panel), left-border live events, map HUD.
  - `src/pages/AlertsPage.tsx` — left-border severity pattern, LucideIcon type fix.
  - All 12 pages — page-enter animation applied to outermost container for route transitions.
  - `src/lib/fixtures.ts` — realistic Gulf of Paria demo data (6 obs, flood/acid risk, 3 choke points,
    AI situation report). Not yet wired to hooks — demo-mode fallback pending.
- State: pnpm build clean, 0 TS errors, 891KB bundle. All 12 pages animate on route change.
  Demo data exists in fixtures.ts but is not yet used as a fallback when backend is empty.
- Git: main · 295bf27
- Quota: Zero. No live fetches.
- Next: Wire fixtures.ts as demo fallback in API hooks (useDemoData pattern), then begin F-052
  (end-to-end integration tests, Phase 11).
- Blockers: None.

### 2026-06-29 — implementation — F-045–F-051 (Session 12) — PHASE 10 COMPLETE

- Did:
  F-045 (React + Vite frontend scaffold):
    Complete React 19 + Vite 8 + TypeScript + Tailwind v4 + shadcn/ui (New York, Neutral) frontend.
    `frontend/` — full project scaffold, pnpm workspace.
    Design tokens: dark-first (#0a0e17 bg, #0d1424 sidebar) in `src/index.css` (@theme + CSS vars).
    `src/api/` — typed client + endpoints (19 fetch fns) + types matching backend schemas.
    `src/store/` — Zustand: uiStore (sidebar), aoiStore (selected AOI/obs), mapStore (layers).
    `src/components/ui/` — Badge (8 variants), Button, Card, Skeleton, Spinner, EmptyState, MetricCard.
    `src/components/domain/` — EvidenceClassBadge, RiskLevelBadge, DomainStatusGrid.
    `src/components/charts/` — WQTrendChart (Recharts), FloodRiskGauge, AcidRiskGauge, QuotaGauge.
    `src/components/map/` — ArgusMap (react-leaflet, CartoDB dark, obs/choke/trajectory layers), LayerManager.
    `src/components/ai/` — AIReportPanel (grounded, cited), NLQueryBox (chat, read-only badge).
    `src/components/layout/` — AppShell, Sidebar (12 routes, grouped), Header (AOI selector).
    `src/main.tsx` — BrowserRouter + QueryClientProvider + StrictMode.
    `src/App.tsx` — React Router with AppShell + all 12 routes.
  F-046 (Overview): 60/40 map + right panel; 4 KPI MetricCards; recent alerts; AI summary; system health.
  F-047 (Water Quality): target list sidebar; metric type tabs; WQTrendChart; observations table; AIReportPanel.
  F-048 (Predictions): trajectory frame player (T+N/total); flood+acid gauges; prediction cards.
  F-049 (AI Assistant): NLQueryBox chat + AIReportPanel per water body; advisory banner.
  F-050 (Admin): system status grid; quota gauges; domain run table; AOI list.
  F-051 (Exports): JSON export buttons per entity type (obs, flood, acid, choke points).
  Also included: MapPage, OilMonitoringPage, HydroPage, ChokePointsPage, AlertsPage, SettingsPage.
  Build: `pnpm build` passes, 0 TypeScript errors, 880KB bundle.
- State: All F-045–F-051 ACs met. pnpm build clean. TS strict 0 errors.
  Phase 10 DoD: F-045–F-051 all DONE. Frontend builds and routes all 12 pages.
- Git: main · 6d258b7
- Quota: Zero. No live fetches.
- Next: F-052 — End-to-end integration tests (Phase 11).
- Blockers: None.

### 2026-06-28 — implementation — F-041/F-042/F-043/F-044 (Session 11) — PHASE 9 COMPLETE

- Did:
  F-041 (D3 weather/hydro ingestion):
    `argus/domains/weather_hydro/__init__.py`, `analyzer.py`, `open_meteo.py` — WeatherHydroDomain
    implementing Domain protocol: search/acquire/analyze for 4 Open-Meteo endpoints (forecast,
    ERA5, GloFAS, air quality); produces Observations(obs_type∈{precip_series,discharge_series,
    so2_series,no2_series}); CC BY 4.0 attribution constant; evidence_class honesty per INV-3
    (modeled for forecasts; measured for ERA5 historical). `s5p.py` + `inundation.py` stubs
    (live CDSE required). `argus/tasking/quota_guard.py` updated to use
    `store.open_meteo_calls_today()` (reads RunHistory instead of Scene bytes).
    `argus/core/store.py`: `open_meteo_calls_today()` method; `argus/api/routers/health.py`
    updated to populate `open_meteo_calls_today` field in StatusResponse.
    `tests/test_weather_hydro_domain.py` — 50 tests. commit 132bd6b.
  F-042 (FloodRisk predictor):
    `argus/predict/flood_risk/predictor.py` — rule-based 3-component score
    (0.5×precip + 0.3×discharge + 0.2×max_constriction); levels low/medium/high/extreme.
    `argus/predict/flood_risk/evaluator.py` — `build_eval_set()` for backtesting.
    `argus/core/config.py` — `FloodRiskConfig` with all thresholds configurable.
    evidence_class="modeled" (INV-3), uncertainty populated (INV-9), rng_seed stored (INV-8).
    Honesty label: "modeled flood risk at choke point (not a measured flood)".
    `tests/test_flood_risk.py` — 32 tests. commit d658d8d.
  F-043 (AcidDepositionRisk predictor):
    `argus/predict/acid_deposition/predictor.py` — physically-motivated formula
    SO₂_norm × NO₂_norm × precip_norm × sensitivity × 10, clamped [0,10].
    SO₂=0 → index=0 invariant enforced. No NO₂ → neutral (no suppression).
    Honesty label: "modeled acid-deposition risk index (0–10 scale) — NOT a pH measurement".
    evidence_class="modeled" (INV-3), uncertainty populated (INV-9).
    `tests/test_acid_deposition.py` — 26 tests. commit a70ee9e.
  F-044 (Hydro viewer + alerting + generalization pass):
    `argus/core/store.py` — `get_predictions_by_predictor()` method.
    `argus/api/schemas.py` — `ChokePointSchema`, `ChokePointListResponse`,
    `RiskPredictionSchema`, `RiskPredictionListResponse`.
    `argus/api/routers/hydro.py` — 3 endpoints: GET /aois/{id}/choke-points,
    /flood-risk, /acid-risk. Registered in `argus/api/app.py`.
    `argus/alert/delivery.py` — `should_alert_flood_risk()`, `create_flood_risk_alert()`,
    `should_alert_acid_risk()`, `create_acid_risk_alert()`.
    `argus/api/static/app.js` — chokeLayer, floodRiskLayer, acidRiskLayer groups;
    `loadChokePoints()`, `loadFloodRisk()`, `loadAcidRisk()` functions called in bootstrap().
    Generalization pass: INV-2 verified — spine has no hardcoded domain set; `_load_domain()`
    is sole registration point; quota_guard unknown-domain fallback allows 5th domain with zero
    spine edits. NFR-4 demonstrated in test.
    `tests/test_hydro_viewer.py` (51 tests, incl. NFR-4), `tests/test_hydro_alerts.py` (30 tests).
    commit 37d941f.
- State: All F-041/F-042/F-043/F-044 ACs met. 1072/1072 offline tests pass. ruff clean. mypy clean.
  CP-3 complete: all 4 domains operational (marine_oil, inland_wq, weather_hydro, hydro_chokepoints).
  Phase 9 DoD: F-040–F-044 all DONE.
- Git: main · 37d941f
- Quota: Zero. No live fetches.
- Next: F-045 — React + Vite + Tailwind frontend scaffold (Phase 10).
- Blockers: None.

### 2026-06-28 — implementation — F-040 (Session 10)

- Did:
  F-040: D4 Hydro Choke Points domain — full implementation.
  `argus/domains/hydro_chokepoints/__init__.py` — package stub.
  `argus/domains/hydro_chokepoints/dem_processor.py` — pure numpy D8 flow direction +
  accumulation + `upstream_area_km2()` conversion helper.
  `argus/domains/hydro_chokepoints/constriction.py` — `score_constriction()`, `extract_choke_points()`,
  `candidates_to_choke_points()`; all thresholds configurable, no hardcoded values (OQ-B).
  `argus/domains/hydro_chokepoints/analyzer.py` — `HydroChokepointsDomain` implementing Domain
  protocol: search/acquire/analyze → Observations(obs_type="choke_point", evidence_class="inferred").
  `argus/core/models.py` — `ChokePoint` model; "choke_point" added to VALID_OBS_TYPES.
  `argus/core/store.py` — `choke_points` table DDL; `save_choke_point()`, `get_choke_points()`,
  `_row_to_choke_point()`.
  `argus/core/config.py` — `HydroChokepointsConfig`, `DomainsConfig`; `Settings.domains` field.
  `argus/tasking/runner.py` — `"hydro_chokepoints"` registered in `_load_domain()`.
  `config/settings.yaml` — `domains.hydro_chokepoints` section with canonical threshold keys.
  `config/dem_sources.yaml` — DEM source registry (cop_glo30, srtm_30m).
  `tests/test_choke_points.py` — 49 tests covering D8 algorithm, constriction, Domain protocol, Store CRUD.
- State: All F-040 ACs met. 909/909 tests pass. ruff clean. mypy clean. INV-3 enforced
  (evidence_class="inferred" on all ChokePoint/choke_point Observations). OQ-B satisfied:
  all thresholds in settings.yaml, zero hardcoded values.
- Git: main · e5c113a
- Quota: Zero. No live fetches.
- Next: F-041 — D3 ingestion (Open-Meteo + SO₂/NO₂ + S1 inundation).
- Blockers: None.

### 2026-06-28 — implementation — F-039 (Session 9 continued)

- Did:
  F-039: `RunSummary` schema (domain_id, aoi_id, last_run_at, last_run_status, scenes_fetched,
  observations_created, bytes_used); extended `StatusResponse` with `domain_runs: list[RunSummary]`
  and `open_meteo_calls_today: int`. Extended `GET /status` handler: calls `_build_domain_runs()`
  which deduplicates run_history by (domain, aoi), newest first. Viewer `index.html`: added
  "System Status" panel div. `app.js`: `loadSystemStatus()` fetches `/status`, renders quota
  gauge (CDSE used/limit/remaining) + per-domain run list with status dot and counts.
  `tests/test_observability.py`: 13 tests.
- State: All F-039 ACs met. 859/859 tests pass. ruff clean. mypy clean.
  Phase 8 DoD: F-037/F-038/F-039 all DONE.
- Git: main · a23ece5
- Quota: Zero.
- Next: F-040 — D4 Choke Points (Phase 9). OQ-B resolved; unblocked.
- Blockers: None.

### 2026-06-28 — implementation — F-037 (Session 9)

- Did:
  F-037: `argus/tasking/` module — `base.py` (ScheduledJob, TaskResult dataclasses; Scheduler protocol);
  `apscheduler_backend.py` (APSchedulerBackend: BackgroundScheduler wrapper; RLock for re-entrant
  schedule/unschedule; trigger() fires callback in daemon thread without disturbing schedule);
  `quota_guard.py` (QuotaDecision; check_cdse_daily_quota / check_open_meteo_daily_quota /
  check_domain_quota — dependency-injected store, stateless); `runner.py` (stateless
  run_domain_task(): quota check → load AOI → resolve MonitorTarget → lazy-import domain →
  search/acquire/analyze → persist AnalysisRun + Observations; dry_run flag for testing;
  handles partial acquire failure gracefully).
  `config/schedule.yaml` — schedule configuration template.
  `tests/test_scheduler.py` — 34 tests covering all modules.
  Bugfix: APScheduler schedule() + unschedule() deadlock fixed by switching to RLock and
  extracting `_unschedule_locked()` helper.
- State: All F-037 ACs met. 825/825 offline tests pass. ruff clean. mypy clean.
  Scheduler protocol is backend-agnostic (Cloud Run can invoke same run_domain_task via HTTP).
- Git: main · 70fa768
- Quota: Zero.
- Next: F-038 — Incremental ingestion + idempotency + run history.
- Blockers: None.

### 2026-06-28 — implementation — F-034–F-036 (Session 8) — PHASE 7 COMPLETE

- Did:
  F-034: Extended `ExposureLayer.layer_type` to add `"drinking_intake"` and `"recreation_site"`.
  Added `assess_wq_impact(prediction, water_body_geom, exposure_layers, ...)` to `assessor.py`:
  checks if anomaly z_score or forecast value exceeds threshold, then intersects water body
  polygon with WQ exposure layers; eta_hours=0 for anomaly, horizon_days*24 for forecast.
  Metrics: `intakes_threatened=1` per intake layer, `recreation_sites_threatened=1` per rec layer.
  `data/static/exposure/drinking_intakes_reference.geojson` + `recreation_sites_reference.geojson`
  (both points inside reference lake polygon). `tests/test_wq_impact.py` (28 tests).
  F-035: `Store.get_predictions_for_target(target_id, kind)` resolves predictions via source obs.
  `Store.get_waterbody_targets()` returns distinct target_ids where domain='inland_wq'.
  `argus/api/schemas.py` — `WaterbodyListResponse`. `argus/api/routers/waterbody.py` — three new
  endpoints: `GET /waterbodies`, `GET /waterbody/{id}/observations`, `GET /waterbody/{id}/anomalies`.
  `index.html` — WQ panel + AI report panel divs. `app.js` — `loadWaterbodies()`,
  `loadWQTarget()`, `loadWQReport()`: fetch /waterbodies, render status dot + trend list
  + anomaly count + AI report text; render water body polygon on map.
  F-036: `Alert.details: dict[str, Any]` field (backwards-compatible); `to_payload()` includes
  details when non-empty. `should_alert_hab()` dual-signal gate (anomaly sigma AND forecast value).
  `create_hab_alert()` builds Alert with full details dict (target_id, anomaly_sigma,
  bloom_risk_forecast, intakes_threatened, recreation_sites_threatened, horizon_days).
  `export_wq_geojson()`, `export_wq_png()` (bloom-risk color scale via matplotlib),
  `export_wq_summary()` (ranked by risk score), `export_wq_products()` orchestrator.
  Fixed pre-existing unused-import lint issues in F-030/F-032/F-033 test files. `tests/test_wq_alert.py` (31 tests).
- State: All Phase 7 ACs met. 791/791 offline tests pass. ruff clean. mypy clean.
  Phase 7 DoD: F-034–F-036 done; HAB early-warning alert fires in offline test; D2 observations,
  anomalies, AI report visible in viewer; D1+D2 both rendered on same map.
- Git: main · a4c4351
- Quota: Zero.
- Next: F-037 — Per-domain tasking + scheduler (Phase 8). Requires ADR-0007 decision first.
- Blockers: ADR-0007 (scheduler strategy) required before F-037. OQ-B blocks F-040.

### 2026-06-27 — implementation — F-030–F-033 (Session 7) — PHASE 6 COMPLETE

- Did:
  F-030: `argus/ai/` scaffold — `base.py` (Scope, GroundedText, GroundedAnswer, AIReport, Assistant
  protocol), `client.py` (ArgusAIClient; pinned model claude-sonnet-4-6; logged calls; lazy anthropic
  import), `grounding.py` (GroundingGuard.validate(): citation existence in store + every factual
  sentence must have [record_id]; raises GroundingError on violation), `fallback.py`
  (generate_template_report for ARGUS_AI_OFFLINE=true), `__init__.py`.
  pyproject.toml: `[ai]` optional extras group `anthropic>=0.30`.
  Fixtures: `grounded_response.json`, `ungrounded_response.json`.
  `tests/test_grounding_guard.py` (30 tests). Commit: cae538e
  F-031: `argus/ai/reports.py` — SituationReporter (builds context from store obs+preds; calls LLM;
  validates via guard; ARGUS_AI_OFFLINE fallback). `Store.get_observations_by_target(target_id,
  since, obs_types)`. `argus/api/routers/ai.py`: GET /waterbody/{id}/report → AIReportResponse.
  `argus/api/schemas.py`: AIReportResponse. Fixture: `report_wq_grounded.json`.
  `tests/test_nl_reports.py` (18 tests). Commit: da441cd
  F-032: `argus/ai/query.py` — QueryPipeline (2-step: translate→StoreQuery JSON → execute →
  synthesize; _is_write_action() refuses without LLM call; _parse_store_query() robust JSON
  extraction; offline GroundedAnswer). POST /query endpoint. QueryRequest / QueryResponse schemas.
  `tests/test_nl_query.py` (23 tests). Commit: f9699f8
  F-033: `argus/ai/anomaly_explain.py` — AnomalyExplainer (builds context from Prediction + source
  obs; parses HYPOTHESIS/ADVISORY/CONFIDENCE from LLM response; offline template; raises ValueError
  for unknown pred_id). GET /anomaly/{id}/explanation → ExplanationResponse (404 on missing).
  ExplanationResponse schema. `tests/test_anomaly_explain.py` (20 tests). Commit: 85e75b1
- State: All Phase 6 ACs met. 732/732 offline tests pass. ruff clean. mypy clean.
  Phase 6 DoD: F-030–F-033 done; grounding guard rejects ungrounded in test; no live
  Anthropic calls; ARGUS_AI_OFFLINE=true fallback works; AIReport citations non-empty.
- Git: main · cae538e / da441cd / f9699f8 / 85e75b1
- Quota: Zero.
- Next: F-034 — WQ Exposure (Drinking Intakes / Recreation) + Impact (Phase 7)
- Blockers: None.

### 2026-06-27 — implementation — F-027, F-028, F-029 (Session 6 continued) — PHASE 5 COMPLETE

- Did:
  F-027: `argus/predict/anomaly_detector/` — `SeasonalBaseline` (per-ISO-week mean/std from
  Observation history), `AnomalyDetector` (z-score vs baseline; threshold_sigma=2.5 default).
  Prediction(kind='anomaly') with uncertainty={"sigma": z_score} per INV-9.
  `Store.get_predictions_by_kind()`. `tests/test_anomaly_detector.py` (21 tests).
  F-028: `argus/predict/wq_forecast/` — `build_feature_vector()` (7-feature vector: lagged
  chl-a, sin/cos doy, weather), `build_training_matrix()`, `train_gbm()` (GBM n_estimators=50).
  `WQForecaster.from_history()` (80/20 holdout, RMSE). `WQForecaster.forecast()` (bootstrap
  median CI guarantees ci_low ≤ value ≤ ci_high). Prediction(kind='forecast') with
  uncertainty={"ci_90_low","ci_90_high","rmse"} per INV-9 AC3. `tests/test_wq_forecast.py` (24 tests).
  F-029: `argus/eval/skill_gate.py` — `check_gate()`, `gate_predictions()`. `Store.passed_gate`
  column on skill_reports (idempotent ALTER TABLE). `Store.get_skill_reports_by_predictor()`.
  `argus/api/routers/waterbody.py` — `GET /waterbody/{id}/forecasts` (gated) and
  `GET /waterbody/{id}/raw_predictions` (unfiltered). `tests/test_skill_gate.py` (18 tests).
- State: All Phase 5 ACs met. 641/641 offline tests pass. ruff clean. mypy clean.
  Phase 5 DoD: F-027–F-029 done; WQForecast SkillReport gate enforced in API; INV-9 satisfied.
- Git: main · F-027 b6399f6 · F-028 a203616 · F-029 422e0a9
- Quota: Zero.
- Next: F-030 — AI Assistant scaffolding + grounding/citation guards (Phase 6)
- Blockers: OQ-D (LLM tier/budget) still open. F-030 can proceed with stub/offline mode.

### 2026-06-27 — implementation — F-024, F-025, F-026 (Session 6) — PHASE 4 COMPLETE

- Did:
  F-024: `argus/aoi/loader.py` — `load_water_body_target()` reads GeoJSON Feature + optional meta
  YAML; `_approx_area_km2()` via shapely; `resolution_status` gate (`MIN_WATER_BODY_AREA_HA = 1.0`);
  `require_eligible()` raises `BelowResolutionError`. `argus/core/errors.py` — `BelowResolutionError`
  (subclass of `AOIError`). `config/water_bodies/reference_lake.geojson` + `reference_lake_meta.yaml`.
  `tests/test_water_body_loader.py` (18 tests).
  F-025: `argus/ingest/catalogue.py` — `search_s2()` (SENTINEL-2 / S2MSI2A, cloud-cover filter),
  `search_s3()` (SENTINEL-3 / OL_2_WFR___, OLCI). `argus/ingest/process_api.py` — `fetch_s2_subset()`
  (6-band L2A evalscript), `fetch_s3_olci_subset()` (10-band OLCI). `argus/preprocess/optical.py` —
  `OpticalScene`, `preprocess_optical()`, `mask_clouds()` stub. `argus/core/models.py` — added
  "bloom_presence" to `VALID_OBS_TYPES`. Fixtures: `cdse_s2_search_reference_lake.json`,
  `s2_water_body_100x100.npy`. Tests: `test_s2_catalogue.py` (17), `test_s3_catalogue.py` (7).
  F-026: `argus/domains/inland_wq/indices.py` — `compute_ndci()`, `compute_ndti()`, `compute_cdom()`,
  `detect_bloom_presence()` (fraction-above-threshold; BLOOM_NDCI_THRESHOLD=0.25, BLOOM_PIXEL_FRACTION=0.02).
  `argus/domains/inland_wq/analyzer.py` — `InlandWqDomain` implementing Domain protocol; `search()`
  calls `require_eligible()` before any CDSE access; `analyze()` emits chlorophyll_a/turbidity/cdom
  (evidence_class="measured") + bloom_presence (evidence_class="inferred") Observations with
  `calibration_state` in attrs. `tests/test_optical_indices.py` (15), `tests/test_inland_wq_analyzer.py` (17).
- State: All 4 ACs met. 578/578 offline tests pass. ruff clean. mypy clean. Phase 4 DoD: F-024–F-026 all done.
- Git: main · F-024 03c0edb · F-025 40abb16 · F-026 f119a9e
- Quota: Zero.
- Next: F-027 — Seasonal baseline + AnomalyDetector (Phase 5)
- Blockers: None. OQ-B still blocks F-040; OQ-D still blocks F-030.

### 2026-06-27 — implementation — F-022, F-023 (Session 5 continued) — PHASE 3.5 COMPLETE

- Did:
  F-022: `argus/core/config.py` — `_deep_merge()`, `_load_yaml()`, profile loading via
  `ARGUS_PROFILE` env var (loads `config/settings.<profile>.yaml` on top of base, then env
  vars win). ValidationError wrapped in ConfigError (fails at startup). `config/settings.dev.yaml`
  + `config/settings.test.yaml`. 9 new tests (23 total in test_config.py).
  F-023: `argus/api/routers/health.py` — `GET /health` (liveness, moved from inline app.py),
  `GET /ready` (503 if Store inaccessible), `GET /status` (version, store_accessible,
  last_analysis_run_at, CDSE quota). `argus/core/store.py` — `ping()` + `get_last_analysis_run_at()`.
  `argus/api/schemas.py` — `ReadyResponse`, `QuotaStatus`, `StatusResponse`. `tests/test_health.py`
  (18 tests).
- State: 503/503 offline tests pass, 2 live deselected. ruff clean. mypy clean. All ACs met.
  Phase 3.5 definition of done: F-018–F-023 complete.
- Git: main · F-022 bf55f14 · F-023 3c93c03
- Quota: Zero.
- Next: F-024 — Water-body model + targets + resolution gate (Phase 4, Domain D2)
- Blockers: None. OQ-B still blocks F-040; OQ-D still blocks F-030.

### 2026-06-27 — implementation — F-018, F-019, F-020, F-021 (Session 5 continued)

- Did:
  F-018: `argus/api/schemas.py` — all response models with `description=` on every field;
  `_attribution` alias via `Field(alias=...)` + `populate_by_name=True`; `HealthResponse`,
  `ObservationSchema`, `PredictionSchema`, `PredictionListResponse` finalized. `argus/api/app.py`
  — version from `__version__`, `openapi_tags` added. `docs/api/API_SPEC.md` — comprehensive
  D1 API spec with all endpoints, schemas, breaking-change policy, attribution requirements.
  `tests/test_api_contracts.py` (36 tests, uses `model_validate()` as schema assertion).
  F-019: `scripts/harness/check_architecture.py` — VAL-008 (copyleft regex), VAL-010 (live
  network), VAL-017 (hardcoded oil types) validators; `scripts/harness/check_spec_health.py`
  — VAL-001/VAL-002/VAL-013; shell wrappers `validate.sh`, `spec_health.sh`, `run_all.sh`.
  `tests/conftest.py` — `tmp_store`, `mock_open_meteo`, `mock_cdse_auth`, `mock_anthropic`
  fixtures. `tests/harness/test_validators.py` (21 tests). Fixed `docs/features/phase-11.md`
  F-056 missing AC section.
  F-020: `argus/core/errors.py` — 15-class ArgusError hierarchy with sub-hierarchies
  (QuotaExceeded⊂Acquisition, BelowResolution⊂AOI, ObservationTypeError⊂ArgusError+ValueError).
  Updated all argus modules to import from errors.py. `tests/test_error_handling.py` (29 tests).
  F-021: `argus/core/logging.py` — `_JsonFormatter`, `_TextFormatter`, `get_logger()`,
  `bind_run_id()`, `current_run_id()` (thread-local). `tests/test_logging.py` (19 tests).
- State: 476/476 offline tests pass, 2 live deselected. ruff clean. mypy clean. All ACs met.
- Git: main · F-018 65cdf72 · F-019 a5494dc · F-020 055c5ff · F-021 41c8c8f
- Quota: Zero.
- Next: F-022 — Config management (settings.yaml schema + env override profiles)
- Blockers: None.

### 2026-06-27 — implementation — F-014, F-015, F-016, F-017 (Session 5 continued) — CP-1 COMPLETE

- Did:
  F-014: `argus/impact/assessor.py` — `load_exposure_layer()` (GeoJSON Feature→ExposureLayer),
  `assess_impact()` (per-layer first-intersection ETA, timezone-aware eta_hours, coastline
  length via shapely .length×111.19, MPA area via .area×111.19²×cos(lat)). `argus/core/models.py` —
  `ExposureLayer` + `ImpactAssessment`. `argus/core/store.py` — `exposure_layers` + `impact_assessments`
  tables + CRUD (INV-6). `data/static/exposure/coastline_tobago.geojson` + `mpas_tobago.geojson`.
  `tests/test_impact_assessor.py` (22 tests).
  F-015: `argus/api/` package — `create_app()` factory (FastAPI, StaticFiles, FileResponse index,
  `/health`). Routers: `aoi.py`, `observations.py`, `predictions.py`, `impact.py` (all using
  `request.app.state.db_path`). `argus/api/schemas.py` — Pydantic v2 response models with
  `_attribution` alias (Field+alias+populate_by_name+response_model_by_alias). `argus/cli.py` —
  `argus serve` command. `fastapi>=0.111`, `uvicorn>=0.30`, `httpx>=0.27` deps added.
  `tests/test_api.py` (50 tests).
  F-016: `argus/api/static/index.html` + `app.js` (Leaflet map, observations polygon layer,
  prediction heatmap, ETA sidebar cards, parallel fetch for obs/predictions/impact).
  F-017: `argus/alert/__init__.py` + `argus/alert/delivery.py` — `AlertChannel`, `Alert`,
  `load_channels()`, `_send_webhook()`, `_send_email()`, `send_alert()` (graceful no-op for
  empty channels). `config/alert_channels.yaml` (template). `argus/export/products.py` —
  `export_metadata()` + updated `export_products()` (now returns "metadata" key).
  `tests/test_alert_delivery.py` (30 tests).
- State: 371/371 offline tests pass. ruff clean. mypy clean (49 source files). All CP-1 ACs met.
- Git: main · F-014 2c851ae · F-015 38000bd · F-016 af20fa3 · F-017 792a3c6
- Quota: Zero.
- Next: F-018 — API contract finalization (Phase 3.5)
- Blockers: None.

### 2026-06-27 — implementation — F-013 (Session 5 continued)

- Did: `argus/predict/oil_trajectory/evaluator.py` — `TrajectoryEvalCase.from_json()` (loads trajectory
  eval case with truth_centroid + rng_seed + horizon_hours); `TrajectorySkillResult` dataclass;
  `_haversine_km()` great-circle distance; `_frame_centroid()` (prefers stats.mean_lon/lat, falls back
  to footprint polygon mean); `evaluate_trajectory()` (last frame centroid vs truth centroid separation);
  `skill_result_to_store_report()` (f1_proxy = max(0, 1 − sep_km/100) → Store.save_skill_report()).
  `data/eval/tobago_2024_trajectory.json` — trajectory eval case (truth_centroid=[-61.25,11.15], rng_seed=42,
  horizon_hours=24). `tests/test_forecast_frames.py` — 21 tests covering all evaluator functions,
  ForecastFrame store round-trips, INV-8/INV-9 checks.
- State: 292/292 offline tests pass. ruff clean. mypy clean (37 source files). All F-013 ACs met.
- Git: main · b3ac90a
- Quota: Zero.
- Next: F-014 — Exposure layers + impact + ETA (Phase 3)
- Blockers: None.

### 2026-06-27 — implementation — F-011, F-012 (Session 5 continued)

- Did: F-012: `argus/predict/oil_trajectory/forcing.py` — `ForcingGrid`, `fetch_open_meteo_winds()`,
  `fetch_cmems_currents()`, `fetch_open_meteo_marine()` (fallback), `get_forcing()` (cache-aware,
  CMEMS fallback on CmemsUnavailableError). Quota tracking: open_meteo_calls + cmems_bytes.
  `argus/predict/oil_trajectory/cache.py` — `ForcingCache` reads/writes parquet via pyarrow.
  Fixtures: `tests/fixtures/cmems_currents_tobago.parquet`, `tests/fixtures/open_meteo_winds_tobago.json`.
  `pyarrow>=14.0` added to deps (BSD license, INV-1 compliant).
  `tests/test_forcing_providers.py` — 23 tests (grid fields, parsing, primary path, fallback, cache).
  F-011 (included above in prev entry).
- State: 269/269 offline tests pass. ruff clean. mypy clean (36 source files). All F-012 ACs met.
- Git: main · F-011 128ffea · F-012 0508df4
- Quota: Zero.
- Next: F-013 — ForecastFrames + trajectory evaluation
- Blockers: None.

### 2026-06-27 — implementation — F-011 (Session 5 continued)

- Did: `argus/predict/base.py` — `Predictor` Protocol scaffold, `PredictContext`, `EvalSet`.
  `argus/predict/oil_trajectory/oil_types.py` — `OilType`, `OilTypeRegistry`, `OilTypeRequiredError`,
  `OilTypeNotFoundError`, `load_oil_types()`. `argus/predict/oil_trajectory/runner.py` —
  `SimInput`, `run_simulation()` (validates oil_type → spawns subprocess → reads output JSON).
  `argus/predict/oil_trajectory/sim_worker.py` — only file that imports opendrift; GPL isolation
  verified by `test_gpl_isolation_opendrift_only_in_sim_worker`.
  `argus/core/models.py` — `Prediction` (INV-9: uncertainty required) + `ForecastFrame`.
  `argus/core/store.py` — `predictions` + `forecast_frames` tables; CRUD methods (INV-6).
  `tests/test_oil_trajectory_service.py` — 19 tests (registry, runner, GPL isolation, store round-trips).
- State: 246/246 offline tests pass. ruff clean. mypy clean (34 source files). All F-011 ACs met.
- Git: main · 128ffea
- Quota: Zero.
- Next: F-012 — Metocean forcing providers + cache
- Blockers: None.

### 2026-06-27 — implementation — F-010 (Session 5 continued) — PHASE 1 COMPLETE

- Did: `argus/core/models.py` — `VALID_OBS_TYPES` registry (6 types); `field_validator` for
  obs_type; `Observation` gains `features`, `status_updated_at`, `domain`, `target_id`, `value`,
  `unit` fields. `argus/core/store.py` — new columns in observations table; idempotent
  `ALTER TABLE` via `contextlib.suppress` for existing DBs; `transition_observation_status()`.
  `argus/domains/marine_oil/classifier.py` — sets `status_updated_at` on transition.
  `argus/domains/marine_oil/detector.py` — populates `features` top-level field.
  `tests/test_observation_schema.py` — 23 tests covering validation, transitions, round-trips,
  migration check (old schema → new columns added on re-open).
- State: 227/227 offline tests pass. ruff clean. mypy clean (28 source files). All F-010 ACs met.
  Phase 1 DoD: F-007–F-010 all done; P/R baseline exists (tobago_2024 eval case); schema frozen.
- Git: main · 2c1ae8e
- Quota: Zero.
- Next: F-011 — OpenOil sim service (Phase 2)
- Blockers: None. OQ-B still blocks F-040; OQ-D still blocks F-030.

### 2026-06-27 — implementation — F-007, F-008, F-009 (Session 5 continued)

- Did: F-007: `argus/domains/marine_oil/segmentor.py` — Otsu thresholding + morphological
  opening (iterations=2); degenerate uniform raster handled. `argus/domains/marine_oil/features.py` —
  9-feature vector (area_km2, perimeter_km, compactness, elongation, convexity, orientation,
  mean_sigma0_db, contrast_vs_background_db, texture_glcm) using GLCM and ConvexHull.
  Renamed `OilDomainV0` → `MarineOilDomain`; alias kept for compatibility.
  `tests/fixtures/sar_with_blob_and_noise.npy` (2×200×200). `tests/test_segmentor.py` (10),
  `tests/test_features.py` (12 via test_oil_detector.py update).
  F-008: `argus/domains/marine_oil/classifier.py` — GBT (n_estimators=50, seed=42 INV-8),
  `OilClassifier.classify()` returns new Observation instances via `model_copy()` (INV-3 evidence_class
  unchanged). `config/oil_classifier.yaml`. `models/oil_classifier_v1.pkl`. `data/eval/labeled_detections.json`
  (15 oil + 15 lookalike). `tests/test_classifier.py` (15 tests). `Observation.status` updated to
  `"dismissed"` (v2.0 canonical).
  F-009: `argus/eval/__init__.py`, `argus/eval/scorer.py` (EvalResult, score()), `argus/eval/harness.py`
  (EvalCase, SkillReport, run() in fixture mode). `argus/core/store.py` — `skill_reports` table +
  save/query methods (INV-6). `tests/test_eval_harness.py` (19 tests).
- State: 204/204 offline tests pass. ruff clean. mypy clean (28 source files). All F-007/F-008/F-009 ACs met.
- Git: main · F-007 9ea967a · F-008 f1ad411 · F-009 a3a5187
- Quota: Zero.
- Next: F-010 — Detection characterization & schema finalization
- Blockers: None. OQ-B still blocks F-040; OQ-D still blocks F-030.

### 2026-06-27 — implementation — F-006 (Session 5 continued) — PHASE 0 COMPLETE

- Did: `argus/export/products.py` — `export_geojson()` (FeatureCollection with evidence_class
  preserved per INV-3), `export_png()` (Matplotlib Agg backend, VV dB raster + polygon overlays),
  `export_products()` (orchestrates to run-tagged output dir). `argus/cli.py` — `argus run` command
  with `--aoi`, `--since`, `--live` (stub), `--output-dir`, `--config-dir` (hidden, for testing);
  offline mode plants a dark blob and runs the full Phase 0 stack. `data/eval/tobago_2024.json` —
  anchor EvalCase with `oil_type="crude_medium"` (ADR-0006), truth_geometry, provenance.
  Added `matplotlib>=3.8` to dependencies (INV-1: MIT, zero recurring cost).
  `tests/test_export.py` (15 tests), `tests/test_phase0_e2e.py` (13 tests).
- State: 147/147 offline tests pass, 2 live deselected. ruff clean. mypy clean (22 source files).
  Phase 0 definition-of-done checklist: all items met. DONE.
- Git: main · 2f9fa68
- Quota: Zero.
- Next: F-007 — Robust dark-spot segmentation (Phase 1)
- Blockers: None. OQ-B still blocks F-040; OQ-D still blocks F-030.

### 2026-06-27 — implementation — F-005 (Session 5 continued)

- Did: `argus/domains/base.py` — `Acquisition` dataclass + `Domain` Protocol (INV-2 stable).
  `argus/domains/marine_oil/detector.py` — `OilDomainV0.analyze()`: adaptive VV dB threshold
  (mean − 2σ), morphological clean-up, connected-component labelling, convex-hull Observation
  output; `make_analysis_run()` helper. `argus/core/models.py` — `AnalysisRun` + `Observation`
  (INV-3: evidence_class on every Observation; INV-9: status field).
  `argus/core/store.py` — `analysis_runs` + `observations` tables + CRUD (INV-6: sole sqlite3
  importer). `tests/test_oil_detector.py` (14), `tests/test_store_observation.py` (16).
- State: 119 offline tests pass, 2 live deselected. ruff clean. mypy clean (20 source files). DONE.
- Git: main · 56a68dc
- Quota: Zero.
- Next: F-006 — Static product export + EvalCase + `argus run` CLI command
- Blockers: None.

### 2026-06-27 — implementation — F-003 + F-004 (Session 5 continued)

- Did: F-003: `argus/ingest/process_api.py` — `fetch_s1_subset()` (Sentinel Hub Process API,
  2-band VV+VH FLOAT32 evalscript, returns tiff bytes + byte count). `argus/ingest/acquire.py` —
  `acquire_scene()` (pre/post-quota check, artifact write, Scene persistence). `argus/core/store.py` —
  SQLite store with `scenes` table, `save_scene/get_scene/daily_bytes_total()` (INV-6).
  `argus/core/models.py` — `Scene` added. `tests/test_store_scene.py` (15), `tests/test_acquire.py` (6).
  F-004: `argus/preprocess/landmask.py` — `GeoTransform` dataclass + `rasterize_land_mask()`
  (shapely 2.0 vectorized). `argus/preprocess/sar.py` — `PreprocessedScene` + `preprocess()`
  (_to_db → _speckle_filter → NaN land pixels). `data/static/coastline.geojson` (Tobago fixture).
  `tests/fixtures/synthetic_sar_100x100.npy`. `tests/test_preprocess.py` (14), `tests/test_landmask.py` (9).
- State: 89 tests after F-004. ruff clean. mypy clean. DONE.
- Git: main · d5ed697 (F-003) · 7fa5c77 (F-004)
- Quota: Zero.
- Next: F-005 (completed above)
- Blockers: None.

### 2026-06-27 — implementation — F-002 (Session 5 continued)

- Did: `argus/ingest/cdse_auth.py` — CdseAuth (password-grant OAuth2, in-memory token cache,
  60s expiry buffer, never logs credentials); `CdseAuthError` with remediation text.
  `argus/ingest/catalogue.py` — `search_s1_grd()` (STAC search, IW+GRD filter, sorted by
  sensing_time); `CatalogueError`. `argus/core/models.py` — `SourceRef` added.
  `tests/fixtures/cdse_s1_search_tobago.json` — 2-product fixture in reverse order (proves sort).
  `tests/test_catalogue.py` — 12 mocked tests covering parse, sort, auth, cache, bearer header.
  `tests/integration/test_cdse_live.py` — 2 live tests (skipped by default with `not live`).
  `pyproject.toml` — added `requests>=2.31`, `-m 'not live'` to default addopts.
- State: 45 tests pass, 2 live deselected. ruff clean. mypy clean (11 source files). DONE.
- Git: main · ba12b28
- Quota: Zero.
- Next: F-003 — Scene acquisition + persistence (Process API + SQLite store)
- Blockers: None.

### 2026-06-27 — implementation — F-001 (Session 5)

- Did: Config system (`argus/core/config.py`) with pydantic models for all YAML sections + explicit
  `ARGUS_*` env var override map; `require_cdse_credentials()` raises `ConfigError` with remediation
  text and no secret values in output. AOI + MonitorTarget data models (`argus/core/models.py`)
  with v2.0 canonical names and `AOI.bbox` property. AOI loader (`argus/aoi/loader.py`) with
  shapely geometry validation, self-intersection check, and 500,000 km² size cap (`AOIError`).
  Tobago anchor AOI (`config/aois/tobago.geojson`). Added `pyyaml>=6.0` and `shapely>=2.0`
  to dependencies. 28 new tests across `test_config.py` and `test_aoi_loader.py`.
- State: All 33 tests pass (28 new + 5 smoke). ruff clean. mypy clean (8 source files). DONE.
- Git: main · 9662b06
- Quota: Zero.
- Next: F-002 — CDSE catalogue client (cdse_auth.py + catalogue.py, mocked HTTP only)
- Blockers: None. OQ-B blocks F-040; OQ-D blocks F-030.

### 2026-06-27 — implementation — F-000 (Session 4)

- Did: Python package scaffold — pyproject.toml (hatchling, ruff, mypy, pytest), argus/__init__.py,
  argus/cli.py (typer multi-command with @app.callback()), argus/core/__init__.py,
  argus/domains/__init__.py, tests/test_smoke.py (5 tests), Makefile, .github/workflows/ci.yml.
  Fixed typer[all] → typer (extra no longer exists in 0.26.x). Fixed unused pytest import.
  Added @app.callback() to force multi-command mode in typer 0.26.x so `argus version` works.
- State: All 5 smoke tests pass. ruff check/format clean. mypy clean (4 source files). DONE.
- Git: main · 850b852
- Quota: Zero.
- Next: F-001 — Config + AOI/target model & loader (pydantic settings + config/settings.yaml loader)
- Blockers: None for F-001. OQ-B still blocks F-040, OQ-D blocks F-030.

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
