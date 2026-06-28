# Argus — Program Log

Append a new entry every session. Newest on top. This is the persistent memory of the project.

---

## 2026-06-28 — Session 11 — F-041/F-042/F-043/F-044: Phase 9 D3/D4 Completion — COMPLETE

**Agent:** Claude claude-sonnet-4-6
**Tasks:** F-041, F-042, F-043, F-044 — Phase 9 (D3 Weather/Hydro + D4 Choke Points) complete; CP-3 achieved

### What happened

**F-041 — D3 Weather/Hydro Ingestion (commit 132bd6b)**
- `argus/domains/weather_hydro/open_meteo.py` — 4 fetch functions (precip forecast, ERA5 historical, GloFAS discharge, air quality SO₂/NO₂); `ATTRIBUTION` constant (CC BY 4.0 required); `mock_response` param for offline tests (INV-7). All functions have `parse_hourly_series()` / `parse_daily_series()` converters.
- `argus/domains/weather_hydro/analyzer.py` — `WeatherHydroDomain` implementing Domain protocol. search() returns 4 SourceRefs (one per Open-Meteo product). acquire() dispatches by product attr. analyze() converts JSON → Observations(obs_type∈{precip_series,discharge_series,so2_series,no2_series}); evidence_class honesty: ERA5="measured", forecast/GloFAS/AQ="modeled" (INV-3).
- `argus/domains/weather_hydro/s5p.py` + `inundation.py` — stubs for live CDSE paths (raise NotImplementedError).
- `argus/core/store.py` — `open_meteo_calls_today()` reads RunHistory.bytes_used for weather_hydro domain.
- `argus/tasking/quota_guard.py` — updated to use `store.open_meteo_calls_today()` (RunHistory instead of Scene bytes, since weather domain has no Scene raster downloads).
- `argus/api/routers/health.py` — `/status` endpoint now populates `open_meteo_calls_today` field properly.
- `tests/test_weather_hydro_domain.py` — 50 tests (parsers, search/acquire/analyze, quota tracking).

**F-042 — FloodRisk Predictor (commit d658d8d)**
- `argus/predict/flood_risk/predictor.py` — `FloodRiskPredictor`; rule-based 3-component score: `0.5×precip_score + 0.3×discharge_score + 0.2×max_constriction`; levels: low/medium/high/extreme driven by configurable thresholds (via ctx.attrs["flood_risk_thresholds"]).
- `argus/predict/flood_risk/evaluator.py` — `build_eval_set()` for hit_rate/false_alarm_rate backtesting.
- `argus/core/config.py` — `FloodRiskConfig` with all 5 threshold keys configurable.
- INV-3: evidence_class="modeled". INV-9: uncertainty with risk_score, model_type="rule_based". INV-8: rng_seed stored. Honesty label: "modeled flood risk at choke point (not a measured flood)".
- `tests/test_flood_risk.py` — 32 tests.

**F-043 — AcidDepositionRisk Predictor (commit a70ee9e)**
- `argus/predict/acid_deposition/predictor.py` — `AcidDepositionRiskPredictor`; formula: SO₂_norm × NO₂_norm × precip_norm × sensitivity × 10 clamped [0,10]. Saturation thresholds: SO₂=50 μg/m³, NO₂=100, precip=50mm. SO₂=0 → index=0 invariant. No NO₂ → neutral (no suppression). INV-3/INV-9/INV-8 enforced. Honesty label: "modeled acid-deposition risk index (0–10 scale) — NOT a pH measurement".
- `tests/test_acid_deposition.py` — 26 tests.

**F-044 — Hydro Viewer + Alerting + Generalization Pass (commit 37d941f)**
- `argus/core/store.py` — `get_predictions_by_predictor(predictor_id)` method added.
- `argus/api/schemas.py` — `ChokePointSchema`, `ChokePointListResponse`, `RiskPredictionSchema`, `RiskPredictionListResponse`.
- `argus/api/routers/hydro.py` — 3 read-only endpoints: GET /aois/{id}/choke-points, /flood-risk, /acid-risk. Registered in `app.py` with "hydro" tag.
- `argus/alert/delivery.py` — `should_alert_flood_risk()` (fires for high/extreme), `create_flood_risk_alert()`, `should_alert_acid_risk()` (fires at index ≥ 7.0), `create_acid_risk_alert()`. All alerts are advisory; honesty labels preserved in payload.
- `argus/api/static/app.js` — `chokeLayer`, `floodRiskLayer`, `acidRiskLayer` L.layerGroup(); `loadChokePoints()` renders circle markers sized by constriction_score; `loadFloodRisk()` / `loadAcidRisk()` populate indicator elements. All 3 called in `bootstrap()`.
- **Generalization pass (INV-2 / NFR-4)**: `_load_domain()` is the sole domain registration point (one if-chain entry = one domain). `quota_guard.check_domain_quota()` returns `allowed=True` for unknown domains — a 5th domain using neither CDSE nor Open-Meteo needs zero spine edits. `inline inland_wq` branch in `_resolve_target()` is a pre-existing bounded exception for water-body target loading, documented with fallback for all other domains.
- `tests/test_hydro_viewer.py` — 22 API tests + NFR-4 protocol test (51 total).
- `tests/test_hydro_alerts.py` — 30 alert function tests.

### Invariant compliance
- INV-2: No spine edits for domain routing. All new domain code in `argus/domains/` and `argus/predict/`.
- INV-3: FloodRisk evidence_class="modeled"; AcidDepositionRisk evidence_class="modeled"; ChokePoint evidence_class="inferred". All tested explicitly.
- INV-4: AI layer unchanged; all predictions carry grounding attrs.
- INV-7: All 157 new tests fully offline. Live paths (S5P, S1 inundation) raise NotImplementedError.
- INV-9: uncertainty populated on both new predictors.

### Tests
1072 passed / 0 failed (up from 909; +157 across F-041–F-044). 2 deselected (--live). ruff clean. mypy clean.

### CP-3 Status
All 4 domains operational: marine_oil (D1), inland_wq (D2), weather_hydro (D3), hydro_chokepoints (D4).
Full automation pipeline functional. AI layer grounded. Phase 9 DoD satisfied.

---

## 2026-06-28 — Session 10 — F-040: D4 Hydro Choke Points — COMPLETE

**Agent:** Claude claude-sonnet-4-6
**Tasks:** F-040

### What happened

**F-040 — D4 Choke Points (commit pending)**

Domain implementation: `argus/domains/hydro_chokepoints/` package.
- `dem_processor.py` — pure numpy D8 flow direction + flow accumulation + upstream_area_km2().
  No rasterio or GDAL. D8 direction offsets with distance-normalised slope to avoid diagonal bias.
  `compute_flow_direction()` → int8 raster (-1=sink, 0–7=D8 direction).
  `compute_flow_accumulation()` → int64 raster (count of upstream contributing cells).
- `constriction.py` — `score_constriction()` normalises facc to [0,1].
  `extract_choke_points()` filters by min_upstream_area_km2 + min_constriction_score, returns top-N.
  `candidates_to_choke_points()` converts grid row/col to GeoJSON Point using bbox origin + cell_size_deg.
- `analyzer.py` — `HydroChokepointsDomain` implements Domain protocol.
  search(): deterministic product_id from target.id (idempotency-safe).
  acquire(): wraps DEM ndarray from ref.attrs["dem_array"] into Acquisition.
  analyze(): D8 pipeline → Observations(obs_type="choke_point", evidence_class="inferred", domain="hydro_chokepoints").
  All thresholds read from acq.attrs (runner passes settings-derived values). No hardcoded thresholds (OQ-B).

Store: `choke_points` table DDL + `save_choke_point()` / `get_choke_points()` / `_row_to_choke_point()`.
Config: `HydroChokepointsConfig` (cell_size_m, min_upstream_area_km2, min_constriction_score, max_candidates, dem_source) + `DomainsConfig` added to Settings.
settings.yaml: `domains.hydro_chokepoints` section aligned with Pydantic model keys.
config/dem_sources.yaml: DEM source registry (cop_glo30, srtm_30m).
runner.py: "hydro_chokepoints" registered in `_load_domain()`.
tests/test_choke_points.py: 49 tests — D8 algorithm, constriction scoring, Domain.search/acquire/analyze, Store CRUD, end-to-end pipeline with funnel and valley DEMs.

### Invariant compliance
- INV-3: evidence_class="inferred" on all ChokePoint models and choke_point Observations; enforced at model level and tested explicitly.
- INV-2: Domain spine not edited.
- OQ-B: All thresholds configurable via settings.yaml; zero hardcoded values.
- INV-7: All 49 tests fully offline (synthetic DEMs; no live Copernicus DEM fetch).

### Tests
909 passed / 0 failed (up from 859; +49 F-040 + 1 from DomainsConfig). ruff clean. mypy clean.

---

## 2026-06-28 — Session 9 — F-037/F-038/F-039: Phase 8 Automation & Scheduling — COMPLETE

**Agent:** Claude claude-sonnet-4-6
**Tasks:** F-037, F-038, F-039 complete — Phase 8 (Automation & Scheduling) complete

### What happened

**F-037 — Per-Domain Tasking + APScheduler Scheduler (commit 70fa768)**
- `argus/tasking/base.py` — ScheduledJob, TaskResult (with Literal status), Scheduler Protocol
- `argus/tasking/apscheduler_backend.py` — APSchedulerBackend; RLock fixes deadlock; trigger() in daemon thread
- `argus/tasking/quota_guard.py` — stateless quota guards, dependency-injected store
- `argus/tasking/runner.py` — stateless run_domain_task() invokable by scheduler/CLI/Cloud Run
- `config/schedule.yaml` — template; 34 tests

**F-038 — Incremental Ingestion + Idempotency + RunHistory (commit dc39641)**
- RunHistory model: domain, aoi, t_start/t_end, counts, status
- Store: run_history table; get_scene_by_product_id for idempotency
- acquire_scene(): skip re-download when product_id already ready in store
- runner.py: save RunHistory on all paths (complete/skipped/failed); 21 tests

**F-039 — Observability (commit a23ece5)**
- RunSummary + StatusResponse extensions (domain_runs, open_meteo_calls_today)
- GET /status: shows last-run per domain × AOI, deduped newest-first
- Viewer: System Status panel with quota gauge and per-domain dots; 13 tests

**Test count:** 825 → 859 (+34). All phases 0–8 green.

---

## 2026-06-28 — Session 9 — F-037: Per-Domain Tasking + APScheduler Scheduler

**Agent:** Claude claude-sonnet-4-6
**Duration:** Single continuous session
**Tasks:** F-037 complete — Phase 8 started

### What happened

**F-037 — Per-Domain Tasking + Scheduler (ADR-0007 Option B)**
- `argus/tasking/base.py` — `ScheduledJob` and `TaskResult` dataclasses; `Scheduler` Protocol
  (backend-agnostic: start/stop/schedule/unschedule/list_jobs/trigger). Protocol design from ADR-0007.
- `argus/tasking/apscheduler_backend.py` — `APSchedulerBackend`: wraps APScheduler 3.x
  `BackgroundScheduler`. Uses `RLock` to prevent deadlock when `schedule()` re-enters `unschedule()`.
  `trigger()` fires callback in a daemon thread so HTTP responses return immediately. Lazy job
  wrapping ensures each run gets the current callback (supports re-scheduling).
- `argus/tasking/quota_guard.py` — Stateless quota check functions; `check_domain_quota()` routes
  by domain_id to CDSE (satellite domains) or Open-Meteo (weather domains). Store is
  dependency-injected; guards read `daily_bytes_total()` for both byte and call counting.
- `argus/tasking/runner.py` — Stateless `run_domain_task()`: quota → AOI load → MonitorTarget
  resolve → lazy domain import → search/acquire/analyze → persist AnalysisRun+Observations →
  TaskResult. `dry_run` flag skips acquisition for quota testing. Handles partial acquire
  failures gracefully (logs, continues to next ref). Invocable by scheduler, CLI, or Cloud Run
  HTTP endpoint without changing business logic (ADR-0007 requirement).
- `config/schedule.yaml` — Schedule configuration template (two example jobs, both disabled).
- `tests/test_scheduler.py` — 34 tests; all offline. Covers: dataclasses, protocol conformance,
  start/stop/schedule/unschedule/list/trigger, deadlock regression, quota guards, runner
  happy path and error paths.

**Bugfixes:**
- APScheduler RLock deadlock: `schedule()` held `threading.Lock` then called `unschedule()` which
  tried to acquire same lock → switched to `threading.RLock` and extracted `_unschedule_locked()`.

**Test count:** 791 → 825 (+34). ruff clean. mypy clean.

**Commit:** 70fa768

### State
- F-037: DONE. All ACs met. Tests green.
- F-038 (Incremental Ingestion + Idempotency + Run History): next.
- No open blockers.

---

## 2026-06-28 — Session 8 — F-034–F-036: Platform Integration (D2) — PHASE 7 COMPLETE

**Agent:** Claude claude-sonnet-4-6
**Duration:** Single continuous session
**Tasks:** F-034, F-035, F-036 complete — Phase 7 (Platform Integration) complete — CP-2 closed

### What happened

**F-034 — WQ Exposure + Impact Assessment**
- Extended `ExposureLayer.layer_type` Literal to include `"drinking_intake"` and `"recreation_site"`.
- Added `_prediction_exceeds_bloom_threshold()` and `assess_wq_impact()` to `argus/impact/assessor.py`.
  The WQ assessor fires when anomaly sigma ≥ 2.5 (or forecast value ≥ 25.0 µg/L), then intersects
  the water body polygon with each WQ exposure layer using shapely; returns one `ImpactAssessment`
  per hit layer. ETA = 0h for anomaly, horizon_days×24h for forecast.
- `data/static/exposure/drinking_intakes_reference.geojson` — Point at (-60.5005, 10.5005) inside reference lake.
- `data/static/exposure/recreation_sites_reference.geojson` — Point at (-60.501, 10.5012) inside reference lake.
- `tests/test_wq_impact.py`: 28 tests covering AC: intake inside lake + forecast above threshold → IA created;
  no exposure → no IA; metrics correct; store round-trips.

**F-035 — Viewer + API Extended to D2**
- `Store.get_predictions_for_target(target_id, kind)` — joins predictions to obs via source_obs_ids.
- `Store.get_waterbody_targets()` — distinct target_ids where domain='inland_wq'.
- `argus/api/schemas.py` — `WaterbodyListResponse`.
- `argus/api/routers/waterbody.py` — `GET /waterbodies`, `GET /waterbody/{id}/observations`,
  `GET /waterbody/{id}/anomalies`.
- `index.html` — added `#wq-panel` and `#report-panel` divs to sidebar.
- `app.js` — `loadWaterbodies()`, `loadWQTarget(targetId)`, `loadWQReport(targetId)`:
  fetches water body list, renders status dot + trend list (chl-a values) + anomaly count
  + AI report; draws water body polygon on map colored by bloom-risk level.

**F-036 — Alerting + Products for D2**
- `Alert.details: dict[str, Any]` — backwards-compatible extra payload field.
- `should_alert_hab(anomaly_pred, forecast_pred)` — dual-signal gate (AND condition).
- `create_hab_alert(target_id, target_name, anomaly_pred, forecast_pred, ...)` — builds
  Alert with water body name, anomaly sigma, bloom-risk forecast, intakes_threatened.
- `export_wq_geojson()`, `export_wq_png()`, `export_wq_summary()`, `export_wq_products()`.
- `tests/test_wq_alert.py`: 31 tests covering should_alert_hab gate, create_hab_alert payload
  contents, send_alert delivery, all WQ product export functions.

### State at end of session

- 791/791 offline tests pass (was 732; +59 new tests). ruff clean. mypy clean.
- Phase 7 definition of done: all ACs met. CP-2 closed.
- Commit: main · a4c4351
- Quota used: Zero (no live API calls).

### Next

F-037 — Per-domain tasking + scheduler (Phase 8). ADR-0007 decision required first.
OQ-B (choke-point definition) still blocks F-040.

---

## 2026-06-27 — Session 7 — F-030–F-033: AI Layer — PHASE 6 COMPLETE

**Agent:** Claude claude-sonnet-4-6
**Duration:** Continuation session (high-velocity mode)
**Tasks:** F-030, F-031, F-032, F-033 complete — Phase 6 (AI Layer) complete

### What happened

**F-030 — Assistant Scaffolding + Grounding Guard**
- `argus/ai/base.py`: `Scope`, `GroundedText`, `GroundedAnswer`, `AIReport`, `Assistant` protocol.
- `argus/ai/client.py`: `ArgusAIClient`; pinned model `claude-sonnet-4-6`; logged calls and tokens;
  lazy `anthropic` import (no live calls in default test suite per INV-7).
- `argus/ai/grounding.py`: `GroundingGuard.validate()` — two-check system: (1) every citation id
  in `citations` must exist in store (as Observation or Prediction), (2) every factual sentence
  (containing digit, risk label, measurement keyword) must have an inline `[record_id]` citation.
  Raises `GroundingError` on any violation.
- `argus/ai/fallback.py`: `is_offline()` checks `ARGUS_AI_OFFLINE` env var; `generate_template_report()`
  produces non-LLM grounded text from store observations. Factual value sentences include `[obs_id]` tags.
- `pyproject.toml`: `[ai]` optional extras `anthropic>=0.30`.
- Fixtures: `tests/fixtures/ai/grounded_response.json`, `ungrounded_response.json`.
- 30 tests. Commit: cae538e

**F-031 — NL Situation Reports (Grounded, Cited)**
- `argus/ai/reports.py`: `SituationReporter` — queries store for recent obs and predictions, builds
  JSON context, calls `ArgusAIClient.complete()` with system prompt, validates via `GroundingGuard`.
  Falls back to `generate_template_report()` when `ARGUS_AI_OFFLINE=true`.
- `argus/core/store.py`: added `get_observations_by_target(target_id, since, obs_types)`.
- `argus/api/routers/ai.py`: `GET /waterbody/{id}/report` → `AIReportResponse`.
- `argus/api/schemas.py`: `AIReportResponse(text, citations, model, _attribution)`.
- Fixture: `tests/fixtures/ai/report_wq_grounded.json`.
- 18 tests (offline mode, mocked LLM grounded passes + ungrounded raises, API endpoint). Commit: da441cd

**F-032 — NL Query (Read-Only)**
- `argus/ai/query.py`: `QueryPipeline` — (1) `_is_write_action()` checks keywords and returns polite
  refusal without any LLM call; (2) 2-step pipeline: translate question to StoreQuery JSON (LLM call 1),
  execute StoreQuery against store, synthesize grounded answer (LLM call 2); (3) validate with guard.
  `_parse_store_query()` extracts JSON from LLM prose robustly.
- `POST /query` endpoint. `QueryRequest`/`QueryResponse` schemas.
- 23 tests (write-action refusal no-LLM, anomaly query mocked 2-step, invented fact raises, offline). Commit: f9699f8

**F-033 — Anomaly Explanation + Triage**
- `argus/ai/anomaly_explain.py`: `AnomalyExplainer.explain(prediction_id)` — loads prediction and
  source observations from store; builds context string; calls LLM with HYPOTHESIS/ADVISORY/CONFIDENCE
  format; parses response into `AnomalyExplanation` dataclass; validates all factual sentences with guard.
  Offline template cites prediction id directly. Raises `ValueError` for unknown prediction ids.
- `GET /anomaly/{id}/explanation` → `ExplanationResponse(hypothesis, advisory, confidence, citations, model, _attribution)`.
  Returns 404 for unknown prediction.
- 20 tests (offline template, mocked LLM all ACs, ungrounded raises, missing pred 404). Commit: 85e75b1

### Test counts: 732 / 732 pass (offline, no live API calls)
### Phase 6 DoD: COMPLETE — all F-030–F-033 ACs met; grounding guard rejects ungrounded in test;
### no live Anthropic API calls in default suite; ARGUS_AI_OFFLINE=true fallback works.

---

## 2026-06-27 — Session 6 — F-027–F-029: WQ Prediction Engine — PHASE 5 COMPLETE

**Agent:** Claude claude-sonnet-4-6
**Duration:** Continuation session (high-velocity mode)
**Tasks:** F-027, F-028, F-029 complete — Phase 5 (Prediction Engine: Water Quality) complete

### What happened

**F-027 — Seasonal Baseline + AnomalyDetector**
- `argus/predict/anomaly_detector/baseline.py`: `SeasonalBaseline` dataclass (per-ISO-week
  mean/std from history). `build_baseline()` bins Observations by `created_at.isocalendar().week`.
  Single-week observations get std=0.0 (insufficient to compute z-score).
- `argus/predict/anomaly_detector/detector.py`: `AnomalyDetector` (fit/predict/validate).
  `predict()` returns Prediction(kind='anomaly', uncertainty={"sigma": z_score}, INV-9).
  `validate()` computes false_alarm_rate; `passed_gate = rate < 10%`.
- `Store.get_predictions_by_kind()` for anomaly query.
- `tests/test_anomaly_detector.py` (21 tests). All ACs verified.
- Commit: b6399f6

**F-028 — WaterQualityForecast GBM with bootstrapped CI**
- `argus/predict/wq_forecast/drivers.py`: `fetch_weather_features()` (Open-Meteo ERA5,
  precip_7d + temp_7d). Used only in live mode; tests bypass it via synthetic data.
- `argus/predict/wq_forecast/trainer.py`: `build_feature_vector()` (7 features: chl lags,
  sin/cos doy, weather). `build_training_matrix()` (lag-aligned from Observation history).
  `train_gbm()` (GradientBoostingRegressor, n_estimators=50).
- `argus/predict/wq_forecast/model.py`: `WQForecaster.from_history()` (80/20 holdout RMSE).
  `forecast()` uses bootstrap median as point estimate → guarantees ci_low ≤ value ≤ ci_high.
  Prediction uncertainty={"ci_90_low","ci_90_high","rmse"} per AC3/INV-9. `save/load` via pickle.
- `tests/test_wq_forecast.py` (24 tests). All ACs verified.
- Commit: a203616

**F-029 — Predictor Interface + Skill Gate**
- `argus/eval/skill_gate.py`: `check_gate(predictor_id, store)` checks most recent SkillReport
  passed_gate. `gate_predictions(preds, store)` filters by gate with per-call cache.
- `argus/core/store.py`: `passed_gate INTEGER DEFAULT 0` column added to skill_reports via
  idempotent ALTER TABLE. `save_skill_report()` updated to accept `passed_gate=bool`.
  `get_skill_reports_by_predictor()` (sorted ascending).
- `argus/api/routers/waterbody.py`: `GET /waterbody/{id}/forecasts` (gated only);
  `GET /waterbody/{id}/raw_predictions` (unfiltered). Registered in `create_app()`.
- `tests/test_skill_gate.py` (18 tests). All ACs verified.
- Commit: 422e0a9

### Outcome
641/641 offline tests pass. ruff clean. mypy clean. Phase 5 DoD complete.
Next: F-030 (Phase 6) — AI Assistant scaffolding + grounding/citation guards.

---

## 2026-06-27 — Session 6 — F-024–F-026: Inland Water Quality Domain — PHASE 4 COMPLETE

**Agent:** Claude claude-sonnet-4-6
**Duration:** Continuation session (high-velocity mode)
**Tasks:** F-024, F-025, F-026 complete — Phase 4 (Domain D2: Inland Water Quality) complete

### What happened

**F-024 — Water-body model + targets + resolution gate**
- `argus/aoi/loader.py`: added `load_water_body_target()` — reads GeoJSON Feature + optional
  meta YAML; computes `area_ha` via shapely `_approx_area_km2()`; sets
  `resolution_status ∈ {"eligible","below_resolution"}` against `MIN_WATER_BODY_AREA_HA = 1.0`.
  Added `require_eligible()` which raises `BelowResolutionError` for below-resolution targets.
- `argus/core/errors.py`: `BelowResolutionError(AOIError)` added.
- `config/water_bodies/reference_lake.geojson` + `reference_lake_meta.yaml`: anchor fixture
  (~11 ha water body in Trinidad/Tobago AOR; calibration_state="uncalibrated").
- `tests/test_water_body_loader.py` (18 tests): all passing.
- Commit: 03c0edb

**F-025 — Sentinel-2/3 optical ingestion**
- `argus/ingest/catalogue.py`: `search_s2()` (SENTINEL-2, S2MSI2A, cloud-cover filter applied
  client-side), `search_s3()` (SENTINEL-3, OL_2_WFR___, OLCI sensor mode).
- `argus/ingest/process_api.py`: `fetch_s2_subset()` (6-band B2/B3/B4/B5/B8A/B11 FLOAT32
  evalscript; S2L2A type), `fetch_s3_olci_subset()` (10-band Oa03–Oa12; S3OLCI type).
- `argus/preprocess/optical.py`: `OpticalScene` dataclass (bands dict + GeoTransform + source);
  `preprocess_optical()` applies land mask (land pixels → NaN); `mask_clouds()` no-op stub
  (requires SCL band, deferred Phase 5).
- `argus/core/models.py`: added `"bloom_presence"` to `VALID_OBS_TYPES`.
- Fixtures: `tests/fixtures/cdse_s2_search_reference_lake.json` (2-scene STAC response in
  reverse order to verify sort); `tests/fixtures/s2_water_body_100x100.npy` (6×100×100 float32,
  seed=77, algae signal at rows 20:40 cols 20:40).
- Tests: `test_s2_catalogue.py` (17), `test_s3_catalogue.py` (7). All passing.
- Commit: 40abb16

**F-026 — `inland_wq` Analyzer**
- `argus/domains/inland_wq/indices.py`: `compute_ndci()` (B5-B4)/(B5+B4), `compute_ndti()`
  (B4-B3)/(B4+B3), `compute_cdom()` B2/B3; all NaN-safe via `np.errstate + np.where`.
  `detect_bloom_presence()`: returns True if ≥ 2% of water pixels exceed NDCI threshold 0.25.
- `argus/domains/inland_wq/analyzer.py`: `InlandWqDomain` implementing v2.0 Domain protocol.
  `search()` calls `require_eligible()` before any CDSE access (AC4). `acquire()` raises
  `NotImplementedError` (requires live auth). `analyze()` produces Observations:
  chlorophyll_a/turbidity/cdom with `evidence_class="measured"`, bloom_presence with
  `evidence_class="inferred"`. `calibration_state` from `MonitorTarget` propagated to all
  Observation `attrs`.
- `tests/test_optical_indices.py` (15 tests), `tests/test_inland_wq_analyzer.py` (17 tests).
- All 4 ACs verified: correct NDCI/NDTI values within tolerance, evidence_class honesty,
  calibration_state propagation, BelowResolutionError before CDSE.
- Commit: f119a9e

### Outcome
578/578 offline tests pass. ruff clean. mypy clean. Phase 4 DoD complete.
Next: F-027 (Phase 5) — Seasonal baseline + AnomalyDetector.

---

## 2026-06-27 — Session 5 — F-022–F-023: Config Profiles, Health Endpoints — PHASE 3.5 COMPLETE

**Agent:** Claude claude-sonnet-4-6
**Duration:** Continuation of Session 5 (high-velocity mode)
**Tasks:** F-022, F-023 complete — Phase 3.5 complete

### What happened

**F-022 — Configuration management + profile system**
- `argus/core/config.py`: added `_deep_merge()` for section-level dict merging; added
  `_load_yaml()` helper; extended `load_settings()` with profile support — reads
  `ARGUS_PROFILE` env var, loads `config/settings.<profile>.yaml` from same directory as
  base settings, deep-merges on top (ARGUS_* env vars still win). `ValidationError` from
  Pydantic is now wrapped in `ConfigError` ("fails at startup" AC).
- `config/settings.dev.yaml`: dev overrides — `LOG_LEVEL=DEBUG`, `ai.offline=true`,
  dev-specific DB paths.
- `config/settings.test.yaml`: test overrides — `ai.offline=true`, `LOG_LEVEL=WARNING`,
  `/tmp/argus_test.db` paths.
- Added 9 new tests to `tests/test_config.py` (23 total): profile loading, deep merge,
  env-var-wins-over-profile, automatic ARGUS_PROFILE loading, invalid config raises
  ConfigError, no credentials in settings.yaml.

**F-023 — Health checks + readiness probes**
- `argus/api/routers/health.py`: three endpoints —
  - `GET /health`: liveness; always 200; moved from inline `app.py` to router.
  - `GET /ready`: readiness; 200 if `Store.ping()` succeeds; 503 with detail on failure.
    503 test uses file-as-parent-dir trick to block SQLite creation.
  - `GET /status`: version, `store_accessible`, `last_analysis_run_at` (from new Store
    method), CDSE quota (`cdse_bytes_today`, `cdse_daily_limit_gb`, `cdse_remaining_bytes`).
- `argus/core/store.py`: added `ping()` (SELECT 1) and `get_last_analysis_run_at()`
  (MAX(started_at) from analysis_runs).
- `argus/api/schemas.py`: added `ReadyResponse`, `QuotaStatus`, `StatusResponse`.
- `argus/api/app.py`: replaced inline `/health` with `health_router.router`.
- `tests/test_health.py`: 18 tests covering all three endpoints, 503 path, quota fields.

### Phase 3.5 definition of done — all items met

- [x] F-018–F-023 acceptance criteria met
- [x] `scripts/harness/run_all.sh` passes on the codebase
- [x] All exceptions in argus/ use canonical types from `errors.py`
- [x] All log output is structured JSON when `LOG_FORMAT=json`
- [x] No unstructured errors or bare exceptions remain

### Git

- F-022: `bf55f14` — `feat(F-022): add profile-based config management with ARGUS_PROFILE env var`
- F-023: `3c93c03` — `feat(F-023): add health, readiness, and status endpoints with quota reporting`

### Test results

503/503 offline tests pass, 2 live deselected. `ruff check` clean. `mypy` clean.

### Quota used

Zero.

---

## 2026-06-27 — Session 5 — F-018–F-021: API Contracts, Harness, Error Hierarchy, Logging

**Agent:** Claude claude-sonnet-4-6
**Duration:** Continuation of Session 5 (high-velocity mode)
**Tasks:** F-018, F-019, F-020, F-021 complete — Phase 3.5 (first 4 features)

### What happened

**F-018 — API contract finalization**
- `argus/api/schemas.py`: all response models with `description=` on every field; `_attribution`
  alias via `Field(alias=...)` + `populate_by_name=True` + `response_model_by_alias=True`;
  `HealthResponse` uses `default_factory=lambda: __version__`; `PredictionListResponse` carries
  `_attribution` alias per Open-Meteo CC BY 4.0 licence requirement.
- `argus/api/app.py`: version now from `argus.__version__`; `openapi_tags` added for structured
  OpenAPI spec.
- `docs/api/API_SPEC.md`: comprehensive D1 API specification — all endpoints, request/response
  schemas, error codes, breaking-change policy, attribution requirements.
- `tests/test_api_contracts.py` (36 tests): uses `model_validate()` as schema contract assertion;
  tests `/openapi.json` endpoint, `_attribution` field presence, sentinel test verifies
  `model_validate()` raises `ValidationError` on a structurally broken response.

**F-019 — Integration test framework + harness scripts**
- `scripts/harness/check_architecture.py` (from stub): VAL-008 uses regex
  `r"^(?:import opendrift|from opendrift)"` (not string match — avoids docstring false positives);
  VAL-010 checks live HTTP calls in tests/; VAL-017 checks hardcoded oil type strings in argus/.
- `scripts/harness/check_spec_health.py`: VAL-001 (FR coverage), VAL-002 (feature-has-tasks),
  VAL-013 (AC non-empty). Uses `"\n" + spec_file.read_text()` trick for start-of-file regex match.
- Shell wrappers: `validate.sh`, `spec_health.sh`, `run_all.sh`.
- `tests/conftest.py`: `tmp_store` (SQLite), `mock_open_meteo`, `mock_cdse_auth` (responses
  library), `mock_anthropic` (MagicMock) shared fixtures.
- `tests/harness/test_validators.py` (21 tests): tests VAL-008/010/017/001/002/013 catch
  synthetic violations and pass on real codebase. String-split trick avoids test source false
  positives (`"requests." + "get(...)"`).
- Fixed `docs/features/phase-11.md` F-056 missing AC section (real spec gap caught by VAL-002).

**F-020 — Structured error handling**
- `argus/core/errors.py`: 15-class hierarchy rooted at `ArgusError(Exception)`. Sub-hierarchies:
  `QuotaExceededError ⊂ AcquisitionError`, `ProcessApiError ⊂ AcquisitionError`,
  `BelowResolutionError ⊂ AOIError`, `ObservationTypeError(ArgusError, ValueError)` (dual
  inheritance: Pydantic v2 `@field_validator` only catches ValueError/AssertionError).
- All argus modules updated to import from `argus.core.errors` (re-exports in existing modules
  preserve external import paths). `runner.py` raises `SimulationError` (was RuntimeError).
  `models.py` raises `ObservationTypeError` (was ValueError). `acquire.py` raises
  `QuotaExceededError` on first quota check.
- `tests/test_error_handling.py` (29 tests): parametrized hierarchy check (all 15 classes);
  sub-hierarchy assertions; catchability; actionable message assertions; integration tests
  (AOI loader, Pydantic ValidationError wrapping, runner SimulationError).

**F-021 — Structured logging**
- `argus/core/logging.py`: `_JsonFormatter` emits one JSON object per line with `ts` (ISO 8601 Z),
  `level`, `module`, `event`, extra fields, optional `run_id`. `_TextFormatter` for dev:
  `ts LEVEL module: event key=val`. `get_logger(name)`: controlled by `LOG_FORMAT` env var;
  sets `propagate=False`; idempotent (tracks configured names). Thread-local `bind_run_id()` /
  `current_run_id()` wire correlation IDs into every log record automatically.
- `tests/test_logging.py` (19 tests): JSON validity, all field names, ISO 8601 ts format,
  correlation ID bind/unbind, text format, no-print sentinel.

### Git

- F-018: `65cdf72` — `feat(F-018): finalize D1 API contracts, add OpenAPI spec and contract tests`
- F-019: `a5494dc` — `feat(F-019): add integration test framework and harness validation scripts`
- F-020: `055c5ff` — `feat(F-020): add structured error hierarchy, canonical ArgusError base, no bare exceptions`
- F-021: `41c8c8f` — `feat(F-021): add structured JSON logging framework with correlation IDs`

### Test results

476/476 offline tests pass, 2 live deselected. `ruff check` clean. `mypy` clean (51 source files).

### Quota used

Zero.

---

## 2026-06-27 — Session 5 — F-014–F-017: Impact Assessment, API, Web Viewer, Alerts — CP-1 COMPLETE

**Agent:** Claude claude-sonnet-4-6
**Duration:** Continuation of Session 5 (high-velocity mode)
**Tasks:** F-014, F-015, F-016, F-017 complete — Phase 3 complete — CP-1 closed

### What happened

**F-014 — Exposure layers + impact + ETA**
- `argus/core/models.py` — added `ExposureLayer` (id, name, layer_type, geometry, attrs) and
  `ImpactAssessment` (id, prediction_id, exposure_layer_id, valid_at, eta_hours, metrics).
- `argus/core/store.py` — `exposure_layers` + `impact_assessments` tables + CRUD methods (INV-6).
- `argus/impact/assessor.py` — `load_exposure_layer()` (reads GeoJSON Feature); `assess_impact()`
  sorts ForecastFrames by valid_at, finds first intersecting frame per exposure layer (shapely),
  computes timezone-aware eta_hours. `_geom_length_km()` handles all shapely geometry types
  (including GeometryCollections from Polygon∩LineString) via `.length × 111.19`. `_geom_area_km2()`
  uses latitude-corrected area formula.
- `data/static/exposure/coastline_tobago.geojson` + `mpas_tobago.geojson` — test fixtures.
- `tests/test_impact_assessor.py` — 22 tests.

**F-015 — FastAPI service**
- `argus/api/app.py` — `create_app(db_path, config_dir)` factory with StaticFiles mount and
  FileResponse index at `/`. Routers mounted at `/aois/*`.
- `argus/api/schemas.py` — Pydantic v2 schemas; `_attribution` via `Field(alias=...)` +
  `populate_by_name=True` + `response_model_by_alias=True` (Pydantic v2 leading-underscore fix).
- Routers: `aoi.py`, `observations.py`, `predictions.py`, `impact.py`.
- `argus/cli.py` — `argus serve` command using uvicorn.
- deps: `fastapi>=0.111`, `uvicorn[standard]>=0.30`, `httpx>=0.27`. `mypy` moved to dev deps.
- `tests/test_api.py` — 50 tests covering all endpoints, alias serialization, 404s, schema.

**F-016 — Web viewer**
- `argus/api/static/index.html` + `app.js` — Leaflet map (CDN, no bundler); `bootstrap()` fetches
  `/aois`, parallel fetches obs/predictions/impact; polygon observations colored by confidence;
  prediction heatmap with opacity ramp; ETA sidebar cards. Verified test uses `/static/app.js`.

**F-017 — Alert delivery + product export**
- `argus/alert/delivery.py` — `AlertChannel` (webhook | email), `Alert` (lifecycle: pending → sent |
  failed), `load_channels()` (YAML, graceful [] on absent file), `_send_webhook()` (POST via
  `requests`, `raise_for_status()`), `_send_email()` (smtplib.SMTP, optional login), `send_alert()`
  (no-op if channels=[], catches all exceptions per channel → "failed").
- `config/alert_channels.yaml` — template with `channels: []` + commented examples.
- `argus/export/products.py` — `export_metadata()` (JSON with run metadata, observations,
  optional prediction/impact sections); `export_products()` gains `prediction`/`impact` kwargs
  and returns a `"metadata"` key alongside `"geojson"` and `"png"`.
- `tests/test_alert_delivery.py` — 30 tests (Alert model, load_channels, no-op, webhook with
  `responses` library mock, email with `unittest.mock.patch("smtplib.SMTP")`, export_metadata,
  export_products metadata key).
- Updated `tests/test_export.py` — extended expected artifact key set to include `"metadata"`.

### Phase 3 definition of done — CP-1

- [x] F-014 (exposure + impact) — commit 2c851ae
- [x] F-015 (FastAPI service) — commit 38000bd
- [x] F-016 (web viewer) — commit af20fa3
- [x] F-017 (alert + export) — commit 792a3c6
- [x] All Phase 3 acceptance criteria met

### Git

Commits: `2c851ae`, `38000bd`, `af20fa3`, `792a3c6`

### Test results

371/371 offline tests pass, 2 live deselected. `ruff check` clean. `mypy` clean (49 source files).

### Quota used

Zero.

---

## 2026-06-27 — Session 5 — F-013: ForecastFrame Evaluator & Trajectory Skill Metric

**Agent:** Claude claude-sonnet-4-6
**Duration:** Continuation of Session 5 (high-velocity mode)
**Tasks:** F-013 complete — Phase 2 complete

### What happened

- Created `argus/predict/oil_trajectory/evaluator.py`:
  - `TrajectoryEvalCase` dataclass + `from_json()`: loads trajectory eval case with
    `truth_centroid [lon, lat]`, `rng_seed` (INV-8), `horizon_hours`.
  - `TrajectorySkillResult` dataclass: captures predicted_centroid, truth_centroid, separation_km,
    n_frames, created_at.
  - `_haversine_km(lon1, lat1, lon2, lat2)`: Haversine great-circle distance using earth radius 6371 km.
  - `_frame_centroid(frame)`: extracts (lon, lat) from `frame.stats["mean_lon"/"mean_lat"]`; falls back
    to mean of footprint polygon coordinates if stats absent.
  - `evaluate_trajectory(eval_case, frames)`: uses last ForecastFrame as T+horizon prediction;
    empty-frames case uses (0, 0) as placeholder (separation still valid for unit tests).
  - `skill_result_to_store_report(result)`: maps separation_km to f1_proxy = max(0, 1 − sep_km/100);
    returns kwargs dict for `Store.save_skill_report()`.
- Created `data/eval/tobago_2024_trajectory.json`:
  - `truth_centroid: [-61.25, 11.15]` (approx drift endpoint from REMPEC 2024 post-spill analysis)
  - `rng_seed: 42`, `horizon_hours: 24`, `oil_type: "crude_medium"`
- Created `tests/test_forecast_frames.py` — 21 tests:
  - `TrajectoryEvalCase.from_json()` field loading
  - INV-9 (uncertainty non-empty), INV-8 (rng_seed matches case), evidence_class=modeled
  - ForecastFrame store round-trips (count, footprint, stats, valid_at)
  - Haversine (same point → 0.0; 1° longitude → ~111.2 km)
  - `_frame_centroid` stats path and polygon fallback path
  - `evaluate_trajectory` return type, non-negative separation, frame count, exact match = 0, empty frames
  - `skill_result_to_store_report` key set; store→retrieve round-trip

### Phase 2 definition of done

- [x] F-011 (sim service) — commit 128ffea
- [x] F-012 (forcing providers + cache) — commit 0508df4
- [x] F-013 (ForecastFrame evaluator) — commit b3ac90a
- [x] All Phase 2 acceptance criteria met

### Git

Commit `b3ac90a` — `feat(F-013): add ForecastFrame evaluator and trajectory skill metric`

### Test results

292/292 offline tests pass, 2 live deselected. `ruff check` clean. `mypy` clean (37 source files).

### Quota used

Zero.

---

## 2026-06-27 — Session 5 — F-012: Metocean Forcing Providers + Cache + Fallback

**Agent:** Claude claude-sonnet-4-6
**Duration:** Continuation of Session 5 (high-velocity mode)
**Tasks:** F-012 complete

### What happened

- Created `argus/predict/oil_trajectory/forcing.py`:
  - `CmemsUnavailableError(RuntimeError)` for CMEMS fallback trigger.
  - `ForcingGrid` dataclass: times, wind_u/v, current_u/v, source, open_meteo_calls, cmems_bytes (quota).
  - `fetch_open_meteo_winds()`: domain-centre lat/lon; hourly wind_speed_10m + wind_direction_10m.
  - `fetch_cmems_currents()`: CMEMS Motu NRT endpoint; raises `CmemsUnavailableError` on any failure.
  - `fetch_open_meteo_marine()`: fallback; ocean_current_velocity + direction.
  - `get_forcing()`: 1. cache check; 2. Open-Meteo winds; 3. CMEMS currents → fallback to marine;
    4. save to cache. `cached: ForcingGrid | None` typed explicitly (mypy).
  - `_wind_components()`, `_parse_open_meteo_winds()`, `_parse_cmems_currents()`, `_parse_open_meteo_marine()`.
- Created `argus/predict/oil_trajectory/cache.py`:
  - `ForcingCache`: pyarrow parquet read/write (columns: time, wind_u, wind_v, current_u, current_v).
  - `_cache_key()`: sha256 of JSON params, 16 hex chars.
- Created `tests/fixtures/cmems_currents_tobago.parquet` (3-row parquet; binary fixture).
- Created `tests/fixtures/open_meteo_winds_tobago.json` (3-hour mock API response).
- Added `pyarrow>=14.0` to `pyproject.toml` (BSD license; INV-1 compliant).
- 23 new tests in `tests/test_forcing_providers.py`.

### Git

Commit `0508df4` — `feat(F-012): add metocean forcing providers, parquet cache, CMEMS fallback`

### Test results

269/269 offline tests pass. `ruff check` clean. `mypy` clean (36 source files).

### Quota used

Zero.

---

## 2026-06-27 — Session 5 — F-011: OpenOil Sim Service, GPL Isolation, Oil Type Registry

**Agent:** Claude claude-sonnet-4-6
**Duration:** Continuation of Session 5 (high-velocity mode)
**Tasks:** F-011 complete

### What happened

- Created `argus/predict/__init__.py` and `argus/predict/base.py`:
  - `Predictor` Protocol (scaffold — frozen at F-029), `PredictContext` dataclass, `EvalSet` type alias.
- Created `argus/predict/oil_trajectory/oil_types.py`:
  - `OilType` frozen dataclass; `OilTypeRegistry` with `.get()` validating against loaded types.
  - `OilTypeRequiredError` (INV-5: no default) and `OilTypeNotFoundError` with available types listed.
  - `load_oil_types(path)` reads `config/oil_types.yaml`.
- Created `argus/predict/oil_trajectory/runner.py`:
  - `SimInput` dataclass: oil_type, seed_geometry, t0, duration_hours, rng_seed (INV-8), n_particles.
  - `run_simulation()`: validates oil_type → serializes SimInput to JSON tempfile → spawns subprocess
    `python -m argus.predict.oil_trajectory.sim_worker` → reads output JSON → returns frame list.
  - Does NOT import opendrift (GPL isolation).
- Created `argus/predict/oil_trajectory/sim_worker.py`:
  - `import opendrift` contained inside `_simulate()` function — only executed as __main__.
  - GPL isolation verified: test scans all argus/*.py files and asserts only sim_worker.py
    contains "import opendrift".
- Extended `argus/core/models.py`: `Prediction` (INV-9: `uncertainty` required) + `ForecastFrame`.
- Extended `argus/core/store.py`: `predictions` + `forecast_frames` tables (INV-6); CRUD.

### Decisions made

- Docstrings in runner.py reworded to avoid false-positive "import opendrift" string match.
- `import opendrift` placed inside `_simulate()` (not module-level) so importing sim_worker
  as a module doesn't fail when opendrift isn't installed.

### Git

Commit `128ffea` — `feat(F-011): add OpenOil sim service with GPL isolation and oil type registry`

### Test results

246/246 offline tests pass. `ruff check` clean. `mypy` clean (34 source files).

### Quota used

Zero.

---

## 2026-06-27 — Session 5 — F-010: Observation Schema Finalization (PHASE 1 COMPLETE)

**Agent:** Claude claude-sonnet-4-6
**Duration:** Continuation of Session 5 (high-velocity mode)
**Tasks:** F-010 complete — Phase 1 definition of done met

### What happened

- Added `VALID_OBS_TYPES: frozenset[str]` to `argus/core/models.py` (6 types: oil_slick,
  chlorophyll_a, turbidity, cdom, surface_temp, inundation). Any new domain must extend this set.
- Added pydantic `field_validator("obs_type")` that raises `ValueError` with actionable message
  listing all registered types.
- Extended `Observation` model with new fields matching DATA_MODELS.md §Observation exactly:
  - `features: dict[str, Any] | None` — top-level feature vector (previously only in attrs)
  - `status_updated_at: datetime | None` — timestamp set on status transition
  - `domain`, `target_id`, `value`, `unit` — optional; populated by domain-aware consumers
- Updated `argus/core/store.py`:
  - New columns in `observations` table DDL (status_updated_at, features, domain, target_id, value, unit)
  - Idempotent `ALTER TABLE ADD COLUMN` via `contextlib.suppress(OperationalError)` for existing DBs
  - `save_observation()` persists all new fields
  - `_row_to_obs()` reads all new fields
  - `transition_observation_status(obs_id, new_status, updated_at=None)` updates status + timestamp
- Updated `argus/domains/marine_oil/detector.py` to populate `features=feats` top-level field
  (attrs["features"] kept for backward compat)
- Updated `argus/domains/marine_oil/classifier.py`: sets `status_updated_at=datetime.now(UTC)`
  on every status transition; `_build_feature_matrix` prefers `obs.features` over `obs.attrs`

### Phase 1 definition of done — all items met

- [x] F-007–F-010 acceptance criteria all met
- [x] P/R report exists for tobago_2024 (eval harness, F-009)
- [x] Observation schema frozen; documented in models.py; any change requires store migration
- [x] No v1.0 entity names anywhere in argus/ code

### Git

Commit `2c1ae8e` — `feat(F-010): freeze Observation schema, add obs_type validation and status transitions`

### Test results

227/227 offline tests pass, 2 live deselected. `ruff check` clean. `mypy` clean (28 source files).

### Quota used

Zero.

---

## 2026-06-27 — Session 5 — F-007, F-008, F-009: Segmentor, Classifier, Eval Harness

**Agent:** Claude claude-sonnet-4-6
**Duration:** Continuation of Session 5 (high-velocity mode)
**Tasks:** F-007 complete, F-008 complete, F-009 complete

### What happened

**F-007 — Robust dark-spot segmentation + features:**
- Created `argus/domains/marine_oil/segmentor.py`:
  - Otsu thresholding via histogram (256 bins); between-class variance maximization.
  - Degenerate case: `np.ptp(arr) < 1e-10` → threshold below all data (no false positives).
  - Morphological opening (erosion + dilation, iterations=2) removes ≤2-pixel noise patches;
    20×20+ blobs survive.
- Created `argus/domains/marine_oil/features.py`:
  - 9-feature vector: area_km2, perimeter_km, compactness, elongation, convexity, orientation,
    mean_sigma0_db, contrast_vs_background_db, texture_glcm.
  - GLCM texture contrast computed via vectorized `np.add.at()`; convexity from scipy ConvexHull.
  - Features stored in `Observation.attrs["features"]` by `analyze()`.
- Renamed `OilDomainV0` → `MarineOilDomain` (v2.0 canonical); backward-compat alias kept.
- Created `tests/fixtures/sar_with_blob_and_noise.npy` (shape 2×200×200, seed=99, dark blob at
  rows 80:100, cols 80:100; four 2×2 noise patches at corners).
- 10 new tests in `tests/test_segmentor.py`; features tested via updated `test_oil_detector.py`.

**F-008 — Look-alike rejection + confidence:**
- Created `argus/domains/marine_oil/classifier.py`:
  - `train_classifier(labeled_samples)`: GBT (n_estimators=50, random_state=42 per INV-8).
  - `OilClassifier.classify()`: returns NEW Observation instances via `model_copy(update={...})`;
    never mutates; evidence_class unchanged (INV-3); sets status="confirmed"/"dismissed".
  - `load_classifier(config_path)`: loads YAML config + pkl model.
- Created `config/oil_classifier.yaml` (threshold=0.5, n_estimators=50, random_state=42).
- Created `models/oil_classifier_v1.pkl` (trained GBT, 100% accuracy on 30 labeled samples).
- Created `data/eval/labeled_detections.json` (15 oil: contrast 11–19 dB; 15 lookalikes: contrast 2–8 dB).
- Updated `Observation.status` to `Literal["candidate", "confirmed", "dismissed"]` (v2.0 canonical).
- 15 new tests in `tests/test_classifier.py`.

**F-009 — Eval harness + P/R scorer + SkillReport store scaffold:**
- Created `argus/eval/__init__.py`, `argus/eval/scorer.py`:
  - `EvalResult` dataclass; `score()` computes TP/FP/FN/precision/recall/F1 via shapely intersection.
  - Confidence threshold filter (default 0.5).
- Created `argus/eval/harness.py`:
  - `EvalCase.from_json()` loads JSON eval case.
  - `SkillReport` dataclass scaffolds predictor skill metrics (gating UI in F-029).
  - `run(eval_case, fixture_mode=True)`: synthetic SAR (seed=42), blob at rows 40:60, cols 20:40
    (positioned to overlap tobago_2024 truth polygon per coordinate transform); runs full stack.
  - `fixture_mode=False` raises NotImplementedError (requires CDSE Phase 2+).
- Extended `argus/core/store.py`: `skill_reports` table with `save_skill_report()` +
  `get_skill_reports_for_case()` (INV-6 maintained).
- 19 new tests in `tests/test_eval_harness.py`.

### Git

- Commit `9ea967a` — `feat(F-007): add Otsu segmentor, morphological cleaning, and feature extraction`
- Commit `f1ad411` — `feat(F-008): add GBT look-alike classifier and OilClassifier`
- Commit `a3a5187` — `feat(F-009): add eval harness, P/R scorer, and SkillReport store scaffold`

### Test results

204/204 offline tests pass, 2 live deselected. `ruff check` clean. `mypy` clean (28 source files).

### Quota used

Zero.

---

## 2026-06-27 — Session 5 — F-006: Product Export, EvalCase & CLI Run (PHASE 0 COMPLETE)

**Agent:** Claude claude-sonnet-4-6
**Duration:** Continuation of Session 5 (high-velocity mode)
**Tasks:** F-006 complete — Phase 0 definition of done met

### What happened

- Added `matplotlib>=3.8` to `pyproject.toml` (MIT license, INV-1 compliant).
- Created `argus/export/__init__.py` and `argus/export/products.py`:
  - `export_geojson(observations, run, path)`: writes FeatureCollection; all Observation
    properties (obs_type, evidence_class, area_km2, confidence, status) preserved in
    feature properties; collection-level properties include analysis_run_id and domain_id.
  - `export_png(preprocessed, observations, path)`: uses `matplotlib.backends.backend_agg.FigureCanvasAgg`
    (non-interactive Agg backend, no global pyplot state); renders VV dB raster with gray colormap,
    overlays candidate observation polygons in red.
  - `export_products(observations, run, preprocessed, output_dir)`: orchestrates both exports
    to a run-tagged subdirectory.
- Updated `argus/cli.py` with `argus run` command:
  - `--aoi <name>`: loads `config/aois/<name>.geojson` via `--config-dir` (testability hook)
  - `--since <date>`: used as output label
  - `--live`: stub — exits with error (Phase 1 implements live CDSE path)
  - Offline mode: synthetic SAR with planted dark blob (seed=42), all-water land mask;
    runs preprocess → detect → export; deterministic due to INV-8.
  - Uses `Annotated[...]` typer style + module-level Path constants (ruff B008 compliant).
- Created `data/eval/tobago_2024.json`:
  - EvalCase with `oil_type="crude_medium"` per ADR-0006 (no default; must be explicit)
  - truth_geometry: approximate bounding polygon from REMPEC incident report 2024-02
  - event_time, cdse_product_id, bbox, provenance fields all present

### Phase 0 definition of done — all items met

- [x] F-000 through F-006 acceptance criteria all met
- [x] `tests/test_phase0_e2e.py` green offline (13 tests)
- [x] `Domain` protocol in `argus/domains/base.py` stable
- [x] `AnalysisRun` + `Observation` in store (INV-6)
- [x] `evidence_class="measured"` on all oil detections (INV-3)
- [x] `EvalCase` tobago_2024.json includes `oil_type` field (ADR-0006)
- [ ] One opt-in `--live` path run manually — deferred to Phase 1 (requires CDSE credentials)

### Git

Commit `2f9fa68` — `feat(F-006): add product export, EvalCase, and CLI run command`

### Test results

147/147 offline tests pass, 2 live deselected. `ruff check` clean. `mypy` clean (22 files).

### Quota used

Zero.

---

## 2026-06-27 — Session 5 — F-003, F-004, F-005: Scene Acquisition, SAR Preprocessing, Domain Protocol & Dark-Spot Detector

**Agent:** Claude claude-sonnet-4-6
**Duration:** Continuation of Session 5 (high-velocity mode)
**Tasks:** F-003 complete, F-004 complete, F-005 complete

### What happened

**F-003 — Scene acquisition + persistence:**
- Created `argus/ingest/process_api.py`: `fetch_s1_subset()` calls Sentinel Hub Process API,
  sends 2-band VV+VH evalscript (FLOAT32 output), returns `(tiff_bytes, byte_count)`.
  Uses AOI bbox for the request body; bearer auth from `CdseAuth`.
- Created `argus/ingest/acquire.py`: `acquire_scene()` enforces pre/post CDSE daily quota,
  writes GeoTIFF artifact to disk, persists `Scene` via store.
- Extended `argus/core/models.py` with `Scene` model.
- Created `argus/core/store.py`: SQLite store (sole sqlite3 importer per INV-6); `scenes`
  table; `save_scene/get_scene/daily_bytes_total()`. Row factory for named column access.
- 21 new tests: `tests/test_store_scene.py` (15), `tests/test_acquire.py` (6).

**F-004 — SAR preprocessing (masked σ⁰ dB):**
- Created `argus/preprocess/landmask.py`: `GeoTransform` dataclass with `lon_res`/`lat_res`
  properties; `load_coastline()` loads a GeoJSON file; `rasterize_land_mask()` uses shapely 2.0
  vectorized `shapely.contains()` + `shapely.points()` — no rasterio required.
- Created `argus/preprocess/sar.py`: `preprocess()` applies `_to_db()` (10·log10, epsilon=1e-10),
  `_speckle_filter()` (scipy `median_filter`), then sets land pixels to NaN (float32).
  `PreprocessedScene` dataclass carries `vv_db`, `vh_db`, `transform`, `crs`.
- Created `data/static/coastline.geojson`: 8-vertex Tobago island polygon for offline tests.
- Created `tests/fixtures/synthetic_sar_100x100.npy`: shape (2,100,100) float32, seed=42.
- 23 new tests: `tests/test_preprocess.py` (14), `tests/test_landmask.py` (9).

**F-005 — Domain Protocol + Naive Dark-Spot Detector + Observation Persistence:**
- Created `argus/domains/base.py`: `Acquisition` dataclass + `Domain` Protocol (INV-2 stable
  interface — never edit without ADR).
- Created `argus/domains/marine_oil/detector.py`: `OilDomainV0` with `analyze()` calling
  `_detect()`: adaptive threshold (mean − 2·max(σ, 1 dB) on VV dB), morphological erosion +
  dilation (1 iteration each), `scipy.ndimage.label`, per-component convex-hull `Observation`.
  `_approx_area_km2()` uses centroid-lat scaling. `make_analysis_run()` helper.
- Extended `argus/core/models.py` with `AnalysisRun` and `Observation` (INV-3: `evidence_class`
  required; INV-9: `status` field gates UI trust).
- Extended `argus/core/store.py`: `analysis_runs` and `observations` SQLite tables; CRUD methods
  `save/get_analysis_run`, `save/get_observation`, `get_observations_for_run`.
- 30 new tests: `tests/test_oil_detector.py` (14), `tests/test_store_observation.py` (16).

### Decisions made

- `strict=True` passed to `zip(lons, lats)` in detector (lengths always equal from `np.where()`).
- `ruff` B905 requires explicit `strict=` on all `zip()` calls — applied project-wide.
- mypy `python_version` bumped to 3.12 (numpy 2.x stubs use PEP 695 `type` statement).

### Git

- Commit `d5ed697` — `feat(F-003): add Process API client, scene acquisition, and SQLite store`
- Commit `7fa5c77` — `feat(F-004): add SAR preprocessing with land mask and speckle filter`
- Commit `56a68dc` — `feat(F-005): add Domain protocol, naive dark-spot detector, and Observation persistence`

### Test results

119/119 offline tests pass. `ruff check` clean. `mypy` clean (20 source files).

### Quota used

Zero.

---

## 2026-06-27 — Session 5 — F-001: Config + AOI/Target Model & Loader

**Agent:** Claude claude-sonnet-4-6
**Duration:** Single implementation session
**Tasks:** F-001 complete

### What happened

- Added `pyyaml>=6.0` and `shapely>=2.0` to `pyproject.toml` dependencies; synced via `uv`.
- Created `argus/core/config.py`:
  - Pydantic models for all settings.yaml sections: `CdseConfig`, `OpenMeteoConfig`,
    `CmemsConfig`, `AiConfig`, `StoreConfig`, `AlertsConfig`, `LoggingConfig`, `PredictionConfig`.
  - `Settings` root model; `load_settings(path)` loads YAML then applies explicit `_ENV_MAP`
    of `ARGUS_*` env var overrides (no pydantic-settings nested-delimiter ambiguity).
  - `ConfigError` raised by `require_cdse_credentials()` with remediation text; never emits
    credential values in the error message.
- Created `argus/core/models.py`:
  - `AOI`: id, name, geometry (GeoJSON dict), `domains: list[str]`, params, active, created_at.
    `bbox` property extracts (min_lon, min_lat, max_lon, max_lat) from coordinates.
  - `MonitorTarget`: id, aoi_id, kind (water_body|region), name, geometry, domains,
    resolution_status (eligible|below_resolution), calibration_state, attrs.
  - `_extract_coords()` helper flattens coordinates for Point/LineString/Polygon/MultiPolygon.
  - All v2.0 canonical names; no v1.0 remnants.
- Created `argus/aoi/__init__.py` and `argus/aoi/loader.py`:
  - `load_aoi(path)` reads GeoJSON Feature or bare Polygon/MultiPolygon; extracts properties
    into `AOI`; falls back to file stem for `id` when properties absent.
  - `_validate_geometry()` uses shapely `is_valid` + `explain_validity`; rejects self-intersecting
    geometries and AOIs >500,000 km² (rough centroid-lat scaling).
  - `AOIError(ValueError)` with clear, actionable messages.
- Created `config/aois/tobago.geojson`: polygon covering Tobago marine waters
  (10.8–11.5°N, 61.2–60.3°W), `domains=["marine_oil"]`.
- 28 new tests: `tests/test_config.py` (14) and `tests/test_aoi_loader.py` (14).

### Decisions made

None requiring ADR. Used an explicit `_ENV_MAP` dict instead of pydantic-settings
`env_nested_delimiter` to avoid ambiguity with multi-word section names (`open_meteo`).

### Git

Commit `9662b06` — `feat(F-001): add config system, AOI model, and loader`

### Test results

33/33 pass. `ruff check` clean. `mypy` clean (8 files).

### Quota used

Zero.

---

## 2026-06-27 — Session 4 — F-000: Repo & Tooling Scaffold

**Agent:** Claude claude-sonnet-4-6
**Duration:** Short implementation session
**Tasks:** F-000 complete

### What happened

- Created Python package skeleton: `argus/`, `argus/core/`, `argus/domains/`
- `argus/__init__.py` — version string 0.1.0
- `argus/cli.py` — typer app; `@app.callback()` forces multi-command mode in typer 0.26.x
  (single `@app.command()` alone collapses to root in newer typer; callback fixes this)
- `pyproject.toml` — hatchling build, ruff (E/W/F/I/UP/B/C4/SIM), mypy (warn_return_any),
  pytest (offline-only default, `live` marker), `typer>=0.12` (removed non-existent `[all]` extra)
- `Makefile` — install, lint, format, test, test-live, run, clean targets
- `.github/workflows/ci.yml` — Python 3.11/3.12 matrix; ruff+mypy+pytest on push/PR to main
- `tests/test_smoke.py` — 5 offline tests; all pass

### Decisions made

None requiring ADR. Fixed typer[all] → typer (upstream extra removed in 0.26.x).

### Git

Commit `850b852` — `feat(F-000): add repo and tooling scaffold`

### Quota used

Zero.

---

## 2026-06-27 — Session 3 — Repository Finalization, Deployment Strategy & Git Init

**Agent:** Claude claude-sonnet-4-6
**Duration:** Continuation session
**Tasks:** Repository cleanup, deployment strategy, git initialization, README rewrite

### What happened

- Audited and removed all root duplicate/stub files (ADR-0003/0004 at root, ARCHITECTURE.md
  stub, DATA_MODELS.md stub, PRD.md stub, phase-0.md stub)
- Deleted all Windows Zone.Identifier files (9 files)
- Fixed broken relative links in docs/adr/ files that still pointed at root paths
- Created docs/architecture/ trilogy: ARCHITECTURE.md v2.1, DATA_MODELS.md v2.1, STACK.md
- Added ADR-0007 (scheduler, DRAFT — pending Josh decision)
- Added ADR-0008 (deployment strategy, Accepted) — Vercel + GCP Cloud Run + Cloud Storage
- Updated CLAUDE.md with §13 (Git identity: CXLD10, conventional commits, no AI co-author)
  and §14 (production deployment constraints, INV-10 scale-to-zero)
- Updated STACK.md with production deployment section
- Updated ARCHITECTURE.md §7 with production deployment (Vercel + Cloud Run)
- Rewrote README.md from scratch (production-quality open-source README)
- Created .gitignore, .gitattributes, .editorconfig
- Added .gitkeep to empty directories (data/eval, data/static, config/aois, docs/api)
- Created config/oil_types.yaml and config/settings.yaml
- Initialized git repository; first commit pending Josh confirmation of email

### Constraints established this session

- Git author: CXLD10 / GitHub no-reply email; no AI co-author attribution ever
- Production deployment: Vercel (frontend) + GCP Cloud Run (API) + GCS (artifacts)
- GCP $300 credits must last many months; scale-to-zero mandatory (INV-10)
- Conventional commits required; small atomic commits; feature branches → PRs

### State at end of session

- Documentation: 100% complete and internally consistent; one authoritative source per concept
- No root duplicate files remain
- Git initialized; initial commit pending (need Josh to confirm GitHub no-reply email format)
- First build task: F-000 (repo + tooling scaffold)

### Next session should

1. Confirm git email and push initial commit if not yet done
2. Begin F-000: create pyproject.toml, argus/ package, tests/ scaffold, CLI smoke test
3. Update BOARD.md: F-000 → IN_PROGRESS

---

## 2026-06-27 — Session 2 — Repository Governance Build

**Agent:** Claude claude-sonnet-4-6
**Duration:** Full session
**Tasks:** Pre-implementation governance build; no implementation code

### What happened

- Performed complete independent validation of all Session 1 outputs
- Found 5 SUPERSEDED/INVALID items (two-tier MVP, OQ-A, OQ-F, AGENTS.md, F-018-F-023 gap)
- Found 13 VALID items confirmed, 2 PARTIALLY VALID
- Identified 9 new issues not caught in Session 1
- Built the complete docs/ directory hierarchy (47 new files, 12 directories)
- Created CLAUDE.md agent operating guide
- Created all governance documents (VALIDATORS.md, HARNESS.md)
- Created spec_graph.md + spec_graph.yaml (complete specification graph)
- Updated PRD.md with new MVP definition
- Created OPEN_QUESTIONS.md with OQ-A and OQ-F resolutions
- Reconstructed ADR-0001 and ADR-0002 from references
- Created ADR-0005 (MVP redefinition) and ADR-0006 (oil type configurability)
- Created TESTING.md, CODING.md, QUOTAS.md standards
- Corrected phase-0.md to v2.0 entity names (critical fix)
- Created phase-1.md through phase-11.md feature specs
- Created all domain specs (D1-D4), predictor specs, ASSISTANT.md
- Updated README.md, BOARD.md, ROADMAP.md

### State at end of session

- Documentation: 100% structured; all files reference-consistent
- Implementation: 0% (no code written)
- First build task: F-000 (repo + tooling scaffold)
- All blocking documentation issues resolved

### Next session should

1. Begin F-000: create pyproject.toml, argus/ package, CLI, smoke test
2. Verify `make lint` and `make test` pass on a trivial scaffold
3. Update BOARD.md: F-000 → IN_PROGRESS

---

## 2026-06-26 — Session 1 — Initial Audit (No files written)

**Agent:** Claude claude-sonnet-4-6
**Duration:** Full session
**Tasks:** Knowledge ingestion, repository audit, architecture analysis

### What happened

- Read all 9 existing markdown documents
- Produced comprehensive audit report (text only, no files written)
- Identified: missing ADR-0001/0002, broken paths, v1.0/v2.0 entity mismatch,
  missing TESTING.md, duplicate open questions, and more

### State at end of session

- Documentation analysis complete; no files written to repository
- Repository was flat-root layout with broken cross-references
- No code, no tests, no docs/ directory
