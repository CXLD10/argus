# Phase 7 — Platform Integration (D2 Full Pipeline)

- **Status:** Specced; waiting for Phase 6
- **Priority:** P0
- **Last updated:** 2026-06-27
- **Features:** F-034–F-036
- **Depends on:** Phase 6 complete
- **Related:** [phase-6.md](phase-6.md) · [phase-8.md](phase-8.md)
- **Checkpoint:** Completes CP-2 (WQ + prediction + AI end-to-end)

**Goal:** Bring D2 water quality fully through impact, viewer, AI, and alerting. Close the
CP-2 internal checkpoint: D2 water quality is fully operational end-to-end.

---

## F-034 — WQ Exposure (Drinking Intakes / Recreation) + Impact

**Why:** Bloom-risk forecasts are actionable only when tied to what is at risk.

**Depends on:** F-026 (WQ Observations), F-029 (Predictions)

**Owns / creates:**
- `argus/impact/assessor.py` (extend for WQ domain)
- `data/static/exposure/drinking_intakes_reference.geojson`
- `data/static/exposure/recreation_sites_reference.geojson`
- `argus/core/store.py` (extend ExposureLayer to support drinking_intake, recreation_site types)
- `tests/test_wq_impact.py`

**Algorithm:**
- When `AnomalyResult` or `Forecast` (bloom-risk) exceeds threshold:
  intersect water body geometry with ExposureLayers
  → `ImpactAssessment(metrics.intakes_threatened=N, metrics.eta_hours=...)`

**Acceptance criteria:**
- Reference lake with nearby intake: forecast above threshold → ImpactAssessment created
- No nearby exposure: no ImpactAssessment (correct non-event handling)

---

## F-035 — Viewer + API Extended to D2

**Why:** D2 outputs must be visible alongside D1 in the same viewer and API.

**Depends on:** F-034

**Owns / creates:**
- `argus/api/routers/observations.py` (extend: water body filter, obs_type filter)
- `argus/api/routers/predictions.py` (extend: WQ forecasts + anomalies)
- `argus/api/routers/ai.py` (extend: report endpoint for water bodies)
- `argus/api/static/app.js` (extend: water-body panel; trend chart; anomaly timeline; AI report sidebar)

**New viewer panels:**
- Water body list with status indicators (normal/warning/alert)
- Time series chart (chlorophyll-a, turbidity over last 90 days)
- Anomaly flag indicators on timeline
- 7-day bloom-risk forecast bar
- AI report panel (shows latest NL report)

**Acceptance criteria:**
- `argus serve` with reference_lake data: water body panel visible on map
- Trend chart renders from `/waterbody/{id}/observations`
- AI report renders from `/waterbody/{id}/report`

---

## F-036 — Alerting + Products for D2

**Why:** HAB early-warning alerts are a core user job-to-be-done (PRD §3).
Closes CP-2 internal checkpoint.

**Depends on:** F-035

**Owns / creates:**
- `argus/alert/delivery.py` (extend for WQ domain alerts)
- `argus/export/products.py` (extend: WQ product exports)
- `tests/test_wq_alert.py`

**HAB early-warning alert trigger:**
- `AnomalyResult.deviation > alert_threshold` AND `Forecast.value > bloom_risk_threshold`
- → `Alert` created; delivery to configured channels; payload includes impact summary

**WQ product exports:**
- GeoJSON of flagged water bodies with anomaly/forecast attributes
- PNG: water body map with bloom-risk color scale
- JSON summary: ranked water bodies by risk

**Acceptance criteria:**
- Anomaly above threshold + forecast above threshold → Alert created + delivered
- Alert payload includes: water body name, anomaly sigma, bloom-risk forecast, intakes_threatened
- Product exports created in artifacts dir

## Phase 7 Definition of Done

- [ ] F-034–F-036 acceptance criteria met
- [ ] CP-2 complete: D2 water quality end-to-end (ingest → analysis → anomaly + forecast → impact → AI report → alert → viewer)
- [ ] HAB early-warning alert fires correctly in offline test
- [ ] D1 and D2 both visible in viewer simultaneously
