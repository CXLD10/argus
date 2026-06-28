# Argus — Demo Mode Guide

- **Audience:** Developers, presenters, evaluators
- **Last updated:** 2026-06-29
- **Purpose:** How to demonstrate Argus using fixture data without a live satellite feed

---

## What Demo Mode Is

Argus ships with a complete set of realistic fixture data in `frontend/src/lib/fixtures.ts`.
This data represents a marine oil incident scenario in the Gulf of Paria, Trinidad — a real
coastal zone with documented maritime traffic and historical spill risk.

Demo mode allows you to run a fully interactive demonstration of the platform's capabilities
without:
- A CDSE account
- Live satellite imagery downloads
- An active Open-Meteo quota
- An Anthropic API key

The backend API still needs to run (to serve the frontend), but the frontend falls back to
fixture data when API responses are empty.

---

## Fixture Data Overview

**Location:** `frontend/src/lib/fixtures.ts`

### DEMO_AOI — Gulf of Paria, Trinidad

```
id: "gulf-paria-tt"
name: "Gulf of Paria — Trinidad & Tobago"
bbox: [-61.95, 10.05, -61.35, 10.70]
domains: ["marine_oil", "inland_wq", "weather_hydro", "hydro_chokepoints"]
```

### DEMO_OBSERVATIONS — 6 observations

| ID | Type | Evidence | Detail |
|---|---|---|---|
| obs-001 | oil_slick | measured | 5.1 km², 85% confidence, Sentinel-1 IW GRD |
| obs-002 | oil_slick | measured | 2.3 km², 72% confidence (older, fading) |
| obs-003 | chlorophyll_a | measured | 28.4 µg/L (elevated, anomaly detected) |
| obs-004 | chlorophyll_a | measured | 12.1 µg/L (baseline) |
| obs-005 | turbidity | measured | 18.7 NTU (moderate) |
| obs-006 | precip_series | modeled | 47.2 mm/24h (heavy precipitation event) |

### DEMO_FLOOD_RISK

```
risk_score: 0.71
risk_level: "high"
component_scores: {
  precip_component: 0.82,  ← driving factor
  discharge_component: 0.65,
  constriction_component: 0.58
}
uncertainty: { method: "weighted_linear_combination" }
honesty_label: "modeled flood risk (not a measured flood)"
```

### DEMO_ACID_RISK

```
acid_risk_index: 6.8
so2_component: 0.71
no2_component: 0.63
precip_factor: 1.52
uncertainty: { method: "index_product" }
honesty_label: "modeled acid-deposition risk index (0–10 scale) — NOT a pH measurement"
```

### DEMO_CHOKE_POINTS — 3 points

| ID | Score | Upstream Area | Location |
|---|---|---|---|
| chk-001 | 0.87 | 1240 km² | Caroni River outlet, Beetham |
| chk-002 | 0.61 | 680 km² | Couva industrial corridor |
| chk-003 | 0.45 | 310 km² | South Oropouche floodplain |

### DEMO_AI_REPORT

A realistic two-paragraph situation report for Gulf of Paria with:
- Citation `¹` → oil slick obs-001 (5.1 km², 85% confidence)
- Citation `²` → trajectory prediction traj-001 (ETA 24h, east coast contact)
- Citation `³` → flood risk flood-001 (risk_score=0.71, high)
- Triage summary: advisory (not incident declaration)
- Model field: `"claude-sonnet-4-6"` (or `"template"` in offline mode)

### DEMO_NL_RESPONSE

Example NL query answer for: "What oil slick detections happened in the last 7 days?"

```
answer: "Two oil slicks have been detected in the last 7 days.
  The most recent (obs-001¹) covers 5.1 km² at 85% confidence,
  detected at 10.32°N, 61.62°W on 2026-06-24 02:14 UTC.
  An older slick (obs-002²) measuring 2.3 km² at 72% confidence
  was detected two days prior at 10.28°N, 61.58°W."
citations: ["obs-001", "obs-002"]
```

---

## How to Run a Demo

### Option A — Fixture data only (frontend + empty backend)

This is the fastest way to run a demo. No satellite data required.

```bash
# Terminal 1: start the backend (serves the frontend, returns empty API responses)
source .venv/bin/activate
argus serve

# Terminal 2: start the frontend dev server
cd frontend
pnpm dev
```

Open `http://localhost:5173` in a browser.

The frontend will query the API and get empty responses for most endpoints. The demo fixtures
are displayed via the `useDemoFallback` hook in each page when the API returns empty arrays.

**Note:** As of v0.1.0, the fixtures are populated in `fixtures.ts` but the `useDemoFallback`
hook is not yet wired into all pages (TD-07). The Overview, Map, Oil Monitoring, and Predictions
pages show fixture data. Other pages may show empty states.

### Option B — Seeded database

For a more complete demo that shows all 12 pages with data:

```bash
# 1. Run the domain analysis against the fixture time window
argus run --aoi gulf-paria-tt --since 2026-06-17 --until 2026-06-24 --domain all

# 2. The store now has real (cached) observations
# 3. Start the server
argus serve

# 4. Start the frontend
cd frontend && pnpm dev
```

This fetches real archived Sentinel imagery from CDSE (requires CDSE credentials in env).
The fixture scenario matches this time window.

### Option C — Production build (demo-ready)

```bash
cd frontend
pnpm build
# Build output is at frontend/dist/
# The FastAPI server serves it automatically at http://localhost:8000/
argus serve
# Open http://localhost:8000/
```

---

## Demo Data Narrative

The Gulf of Paria scenario tells a coherent multi-hazard story:

**Primary incident:** A 5.1 km² oil slick detected south of the Caroni river mouth, likely
from maritime traffic transiting to the Pointe-à-Pierre refinery approach lane. The slick's
confidence (85%) is above the alert threshold. Trajectory modelling projects coastal contact
with the Beetham wetlands in approximately 24 hours.

**Compounding factor — flood:** Heavy precipitation (47.2 mm/24h) has elevated the Caroni
River discharge, pushing the Beetham choke point (score 0.87) toward its maximum restriction
capacity. Flood risk is elevated to "high" (0.71).

**Water quality concern:** Lake Nariva (inland, east coast) is showing chlorophyll-a at
28.4 µg/L — above the bloom-risk threshold. The anomaly detector has flagged this as
z-score +2.8σ above the seasonal baseline, triggering the HAB early-warning.

**Acid deposition:** SO₂ and NO₂ from the Pointe-à-Pierre industrial corridor, combined
with the heavy precipitation, yields an acid deposition risk index of 6.8 — in the "elevated"
band. Freshwater intakes south of Port of Spain are flagged for monitoring.

This narrative allows the presenter to walk through all four domains, all five predictors,
the AI assistant, the map, alerts, and the export functionality in a single coherent scenario.

---

## Customizing Fixture Data

Edit `frontend/src/lib/fixtures.ts` to modify the demo scenario. All fixtures are typed:

```typescript
// Example: change the oil slick confidence
export const DEMO_OBSERVATIONS: ObservationSchema[] = [
  {
    id: "obs-001",
    obs_type: "oil_slick",
    confidence: 0.85,          // ← change here
    evidence_class: "measured",
    area_km2: 5.1,
    // ...
  }
];
```

The TypeScript types live in `frontend/src/api/types.ts`. The `ObservationSchema`,
`PredictionSchema`, `FloodRiskResponse`, `AcidRiskResponse`, and `ChokePointSchema` types
match the Pydantic response schemas in `argus/api/schemas.py`.

---

## Known Demo Limitations

| Limitation | Status | Impact |
|---|---|---|
| `useDemoFallback` not wired in all pages | TD-07 (Phase 11) | Water Quality, Hydro, Choke Points pages may show empty states without a seeded DB |
| AI report requires `ARGUS_AI_KEY` env var or shows template mode | OQ-D | Demo shows "model: template" in offline mode — still functional |
| Map trajectory animation requires predictions in store | TD-07 | In Option A, trajectory player shows no frames |
| CDSE credentials required for Option B | — | Use Option A for credential-free demo |
