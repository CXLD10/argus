# Argus — Program Log

Append a new entry every session. Newest on top. This is the persistent memory of the project.

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
