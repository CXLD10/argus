# Phase 3 — Impact, Delivery & Viewer (Oil)

- **Status:** Specced; waiting for Phase 2
- **Priority:** P0
- **Last updated:** 2026-06-27
- **Depends on:** Phase 2 complete
- **Related:** [phase-2.md](phase-2.md) · [ARCHITECTURE.md](../architecture/ARCHITECTURE.md)
- **Checkpoint:** Completes CP-1 (oil pipeline end-to-end)

**Goal:** Close the oil pipeline end-to-end: impact assessment, HTTP API, web viewer,
and alert delivery. After Phase 3, D1 oil is fully operational (detect → predict → impact
→ alert → viewer). Internal checkpoint CP-1.

---

## F-014 — Exposure Layers + Impact Assessment + ETA

**Why:** Trajectory footprints are useful only when tied to what they might affect.

**Depends on:** F-013 (ForecastFrames available)

**Owns / creates:**
- `argus/impact/__init__.py`
- `argus/impact/assessor.py`
- `argus/core/models.py` (add `ExposureLayer`, `ImpactAssessment`)
- `argus/core/store.py` (add ExposureLayer, ImpactAssessment CRUD)
- `data/static/exposure/coastline_tobago.geojson`
- `data/static/exposure/mpas_tobago.geojson`
- `tests/test_impact_assessor.py`

**Exposure types (MVP D1):** coastline, marine_protected_area

**Algorithm:**
- For each `ForecastFrame` (ordered by `valid_at`): intersect `footprint` with each
  `ExposureLayer.geometry_ref`
- First intersection = ETA; record `ImpactAssessment.valid_at` = that frame's valid_at
- `metrics.coast_length_km`, `metrics.mpa_area_km2`, `metrics.eta_hours`

**Acceptance criteria:**
- Synthetic trajectory footprint that intersects coastline polygon → `ImpactAssessment` with `valid_at` set
- Trajectory that misses all exposure → no `ImpactAssessment` (not a zero-value record)

---

## F-015 — FastAPI Service

**Why:** Expose all pipeline outputs over HTTP for the viewer and external consumers.

**Depends on:** F-014

**Owns / creates:**
- `argus/api/__init__.py`
- `argus/api/app.py` (FastAPI application factory)
- `argus/api/routers/aoi.py`
- `argus/api/routers/observations.py`
- `argus/api/routers/predictions.py`
- `argus/api/routers/impact.py`
- `argus/api/schemas.py` (Pydantic response models)
- `tests/test_api.py`

**Endpoints (MVP D1):**
- `GET /aois` — list AOIs
- `GET /aois/{id}/observations` — list Observations with filters
- `GET /aois/{id}/predictions` — list Predictions (trajectory ForecastFrames)
- `GET /aois/{id}/impact` — ImpactAssessments
- `GET /health` — readiness probe

**Rules:**
- All responses include `_attribution` field when Open-Meteo data is involved
- No authentication at MVP (single-operator local tool)

**Acceptance criteria:**
- All GET endpoints return 200 on seeded test data
- Response schemas are Pydantic-validated
- `GET /health` always returns 200

---

## F-016 — Web Viewer (Detection + Forecast + Impact)

**Why:** Make the pipeline outputs visible on a map.

**Depends on:** F-015

**Owns / creates:**
- `argus/api/static/index.html`
- `argus/api/static/app.js`
- `argus/api/static/style.css`

**Implementation:**
- Static Leaflet/MapLibre page served by FastAPI as static files
- Panels: detection polygons (colored by confidence), trajectory footprint heatmap,
  impact intersection highlight, ETA text
- All data loaded from GET endpoints (no hardcoded data in JS)

**Acceptance criteria:**
- `argus serve` starts; accessing `http://localhost:8000` shows the map
- Detection polygons from tobago fixture visible on the map
- Trajectory footprint visible when ForecastFrames exist

---

## F-017 — Alert Delivery + Product Export

**Why:** Close the pipeline with operational alerting and portable outputs.
Internal CP-1 checkpoint.

**Depends on:** F-016

**Owns / creates:**
- `argus/alert/__init__.py`
- `argus/alert/delivery.py` (webhook + email; explicit config required)
- `argus/export/products.py` (extend for full pipeline outputs: GeoJSON + PNG + metadata)
- `config/alert_channels.yaml` (template; not committed with real credentials)
- `tests/test_alert_delivery.py`

**Alert rules:**
- No alert sent without explicit channel configured in `alert_channels.yaml`
- Alert payload includes: domain, target, observation/prediction id, confidence, ETA
- `Alert.status` tracks pending/sent/failed

**Acceptance criteria:**
- Webhook alert: mocked HTTP endpoint receives correctly-structured payload
- Email alert: mocked SMTP sends correct subject/body
- No alert sent when no channel configured (graceful no-op)
- Product export: GeoJSON + PNG + JSON metadata written to artifacts dir

## Phase 3 Definition of Done

- [ ] F-014–F-017 acceptance criteria met
- [ ] `argus serve` starts and map renders on localhost
- [ ] Webhook alert fires successfully in offline test
- [ ] CP-1 internal checkpoint: complete D1 oil pipeline (detect → trajectory → impact → alert → viewer)
