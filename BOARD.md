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
