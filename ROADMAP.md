# Argus — Feature Roadmap

- **Status:** v2.1 (full Environmental Intelligence Platform)
- **Last updated:** 2026-06-27
- **Supersedes:** v2.0 (two-tier MVP model — RETIRED per ADR-0005)
- **Related:** [`docs/product/PRD.md`](docs/product/PRD.md)
  · [`docs/architecture/ARCHITECTURE.md`](docs/architecture/ARCHITECTURE.md)
  · [`docs/adr/ADR-0005-mvp-redefinition.md`](docs/adr/ADR-0005-mvp-redefinition.md)
  · [`BOARD.md`](BOARD.md)

**MVP = CP-4 (Phase 11 complete, Josh sign-off). No other milestone is MVP.**

"Vertical-Slice MVP" and "Platform MVP" are retired terms. There are 4 internal checkpoints
(CP-1 through CP-4) for tracking progress, but only CP-4 constitutes the MVP.

Features are additive, independently buildable slices with clearly owned files.
**P0** = MVP-critical · **P1** = post-MVP or parallel.

---

## Phase 0 — Foundation & Spike (D1 Oil) *(P0)*

Prove the spine end-to-end on one curated spill.
Detailed specs: [`docs/features/phase-0.md`](docs/features/phase-0.md)

| ID | Feature | Maps to |
|---|---|---|
| F-000 | Repo & tooling scaffold | NFR-2 |
| F-001 | Config + AOI/target model & loader | FR-1 |
| F-002 | CDSE catalogue client (auth + STAC/OData) | FR-2 |
| F-003 | Scene acquisition (Process-API subset) + persistence | FR-2, FR-3 |
| F-004 | SAR preprocessing (masked σ⁰ dB) | FR-4 |
| F-005 | Naive dark-spot detector + Observation(obs_type="oil_slick") | FR-4, FR-3 |
| F-006 | Static product export (GeoJSON+PNG) — spike close | FR-19 (partial) |

## Phase 1 — Detection Vertical (Oil) *(P0)*

Detailed specs: [`docs/features/phase-1.md`](docs/features/phase-1.md)

| ID | Feature | Maps to |
|---|---|---|
| F-007 | Robust dark-spot segmentation + features | FR-4 |
| F-008 | Look-alike rejection + confidence | FR-4 |
| F-009 | Eval harness + labeled dataset + P/R report | §9 metrics |
| F-010 | Detection characterization & schema finalize | FR-3 |

## Phase 2 — Simulation Vertical (Oil) *(P0)*

Detailed specs: [`docs/features/phase-2.md`](docs/features/phase-2.md)

| ID | Feature | Maps to |
|---|---|---|
| F-011 | OpenOil sim service (isolated subprocess) + seeding | FR-8 |
| F-012 | Metocean forcing providers + caching + fallback | FR-8 |
| F-013 | ForecastFrames + trajectory eval | FR-8, §9 |

## Phase 3 — Impact, Delivery & Viewer (Oil) *(P0)* — CP-1

Detailed specs: [`docs/features/phase-3.md`](docs/features/phase-3.md)

| ID | Feature | Maps to |
|---|---|---|
| F-014 | Exposure layers + impact assessment + ETA | FR-16 |
| F-015 | FastAPI service | FR-17 |
| F-016 | Web viewer (detection + forecast + impact) | FR-18 |
| F-017 | Alert delivery + product export — **CP-1 close** | FR-19 |

## Phase 3.5 — Foundation Hardening *(P0)*

Detailed specs: [`docs/features/phase-3.5.md`](docs/features/phase-3.5.md)

Hardens the pipeline before adding further domains.

| ID | Feature | Maps to |
|---|---|---|
| F-018 | API contract finalization (OpenAPI spec + versioning) | NFR-2 |
| F-019 | Integration test framework + harness scripts | NFR-3, NFR-6 |
| F-020 | Structured error handling (error catalog + codes) | NFR-2 |
| F-021 | Structured logging (JSON format + trace IDs) | NFR-6 |
| F-022 | Config management (settings.yaml schema + env override) | NFR-2 |
| F-023 | Health checks + readiness endpoints | NFR-6 |

## Phase 4 — Domain D2: Inland Water Quality *(P0)*

First plug-in domain on the generalized spine.
Detailed specs: [`docs/features/phase-4.md`](docs/features/phase-4.md)

| ID | Feature | Maps to | Notes |
|---|---|---|---|
| F-024 | Water-body model + monitor targets + resolution gate | FR-1, §6 | below_resolution policy |
| F-025 | Sentinel-2/3 optical ingestion | FR-2 | reuses ingestion patterns |
| F-026 | `inland_wq` analyzer: chl-a/turbidity/CDOM/temp + calibration state | FR-5 | measured-proxy tagging (NFR-8) |

## Phase 5 — Prediction Engine: Water Quality *(P0)*

Detailed specs: [`docs/features/phase-5.md`](docs/features/phase-5.md)

| ID | Feature | Maps to | Notes |
|---|---|---|---|
| F-027 | Per-water-body seasonal baseline + AnomalyDetector | FR-10 | early pollution/discharge warning |
| F-028 | WaterQualityForecast (n-day bloom-risk + CI) | FR-9 | Open-Meteo history as drivers |
| F-029 | Predictor interface + validation/skill gate | FR-12 | beats persistence baseline |

## Phase 6 — AI Layer *(P0)*

Detailed specs: [`docs/features/phase-6.md`](docs/features/phase-6.md)

| ID | Feature | Maps to | Notes |
|---|---|---|---|
| F-030 | Assistant scaffolding + Anthropic client + grounding guards | FR-13–15, NFR-9 | no invented values |
| F-031 | NL situation reports (grounded, every claim cited) | FR-13 | per water body / district |
| F-032 | NL query (text → store query → grounded answer; read-only) | FR-14 | OQ-E resolved: read-only |
| F-033 | Anomaly explanation / triage (advisory, human-in-the-loop) | FR-15 | labels confidence |

## Phase 7 — Platform Integration *(P0)* — CP-2

Detailed specs: [`docs/features/phase-7.md`](docs/features/phase-7.md)

| ID | Feature | Maps to | Notes |
|---|---|---|---|
| F-034 | WQ exposure (drinking intakes / recreation) + impact | FR-16 | |
| F-035 | Viewer + API extended to D2 (trends, anomalies, forecasts, AI report) | FR-17, FR-18 | |
| F-036 | Alerting + products for D2 — **CP-2 close** | FR-19 | HAB early-warning alert |

## Phase 8 — Automation & Scheduling *(P1)*

ADR-0007 (scheduler) must be written and approved before F-037 starts.
Detailed specs: [`docs/features/phase-8.md`](docs/features/phase-8.md)

| ID | Feature | Maps to | Notes |
|---|---|---|---|
| F-037 | Per-domain tasking + scheduler (quota/call-aware) | FR-20 | ADR-0007 required first |
| F-038 | Incremental ingestion, idempotency, run history | FR-20 | |
| F-039 | Observability (metrics + run dashboard) | NFR-6 | |

## Phase 9 — Domains D3 (weather/hydro) & D4 (choke points) *(P1)* — CP-3

F-040 is BLOCKED on OQ-B (choke-point definition).
Detailed specs: [`docs/features/phase-9.md`](docs/features/phase-9.md)

| ID | Feature | Maps to | Notes |
|---|---|---|---|
| F-040 | D4 choke points: DEM flow-accumulation → drainage + choke nodes | FR-7 | BLOCKED: OQ-B |
| F-041 | D3 ingestion: Open-Meteo + SO₂/NO₂ + S1 inundation | FR-6 | |
| F-042 | FloodRisk predictor @ choke points + hydro exposure/impact | FR-11, FR-16 | risk, not deterministic |
| F-043 | AcidDepositionRisk index (modeled, labeled — never a measurement) | FR-11, §6 | |
| F-044 | Hydro viewer + alerting + generalization pass — **CP-3 close** | FR-18, NFR-4 | |

## Phase 10 — Production Dashboard *(P0)*

React + Vite + Tailwind unified dashboard. Replaces the per-domain Leaflet viewers.
Detailed specs: [`docs/features/phase-10.md`](docs/features/phase-10.md)

| ID | Feature | Maps to |
|---|---|---|
| F-045 | React + Vite + Tailwind frontend scaffold | FR-18 |
| F-046 | Overview dashboard (system health, all domains) | FR-18 |
| F-047 | WQ monitoring panel (trends, anomalies, forecasts) | FR-5, FR-10 |
| F-048 | Hazard prediction panel (trajectory player, flood risk) | FR-8, FR-11 |
| F-049 | AI assistant interface with citation viewer | FR-13–15 |
| F-050 | Admin panel (AOI/target management, config) | FR-1 |
| F-051 | Export + reporting UI (PDF/GeoJSON/CSV) | FR-19 |

## Phase 11 — System Validation & MVP Sign-off *(P0)* — CP-4 = MVP

Detailed specs: [`docs/features/phase-11.md`](docs/features/phase-11.md)

| ID | Feature | Maps to |
|---|---|---|
| F-052 | End-to-end integration tests (all 4 domains) | NFR-3 |
| F-053 | Performance profiling (< 10min/AOI target) | NFR-3 |
| F-054 | Documentation finalization (USER_GUIDE, API_SPEC, DEPLOYMENT) | NFR-2 |
| F-055 | Demo dataset preparation (all 4 domain eval cases) | §9 metrics |
| F-056 | MVP validation checklist + Josh sign-off — **CP-4 = MVP** | PRD §MVP |

---

## Critical Path

```
Phase 0─1─2─3 (D1 oil) ──────────────────────────────────────────────────────▶ CP-1 (F-017)
                │
Phase 3.5 (hardening) ──────────────────────────────────────────────────────▶ (F-023)
                │
Phase 4 (D2 WQ) ─ Phase 5 (prediction) ─ Phase 6 (AI) ─ Phase 7 ──────────▶ CP-2 (F-036)
                │
Phase 8 (automation) ─ Phase 9 (D3+D4) ────────────────────────────────────▶ CP-3 (F-044)
                │
Phase 10 (production UI) ─ Phase 11 (validation + sign-off) ───────────────▶ CP-4 = MVP
```

## Slicing Principles (Every Feature)

1. **Additive** — adds capability without breaking earlier tests.
2. **Owned files** — each task lists files it creates/edits; no overlapping ownership in a phase.
3. **Domain-respecting** — domain/predictor changes go behind the `Domain`/`Predictor`/`Assistant`
   interfaces; the spine stays domain-agnostic (INV-2/NFR-4).
4. **Honest** — observations tagged measured/modeled/inferred; AI output record-cited (INV-3/INV-4).
5. **Demoable end state** — a test, file, rendered map, metric, or grounded report.
6. **Quota/call-aware** — prefer subsets; budget CDSE transfer + Open-Meteo calls (QUOTAS.md).
7. **Zero recurring cost** — every feature must satisfy INV-1; verify at implementation.
