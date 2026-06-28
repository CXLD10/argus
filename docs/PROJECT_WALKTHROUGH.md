# Argus — Project Walkthrough

- **Audience:** Developers, technical evaluators, contributors
- **Last updated:** 2026-06-29
- **Version:** 0.1.0

This document provides a complete technical and product tour of the Argus Environmental
Intelligence Platform. Read it end-to-end to understand the system before touching any code.

---

## 1. What Makes Argus Unique

Most environmental monitoring tools either:
- Require expensive proprietary data subscriptions, or
- Cover a single hazard (just oil spills, just water quality, just flooding), or
- Output raw data without interpretation

Argus does all four hazard domains from **free public satellite data**, assembles them into a
**unified store**, runs **validated predictors** on top, and **narrates the results in plain
English** with every factual claim grounded to a specific store record.

The key architectural insight: the same spine (tasking → ingestion → store → prediction → AI)
handles all four domains identically. Adding a fifth domain requires implementing one protocol
(`Domain`) and zero changes to the spine, the predictor interface, or the AI layer.

---

## 2. Architecture Walkthrough

The system has five layers:

```
RAW DATA SOURCES
  Sentinel-1 SAR (CDSE)           Sentinel-2/3 optical (CDSE)
  Open-Meteo API                  Copernicus DEM
        │
        ▼
OBSERVATION DOMAINS (Domain protocol plug-ins)
  D1 marine_oil    D2 inland_wq    D3 weather_hydro    D4 hydro_chokepoints
        │
        ▼
SPINE (domain-agnostic)
  argus.tasking ── argus.ingest ── argus.core.store ── argus.impact ── argus.alert
        │
        ▼
PREDICTION ENGINE (Predictor protocol)
  OilTrajectory  WQForecast  AnomalyDetector  FloodRisk  AcidDepositionRisk
        │
        ▼
AI ASSISTANT (grounded, read-only)
  SituationReporter  QueryPipeline  AnomalyExplainer
        │
        ▼
API + FRONTEND
  FastAPI (21 endpoints)   React 19 + Vite 8 dashboard (12 pages)
```

### The spine is permanent; domains are pluggable

The spine never changes for a new domain. Adding D5 would mean creating one new directory
under `argus/domains/` with a class implementing `Domain` (three methods: `search`, `acquire`,
`analyze`). The rest of the system picks it up automatically.

### The store is the backbone

All stages communicate by writing and reading durable records in SQLite — never shared
in-memory state. This means every step is:
- **Inspectable**: you can query the store directly with any SQLite client
- **Re-runnable**: stages are idempotent
- **Debuggable**: you can replay any analysis from the stored inputs

---

## 3. Data Flow: From Satellite to AI Report

Here's what happens when Argus processes a new oil slick detection:

```
1. AOI configured in config/aois/tobago.geojson
         │
2. argus.tasking.runner decides D1 is due; calls domain.search()
         │
3. D1 domain.search() queries CDSE STAC for Sentinel-1 IW GRD products
   over the AOI bounding box in the requested time window
         │
4. domain.acquire(ref) downloads the scene via CDSE Process API (subset)
   → Scene stored in argus.db.scenes; bytes counted against daily quota
         │
5. domain.analyze(acq) runs the pipeline:
   preprocess.sar() → σ⁰ dB conversion, land mask
   detector.detect() → threshold-based dark-spot candidates
   segmentor.segment() → polygon refinement
   features.extract() → backscatter stats, aspect ratio, texture
   classifier.classify() → look-alike rejection; confidence score
   → Observation(obs_type="oil_slick", evidence_class="measured",
                  geometry=Polygon, area_km2=5.1, confidence=0.85)
   → stored in argus.db.observations
         │
6. OilTrajectory predictor picks up the observation (via store)
   → loads metocean forcing (CMEMS currents + Open-Meteo winds)
   → spawns OpenOil subprocess (GPL-isolated): simulate_particles()
   → ForecastFrame[] stored per timestep (T+6h, T+12h, … T+72h)
   → Prediction(kind="trajectory", uncertainty={particle_spread_km: 18.0})
         │
7. impact.assessor intersects trajectory frames with exposure layers
   → ImpactAssessment(eta_hours=24, metrics={coast_length_km: 12.5})
         │
8. alert.delivery checks trigger conditions → fires webhook/email if met
         │
9. API serves everything:
   GET /aois/tobago/observations → the oil slick
   GET /aois/tobago/predictions  → the trajectory + ForecastFrames
   GET /aois/tobago/impact       → the coast ETA
         │
10. AI layer: GET /waterbody/lake-nariva/report
    SituationReporter queries store for last 30 days of observations
    GroundingGuard validates every factual claim has a record_id
    Generates: "An oil slick (obs-abc123) of 5.1 km² was detected at 85%
    confidence on 2024-02-07. Trajectory modelling projects coastline
    contact within 24 hours (ia-001)."
    citations = ["obs-abc123", "ia-001"]
```

---

## 4. Domain Details

### D1 — Marine Oil (`argus/domains/marine_oil/`)

**Data source:** Sentinel-1 IW GRD (SAR C-band), acquired via CDSE Process API

**Pipeline:**
1. `sar.preprocess()` — calibrate to σ⁰ dB; apply land mask from GSHHG coastline
2. `segmentor.segment()` — adaptive threshold, connected-component labeling
3. `features.extract()` — shape (area, perimeter, compactness), texture (GLCM contrast),
   backscatter statistics
4. `classifier.classify()` — SVM look-alike rejection trained on labeled spills vs.
   biogenic films, rain cells, ship wakes

**Output:** `Observation(obs_type="oil_slick", evidence_class="measured")`

**Files:** `argus/domains/marine_oil/{detector,segmentor,features,classifier}.py`

---

### D2 — Inland Water Quality (`argus/domains/inland_wq/`)

**Data source:** Sentinel-2 MSI / Sentinel-3 OLCI (optical), acquired via CDSE

**Pipeline:**
1. `optical.preprocess()` — atmospheric correction (simplified), water masking
2. `indices.calculate()` — NDCI (chlorophyll proxy), turbidity from red band, CDOM from
   blue/green ratio, surface temperature from thermal band
3. Each index becomes an `Observation` with `obs_type ∈ {chlorophyll_a, turbidity, cdom, surface_temp}`

**Evidence class:** `"measured"` — but note these are optical proxies. Absolute values depend
on calibration. Values are accurate relative to each other within a water body.

**Files:** `argus/domains/inland_wq/{analyzer,indices}.py`

---

### D3 — Weather/Hydro (`argus/domains/weather_hydro/`)

**Data sources:**
- Open-Meteo API (precipitation forecast, ERA5 reanalysis, GloFAS discharge, air quality SO₂/NO₂)
- Sentinel-5P (atmospheric column NO₂/SO₂) — stub, requires CDSE access
- SAR inundation mapping — stub, requires live Sentinel-1 access

**Output observation types:**
- `precip_series` (evidence_class: `"modeled"` for forecasts, `"measured"` for ERA5 historical)
- `discharge_series` (evidence_class: `"modeled"`)
- `so2_series`, `no2_series` (evidence_class: `"modeled"`)

**Open-Meteo attribution:** CC BY 4.0 required in all outputs containing this data. The API
automatically adds `_attribution: "Weather data by Open-Meteo.com (CC BY 4.0)"` to all
affected endpoint responses.

**Files:** `argus/domains/weather_hydro/{analyzer,open_meteo,s5p,inundation}.py`

---

### D4 — Hydrological Choke Points (`argus/domains/hydro_chokepoints/`)

**Data source:** Copernicus DEM GLO-30 (30m global DEM) + HydroSHEDS flow networks

**Pipeline:**
1. `dem_processor.process()` — fill sinks, compute flow direction (D8 algorithm)
2. `constriction.find_choke_points()` — flow accumulation above threshold; identify nodes
   where high accumulation passes through narrow channel sections
3. `constriction_score` — normalized metric 0–1: 1.0 = maximum restriction

**Evidence class:** Always `"inferred"` — these points are derived from DEM modelling, not
directly observable from orbit.

**Files:** `argus/domains/hydro_chokepoints/{analyzer,dem_processor,constriction}.py`

---

## 5. Predictor Details

All predictors implement the `Predictor` protocol in `argus/predict/base.py`:
```python
class Predictor(Protocol):
    predictor_id: str
    def predict(self, ctx: PredictContext, rng_seed: int) -> Prediction: ...
    def validate(self, history: EvalSet) -> SkillReport: ...
```

The `validate()` method runs against historical observations and returns a `SkillReport`.
The skill gate (`argus/eval/skill_gate.py`) filters the `/waterbody/{id}/forecasts` endpoint
to only return predictions from predictors with `passed_gate=True`.

### OilTrajectory (`argus/predict/oil_trajectory/`)

**Algorithm:** OpenDrift particle simulation (GPLv2). Runs in an isolated subprocess
(`sim_worker.py`) to prevent GPL licence contamination of the main process.

**Inputs:** Oil slick observation (seed position), metocean forcing (CMEMS currents + Open-Meteo
winds, cached in `argus/predict/oil_trajectory/cache.py`)

**Output:** `Prediction(kind="trajectory")` with embedded `ForecastFrame[]` at T+6h intervals.
`uncertainty = {particle_spread_km: float}` — particle cloud spread at final frame.

**INV-5:** Oil type (`crude`, `bunker`, `diesel`, etc.) is always read from `config/oil_types.yaml`.
No default is permitted. Validation fails if `oil_type` is absent.

### WaterQualityForecast (`argus/predict/wq_forecast/`)

**Algorithm:** Gradient-boosted regression (scikit-learn). Trained per water body on
historical chl-a observations + Open-Meteo precipitation/temperature drivers.

**Output:** `Prediction(kind="forecast")` with 14-day bloom-risk scores + 90% confidence interval.

**Skill gate:** Must beat a persistence baseline (predicting tomorrow = today's value).
Failing predictors are excluded from the `/forecasts` endpoint.

### AnomalyDetector (`argus/predict/anomaly_detector/`)

**Algorithm:** STL (Seasonal-Trend decomposition using LOESS) on the per-lake WQ time series,
followed by z-score calculation on the residuals.

**Output:** `Prediction(kind="anomaly")` with `z_score` and `direction` (positive=elevated, negative=depleted).
Anomalies above 2.5σ trigger HAB alerts.

### FloodRisk (`argus/predict/flood_risk/`)

**Algorithm:** Weighted 3-component linear combination:
```
risk_score = 0.5 × precip_component + 0.3 × discharge_component + 0.2 × constriction_component
```
All components normalized to [0, 1]. Risk level thresholds: low < 0.35 · medium 0.35–0.55 ·
high 0.55–0.75 · extreme ≥ 0.75.

**Honesty label:** Always `"modeled flood risk (not a measured flood)"` — this is invariant.

### AcidDepositionRisk (`argus/predict/acid_deposition/`)

**Algorithm:** `acid_risk_index = SO₂_norm × NO₂_norm × precip_factor` scaled to 0–10,
where components are normalized against historical percentiles.

**Honesty label:** Always `"modeled acid-deposition risk index (0–10 scale) — NOT a pH measurement"`.

---

## 6. The AI Pipeline

### Grounding Guard (`argus/ai/grounding.py`)

The `GroundingGuard` is the single most important safety component. It validates that every
factual environmental claim in AI-generated text contains a reference to a real record ID
in the store. Ungrounded claims are rejected and logged as defects.

The guard works by:
1. Maintaining a set of valid record IDs for the current scope (AOI + time window)
2. Scanning AI output for citation patterns (`[record_id]`)
3. Verifying each cited ID exists in the store
4. Rejecting or flagging output that makes claims without citations

### ArgusAIClient (`argus/ai/client.py`)

Wraps the Anthropic API. When `ARGUS_AI_OFFLINE=true` (or API unavailable), falls back to
`argus/ai/fallback.py` which generates deterministic templated text. The `model` field in
all responses returns `"template"` in fallback mode.

### SituationReporter (`argus/ai/reports.py`)

Called by `GET /waterbody/{target_id}/report`. Queries the store for the last 30 days of
observations for the target, formats them into a structured context, calls the AI client,
runs the grounding guard on the output, returns `GroundedText(text, citations[])`.

### QueryPipeline (`argus/ai/query.py`)

Called by `POST /query`. Two-phase:
1. **Write-action detection**: keyword scan for write intent ("run", "update", "delete", "trigger").
   If detected, returns a polite refusal immediately without an LLM call.
2. **Store query**: translates the question to a structured `StoreQuery`, executes it,
   formats results, generates a grounded answer.

### AnomalyExplainer (`argus/ai/anomaly_explain.py`)

Called by `GET /anomaly/{prediction_id}/explanation`. Looks up the anomaly prediction and its
source observations, generates a hypothesis (candidate cause) and an advisory (recommended actions).
The output always carries `confidence: "low"|"medium"|"high"` and is always labeled as advisory.

---

## 7. The Store (SQLite)

All data lives in `argus.db` (or the path specified via `--db-path`). All access goes through
`argus/core/store.py`. No other module imports `sqlite3` directly (INV-6).

**Key tables:**
| Table | Contents |
|---|---|
| `aoi` | Configured areas of interest (loaded from config/ at each startup) |
| `analysis_runs` | One row per domain run: aoi_id, domain_id, started_at, status |
| `scenes` | Acquired satellite scenes: scene_id, bytes, product_id |
| `observations` | All domain outputs: obs_type, evidence_class, geometry, confidence |
| `predictions` | All predictor outputs: predictor_id, kind, evidence_class, uncertainty |
| `forecast_frames` | OilTrajectory frames: prediction_id, valid_at, footprint |
| `impact_assessments` | Exposure intersections: prediction_id, eta_hours, metrics |
| `exposure_layers` | Static exposure features (coastlines, intakes, MPAs) |
| `choke_points` | D4 outputs: location, constriction_score, upstream_area_km2 |
| `run_history` | Per-domain run summaries for the observability dashboard |

**Inspecting the store directly:**
```bash
sqlite3 argus.db ".tables"
sqlite3 argus.db "SELECT obs_type, evidence_class, confidence FROM observations LIMIT 10;"
```

---

## 8. The Frontend Architecture

### File structure

```
frontend/src/
├── api/
│   ├── client.ts      — typed fetch() wrapper; base URL from import.meta.env
│   ├── endpoints.ts   — 19 typed fetch functions (one per endpoint group)
│   └── types.ts       — TypeScript types mirroring Pydantic schemas
├── store/
│   ├── aoiStore.ts    — selectedAOI (AOISchema | null), selectedObservation
│   ├── mapStore.ts    — activeLayers: Set<string>
│   └── uiStore.ts     — sidebarOpen: boolean
├── components/
│   ├── layout/        — AppShell (skip nav, role=main), Header (AOI select), Sidebar (12 links)
│   ├── map/           — ArgusMap (react-leaflet), LayerManager (Escape-dismiss floating panel)
│   ├── charts/        — WQTrendChart (Recharts), FloodRiskGauge, AcidRiskGauge, QuotaGauge
│   ├── ai/            — AIReportPanel (numbered citations), NLQueryBox (thinking-dot animation)
│   ├── domain/        — DomainStatusGrid, EvidenceClassBadge, RiskLevelBadge
│   └── ui/            — badge, button, card (5 variants), empty-state, metric-card,
│                        skeleton (5 content-shaped variants), spinner
└── pages/             — 12 page components (see Architecture doc §3)
```

### State management

**TanStack Query** handles all server state: caching, background refresh, loading/error states.
Each page declares its own queries with explicit `queryKey` arrays for cache invalidation.
The Header's "Refresh" button calls `queryClient.invalidateQueries()` to force a full refresh.

**Zustand** stores hold only client state that needs to be shared across components:
- `aoiStore.selectedAOI` — drives all AOI-scoped queries via `enabled: !!aoiId`
- `mapStore.activeLayers` — controls which layer groups the Leaflet map renders
- `uiStore.sidebarOpen` — sidebar collapse state

**No global state for server data** — everything goes through React Query. Components fetch
their own data; the store does not cache API responses.

### Map architecture (React Leaflet)

`ArgusMap` renders:
- **CartoDB Dark Matter** basemap (tile layer)
- **Observation layer** — GeoJSON polygons from `/aois/{id}/observations`
- **Choke points layer** — circle markers from `/aois/{id}/choke-points`
- **Trajectory layer** — GeoJSON polygons from `/aois/{id}/predictions` frames (animated in
  PredictionsPage via frame index)

The `activeLayers` Zustand store controls which `LayerGroup` components are rendered.
`LayerManager` is a floating panel that renders `Eye`/`EyeOff` toggles for each layer.

---

## 9. Test Philosophy

56 test files · 1072 tests · run with `pytest tests/`

**Offline by default:** No test in the default suite makes a network call. Live tests are
decorated with `@pytest.mark.live` and excluded by the `addopts = "-m 'not live'"` in
`pyproject.toml`. This is INV-7.

**Fixture-based:** Each test creates its own in-memory SQLite store via `conftest.py`.
No shared state between tests. No database mocking — tests use real SQLite with real schemas.

**Contract tests:** `tests/test_api_contracts.py` locks the response schema of every D1
endpoint. Any breaking field removal fails immediately.

**AI layer tests:** Use `ARGUS_AI_OFFLINE=true` + recorded responses. No live Anthropic API
in the default suite.

**Skill gate tests:** `tests/test_skill_gate.py` verifies that predictors without a passing
`SkillReport` are filtered from the `/forecasts` endpoint.

**Coverage areas by file:**

| File pattern | What it covers |
|---|---|
| `test_oil_*.py`, `test_classifier.py` | D1 detection pipeline |
| `test_oil_trajectory*.py`, `test_forecast_frames.py` | OilTrajectory predictor |
| `test_inland_wq_*.py`, `test_wq_*.py` | D2 domain + WQ predictors |
| `test_nl_*.py`, `test_grounding_*.py`, `test_anomaly_explain.py` | AI layer |
| `test_choke_points.py`, `test_flood_risk.py`, `test_acid_deposition.py` | D3/D4 |
| `test_api*.py`, `test_health.py` | API contract |
| `test_scheduler.py`, `test_observability.py` | Phase 8 automation |

---

## 10. Design Decisions — ADR Index

| ADR | Decision | Status |
|---|---|---|
| ADR-0001 | Vertical-slice architecture + pipeline pattern | Accepted |
| ADR-0002 | Data and simulation stack (SQLite, OpenDrift subprocess) | Accepted |
| ADR-0003 | Water health platform + domain plug-in pattern | Accepted |
| ADR-0004 | Prediction + AI layer architecture | Accepted |
| ADR-0005 | MVP redefined to full platform (no Vertical-Slice MVP) | Accepted |
| ADR-0006 | Oil type is always configurable; no default | Accepted |
| ADR-0007 | APScheduler for domain automation (quota-aware) | Accepted |
| ADR-0008 | Production deployment: Vercel + GCP Cloud Run + GCS | Accepted |

Full ADR texts: `docs/adr/`

---

## 11. How to Add a New Domain

Adding a new observation domain (e.g. D5 Groundwater) requires **3 files** and **0 spine edits**:

**Step 1:** Create the domain directory and implement the `Domain` protocol:

```python
# argus/domains/groundwater/analyzer.py
from argus.domains.base import Domain, Acquisition, SourceRef
from argus.core.models import MonitorTarget, Observation

class GroundwaterDomain(Domain):
    domain_id = "groundwater"

    def search(self, target: MonitorTarget, t0, t1) -> list[SourceRef]:
        # Query your data source for available products
        ...

    def acquire(self, ref: SourceRef) -> Acquisition:
        # Download and return the raw data product
        ...

    def analyze(self, acq: Acquisition) -> list[Observation]:
        # Process and return observations
        # Always set evidence_class per INV-3
        return [Observation(
            obs_type="water_level",
            evidence_class="modeled",  # or measured/inferred
            ...
        )]
```

**Step 2:** Register the domain in `argus/domains/__init__.py` (or wherever the registry lives)

**Step 3:** Add test file `tests/test_groundwater_domain.py`

**What you do NOT need to change:**
- `argus/core/store.py` — store handles any domain's observations automatically
- `argus/api/` — observations are served by the existing `/aois/{id}/observations` endpoint
- `argus/ai/` — the AI layer reads any observations from the store
- `argus/alert/` — alert conditions can reference the new obs_type via config
- The frontend — new observations appear on the map automatically via the observation layer

---

## 12. How to Add a New Predictor

Adding a new predictor requires **2 files**:

**Step 1:** Implement the `Predictor` protocol:

```python
# argus/predict/my_predictor/predictor.py
from argus.predict.base import Predictor, PredictContext, Prediction, SkillReport, EvalSet

class MyPredictor(Predictor):
    predictor_id = "my_predictor_v1"

    def predict(self, ctx: PredictContext, rng_seed: int) -> Prediction:
        # Must populate uncertainty (INV-9)
        return Prediction(
            predictor_id=self.predictor_id,
            kind="forecast",
            evidence_class="modeled",  # always modeled for predictions
            uncertainty={"my_metric": 0.15},  # must be non-empty
            ...
        )

    def validate(self, history: EvalSet) -> SkillReport:
        # Return SkillReport(passed_gate=True/False)
        # Must beat a persistence baseline
        ...
```

**Step 2:** Add test file `tests/test_my_predictor.py`

**Key invariants for predictors:**
- `evidence_class` must always be `"modeled"` (INV-3)
- `uncertainty` must always be present and non-empty (INV-9)
- `rng_seed` must be used for any stochastic operation (INV-8)
- The predictor appears in `/waterbody/{id}/forecasts` only after `validate()` returns
  `passed_gate=True`
