# Phase 10 — Production UI/UX Dashboard

- **Status:** Specced; waiting for Phase 9
- **Priority:** P0 (required for MVP)
- **Last updated:** 2026-06-27
- **Features:** F-045–F-051
- **Depends on:** Phase 9 complete (all domains operational)
- **Related:** [phase-9.md](phase-9.md) · [phase-11.md](phase-11.md) · [API_SPEC.md](../api/API_SPEC.md)
- **Checkpoint:** Starts CP-4 (production ready)

**Goal:** Build a polished, production-quality UI/UX dashboard that demonstrates the complete
Argus Environmental Intelligence Platform. This is NOT a prototype or a map with overlays —
it is a full product dashboard with multiple panels, data visualizations, AI assistant
interface, and an administrative panel.

**Technology:** React (Vite) + Tailwind CSS + Leaflet/MapLibre served by FastAPI as static
files. All processing on the backend; frontend is a pure presentation layer.

---

## F-045 — Frontend Framework + Build Pipeline

**Why:** The Phase 0–9 viewer (plain HTML + vanilla JS) is not production-quality. A modern
component-based framework is required for a polished dashboard.

**Depends on:** F-044

**Owns / creates:**
- `frontend/` (React + Vite project)
- `frontend/src/` (React components)
- `frontend/vite.config.js`
- `Makefile` (extend: `build-frontend`, `dev-frontend`)
- FastAPI serves `frontend/dist/` as static files
- `tests/test_frontend_build.py` (smoke: build succeeds; bundle exists)

**Cost validation:** React, Vite, Tailwind CSS are open-source; no paid UI library.

**Acceptance criteria:**
- `make build-frontend` produces `frontend/dist/` without errors
- `argus serve` serves the built frontend at `http://localhost:8000`
- All API endpoints accessible from the frontend (no CORS errors)

---

## F-046 — Multi-Domain Overview Dashboard

**Why:** The home screen must show the health of all monitored water bodies and AOIs at a glance.

**Depends on:** F-045

**Owns / creates:**
- `frontend/src/pages/Overview.jsx`
- `frontend/src/components/DomainStatusCard.jsx`
- `frontend/src/components/WaterBodySummaryTable.jsx`
- `frontend/src/components/AlertBadge.jsx`

**Overview panels:**
- Map: all water bodies color-coded by current status (normal/warning/alert)
- Domain status cards: D1/D2/D3/D4 — last run, scene count, open alerts
- Water body summary table: ranked by risk (anomaly severity × forecast trend)
- Recent alerts ticker

**Acceptance criteria:**
- All domains visible on the overview map simultaneously
- Water body table sortable by risk level
- Domain status shows "last updated" timestamp

---

## F-047 — Water Quality Monitoring Dashboard

**Why:** The D2 inland water quality domain is the most data-rich; needs a dedicated panel.

**Depends on:** F-046

**Owns / creates:**
- `frontend/src/pages/WaterBodyDetail.jsx`
- `frontend/src/components/WQTrendChart.jsx` (recharts or Chart.js)
- `frontend/src/components/AnomalyTimeline.jsx`
- `frontend/src/components/BloomRiskForecastBar.jsx`

**Panels:**
- Multi-metric time series: chl-a, turbidity, CDOM, surface temp (last 90 days)
- Anomaly timeline with sigma labels
- 7-day bloom-risk forecast with CI bands
- Impact panel: nearby intakes/recreation sites status
- NL report panel (AI-generated, cited)

**Acceptance criteria:**
- Chart renders from real (fixture) observation data
- CI bands visible on forecast chart
- Anomaly spikes highlighted on time series

---

## F-048 — Hazard Prediction Dashboard

**Why:** D1 oil trajectory, D3 flood risk, D3 acid risk, and D4 choke points need a unified
hazard view.

**Depends on:** F-047

**Owns / creates:**
- `frontend/src/pages/HazardView.jsx`
- `frontend/src/components/TrajectoryPlayer.jsx` (time-step animation of ForecastFrames)
- `frontend/src/components/FloodRiskMap.jsx`
- `frontend/src/components/AcidRiskLayer.jsx`
- `frontend/src/components/ChokePointLayer.jsx`

**Panels:**
- Oil trajectory: animated particle footprint stepping through ForecastFrames
- Flood risk: choke-point map with risk color scale
- Acid risk: catchment map with index value
- All hazards: ETA countdown for active impacts

**Acceptance criteria:**
- Trajectory animation plays through ForecastFrames (fixture data)
- Choke-point layer renders with constriction_score color scale
- All evidence labels visible (modeled risk, not measurement)

---

## F-049 — AI Assistant Interface

**Why:** Non-specialists need to query the platform and read AI-generated reports in a clean UI.

**Depends on:** F-048

**Owns / creates:**
- `frontend/src/pages/Assistant.jsx`
- `frontend/src/components/NLQueryBox.jsx`
- `frontend/src/components/GroundedAnswerPanel.jsx`
- `frontend/src/components/CitationViewer.jsx`
- `frontend/src/components/ReportViewer.jsx`

**UX:**
- Query box: type a question; shows structured query that was executed (transparency)
- Answer panel: answer text with inline citation links (click to see record)
- Citation viewer: slide-out showing the cited record details
- Report viewer: formatted NL report with collapsible citation list
- AI label: all AI content clearly labeled "AI-generated · Grounded · [record citations]"

**Acceptance criteria:**
- Query → answer with citations renders from fixture API response
- Citation links open the source record (inline)
- AI label visible on all AI-generated content (cannot be hidden)

---

## F-050 — System Administration Panel

**Why:** Operators need to manage AOIs, water bodies, alert rules, and domain configuration
without editing YAML files.

**Depends on:** F-049

**Owns / creates:**
- `frontend/src/pages/Admin.jsx`
- `frontend/src/components/AOIManager.jsx`
- `frontend/src/components/AlertRuleEditor.jsx`
- `frontend/src/components/DomainToggle.jsx`
- `argus/api/routers/admin.py` (write endpoints: PUT /aoi, POST /aoi, PUT /alert-rules)

**Acceptance criteria:**
- AOI list shows all AOIs with enabled domains
- Domain toggles update AOI.domains via API
- Alert rule editor saves threshold changes to config (not in-memory only)

---

## F-051 — Export + Reporting UI

**Why:** Operators need to generate portable reports and download data products.

**Depends on:** F-050

**Owns / creates:**
- `frontend/src/pages/Export.jsx`
- `frontend/src/components/ReportGenerator.jsx`
- `argus/api/routers/export.py` (extend: PDF report endpoint)
- `argus/export/pdf.py` (if needed; use reportlab/weasyprint — open-source)

**Exports:**
- PDF situation report (NL report + charts + map)
- GeoJSON: all observations/predictions for a water body + time window
- PNG: map snapshot with all layers active

**Acceptance criteria:**
- PDF report generated from fixture data; includes Open-Meteo attribution
- GeoJSON export contains correct schema (evidence_class, citations)

## Phase 10 Definition of Done

- [ ] F-045–F-051 acceptance criteria met
- [ ] `make build-frontend` produces a clean production build
- [ ] All dashboard pages render without console errors
- [ ] Evidence labels visible on all modeled/inferred values
- [ ] AI content clearly labeled throughout the UI
