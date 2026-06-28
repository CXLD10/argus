# Argus Environmental Intelligence Platform — Frontend Blueprint

- **Version:** 1.0
- **Created:** 2026-06-28
- **Status:** AUTHORITATIVE — single source of truth for Phase 10 frontend implementation
- **Phase coverage:** Phase 10 (F-045–F-051) implementation + Phase 11 frontend requirements
- **Backend baseline:** Phases 0–9 complete (F-000–F-044 committed)

This document replaces all prior informal frontend notes. All implementation decisions in
Phase 10 must be traceable to a section in this document. Updates require incrementing the
version and appending a change note to §19.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Product Capability Overview](#2-product-capability-overview)
3. [User Journeys](#3-user-journeys)
4. [Navigation Architecture](#4-navigation-architecture)
5. [Complete Dashboard Layout](#5-complete-dashboard-layout)
6. [Screen Inventory](#6-screen-inventory)
7. [Component Library](#7-component-library)
8. [API Integration Guide](#8-api-integration-guide)
9. [State Management](#9-state-management)
10. [Frontend Architecture](#10-frontend-architecture)
11. [Design System](#11-design-system)
12. [Technology Stack](#12-technology-stack)
13. [Data Visualization Guide](#13-data-visualization-guide)
14. [AI Experience](#14-ai-experience)
15. [Phase 10 Implementation Plan](#15-phase-10-implementation-plan)
16. [Phase 11 Frontend Requirements](#16-phase-11-frontend-requirements)
17. [Traceability Matrix](#17-traceability-matrix)
18. [Presentation Assets Checklist](#18-presentation-assets-checklist)
19. [Living Document Rules](#19-living-document-rules)

---

## 1. Executive Summary

### What Argus Is

Argus is a **Water Health Intelligence Platform** that fuses free Earth-observation and weather
data into actionable intelligence about water bodies and water-related hazards. It produces
grounded, AI-narrated situation reports across four environmental domains:

| Domain | ID | What it detects |
|---|---|---|
| Marine Oil | `marine_oil` | SAR-detected dark spots / oil slicks |
| Inland Water Quality | `inland_wq` | Algal blooms (chl-a, turbidity, CDOM, surface temp) |
| Weather / Hydro | `weather_hydro` | Precip series, river discharge, SO₂/NO₂ deposition |
| Hydro Choke Points | `hydro_chokepoints` | DEM-derived drainage constriction nodes |

### Current Implementation State

All backend phases are complete as of 2026-06-27:

| Milestone | Features | Status |
|---|---|---|
| Phase 0–3: Oil domain | F-000–F-017 | **DONE** |
| Phase 3.5: Hardening | F-018–F-023 | **DONE** |
| Phase 4–5: WQ + prediction | F-024–F-029 | **DONE** |
| Phase 6: AI layer | F-030–F-033 | **DONE** |
| Phase 7: Integration | F-034–F-036 | **DONE** |
| Phase 8: Automation | F-037–F-039 | **DONE** |
| Phase 9: D3+D4 + viewer | F-040–F-044 | **DONE** |
| **Phase 10: Production UI** | **F-045–F-051** | **TODO — this blueprint** |
| Phase 11: Validation/MVP | F-052–F-056 | FUTURE |

The current viewer (`argus/api/static/index.html` + `app.js`) is a functional
plain-HTML+Leaflet prototype that covers all 8 load functions but lacks:
- Multi-AOI support with switching
- Domain-specific drill-down panels
- Animated trajectory playback
- Time-series charts for WQ trends
- Full AI assistant UI with citation rendering
- Admin/config management
- Export workflows
- Mobile responsiveness

Phase 10 replaces the static viewer with a production React+Vite+Tailwind dashboard
served from `frontend/dist/` via FastAPI's static file mount.

### How to Use This Document

- **§2**: What capabilities exist to expose in the UI
- **§3**: User goals that drive screen priorities
- **§4–§6**: Routing, layout, and screen definitions
- **§7**: Every component with TypeScript props (implement these exactly)
- **§8**: Every API endpoint — how to call, what to expect
- **§9–§10**: State management and folder structure
- **§11–§12**: Visual language and technology decisions
- **§13–§14**: Chart types and AI UX patterns
- **§15**: Sprint-by-sprint implementation plan
- **§17**: Traceability from screen → requirement → API

---

## 2. Product Capability Overview

### 2.1 Domain Outputs (IMPLEMENTED — all in store)

#### D1: Marine Oil (`marine_oil`)

- **Observation types:** `oil_slick` (evidence_class: `measured`)
- **Predictor:** `OilTrajectory` (kind: `trajectory`)
  - Output: `ForecastFrame[]` — each frame has `footprint` (GeoJSON Polygon),
    `particle_count`, `stats` (mean_lon, mean_lat, spread_km, drift_km)
  - Uncertainty: ensemble spread metrics
- **Impact:** `ImpactAssessment[]` — ETA hours + metrics (coast_length_km, mpa_area_km2)
- **Alert gate:** `should_alert_hab()` not applicable; oil alerts via confidence + ETA
- **UI surfaces:** Oil overlay on map, trajectory animation, ETA cards, impact badges

#### D2: Inland Water Quality (`inland_wq`)

- **Observation types (all measured at Observation level):**
  - `chlorophyll_a` (evidence_class: `measured`) — µg/L, bloom proxy
  - `turbidity` (evidence_class: `measured`) — NTU
  - `cdom` (evidence_class: `measured`) — g/m³
  - `surface_temp` (evidence_class: `measured`) — °C
  - `bloom_presence` (evidence_class: `inferred`) — derived from elevated chl-a proxy
- **Predictors:**
  - `WaterQualityForecast` (kind: `forecast`) — 7-day bloom risk + 90% CI per water body
  - `AnomalyDetector` (kind: `anomaly`) — deviation z-score, direction (positive/negative)
- **Alert gates:**
  - HAB fires when z_score > 2.5σ AND forecast bloom > 25 µg/L
- **UI surfaces:** WQ trend chart, anomaly timeline, bloom forecast bar, AI situation report

#### D3: Weather/Hydrology (`weather_hydro`)

- **Observation types (all modeled):**
  - `precip_series` (evidence_class: `modeled`) — precipitation time series, Open-Meteo
  - `discharge_series` (evidence_class: `modeled`) — river discharge, GloFAS
  - `so2_series` (evidence_class: `modeled`) — SO₂ column, Open-Meteo air quality
  - `no2_series` (evidence_class: `modeled`) — NO₂ column, Open-Meteo air quality
- **Predictors:**
  - `FloodRisk` (kind: `risk`) — risk_level ∈ {low/medium/high/extreme}, risk_score 0–1
  - `AcidDepositionRisk` (kind: `risk`) — acid_risk_index 0–10 (NOT a pH measurement)
- **Alert gates:**
  - Flood: fires when risk_level ∈ {high, extreme}
  - Acid: fires when acid_risk_index ≥ 7.0
- **UI surfaces:** Risk level badge, acid index gauge, Open-Meteo CC BY 4.0 attribution

#### D4: Hydro Choke Points (`hydro_chokepoints`)

- **Output:** `ChokePoint[]` — DEM-derived drainage constriction nodes
  - `location` (GeoJSON Point), `upstream_area_km2`, `constriction_score` 0–1
  - evidence_class: always `inferred` — never `measured`
  - dem_source: `cop_glo30` (Copernicus GLO-30 DEM)
- **UI surfaces:** Circle markers on map, sorted by constriction_score desc

### 2.2 AI Layer (IMPLEMENTED — grounded)

All AI output carries `{text|answer|hypothesis, citations[], model, _attribution}`.
All claims in AI-generated text reference a record ID (INV-4). Ungrounded claims are defects.

| Endpoint | Function | UI surface |
|---|---|---|
| `GET /waterbody/{id}/report` | Situation report for one water body | ReportViewer panel |
| `GET /anomaly/{id}/explanation` | Hypothesis + advisory for anomaly | ExplanationCard |
| `POST /query` | Read-only NL query over store | NLQueryBox + GroundedAnswerPanel |

**Offline fallback:** When `ARGUS_AI_OFFLINE=true`, endpoints return templated text without
LLM inference. UI must render fallback text identically to live text; the `model` field
returns `"template"` in fallback mode.

### 2.3 Alert Pipeline (IMPLEMENTED)

| Alert type | Domain | Trigger | Message fields |
|---|---|---|---|
| HAB | `inland_wq` | z_score > 2.5σ AND bloom > 25 µg/L | domain, target, confidence, message, details |
| Flood risk | `weather_hydro` | risk_level ∈ {high, extreme} | Same; label = "not a measured flood" |
| Acid risk | `weather_hydro` | acid_risk_index ≥ 7.0 | Same; label = "NOT a pH measurement" |
| Oil (severity) | `marine_oil` | confidence-based, ETA-based | Same |

The alert delivery channel (webhook/email) is backend-configured. The frontend UI surfaces
alert history and current alert status; it does NOT trigger alerts.

### 2.4 Evidence Class Rules (INVARIANT — INV-3)

Every value displayed in the UI must reflect evidence_class. The UI must never imply that
modeled or inferred values were directly measured.

| evidence_class | Visual treatment | Required disclaimer |
|---|---|---|
| `measured` | No badge required | None required |
| `modeled` | "Modeled" badge (amber) | Source attribution (e.g. "Open-Meteo") |
| `inferred` | "Inferred" badge (blue) | Note derivation method (e.g. "DEM-derived") |

### 2.5 Open-Meteo Attribution (MANDATORY — CC BY 4.0)

Every screen or panel that displays weather/hydro predictions MUST include:

```
Weather data by Open-Meteo.com (CC BY 4.0)
```

This attribution is also present in API responses as `_attribution` field. Render it visibly
in the UI — not just in hover text. The footer of any weather/hydro panel is the canonical
placement.

---

## 3. User Journeys

Ten primary journeys mapped to the six PRD personas.

### Journey 1: Daily WQ Check (Municipal Water Officer)

**Persona:** Municipal water quality officer monitoring a reservoir used for drinking water.

**Goal:** Arrive at the dashboard each morning and within 30 seconds know if the reservoir is
normal or elevated risk.

**Steps:**
1. Open dashboard → see Overview screen with WQ domain status card
2. See AlertBadge if HAB gate triggered overnight
3. Click reservoir in WaterBodySummaryTable → navigate to WQ Monitoring screen
4. See chl-a trend chart (7-day), bloom risk forecast bar, anomaly flags
5. If anomaly present → click "Explain" → ExplanationCard with advisory
6. Print situation report PDF for department head

**Acceptance:** Reservoir risk state visible within 2 clicks from landing; AI advisory visible within 3.

### Journey 2: Oil Spill Response (Spill Coordinator)

**Persona:** Spill-response coordinator receiving a satellite-confirmed oil slick alert.

**Goal:** Determine where oil will be in 24 hours and what assets are at risk.

**Steps:**
1. Receive email/webhook alert with link → open Hazard screen for affected AOI
2. See oil slick footprint on map (red polygon, confidence-colored)
3. Click "Play Trajectory" → TrajectoryPlayer animates hourly frames
4. See ETA cards for coastline segments and MPAs in impact panel
5. Query AI: "Which MPA intersects the trajectory within 12 hours?" → GroundedAnswer
6. Export trajectory GeoJSON for GIS team

**Acceptance:** Trajectory animation plays without page reload; export runs in < 5 seconds.

### Journey 3: Beach Closure Decision (Public Health Official)

**Persona:** Public health official deciding whether to close a recreational beach.

**Goal:** Determine if bloom conditions at monitored water body exceed safe thresholds.

**Steps:**
1. Open WQ Monitoring screen for target water body
2. Read WQForecast bloom-risk chart: next 7 days, 90% CI band shown
3. Check AnomalyDetector z-score: if > 2.5σ alert badge is shown
4. Click "Situation Report" → AI report references observation IDs
5. Check citation links → verify evidence_class is `measured` or `inferred`

**Acceptance:** Evidence_class is visible for every cited value; CI band is labeled "90% confidence interval".

### Journey 4: Flood Preparedness (Stormwater Engineer)

**Persona:** Stormwater engineer assessing drainage capacity before a storm event.

**Goal:** Identify highest-risk choke points and current flood risk level.

**Steps:**
1. Open Hazard screen → select Flood Risk sub-panel
2. See FloodRisk risk_level badge (color-coded: green/amber/orange/red)
3. See choke-point layer on map (circles sized by constriction_score)
4. Click choke point → popup with upstream_area_km2, constriction_score, dem_source
5. Note "Modeled" and "Inferred" badges per INV-3
6. Note CC BY 4.0 Open-Meteo attribution in panel footer

**Acceptance:** Risk level and choke points visible on same map without toggling; INV-3 labels visible without tooltip inspection.

### Journey 5: AI Situation Query (Environmental Researcher)

**Persona:** Environmental NGO researcher querying the system without domain expertise.

**Goal:** Get a plain-language summary of current water quality across the monitored basin.

**Steps:**
1. Open AI Assistant screen
2. Type: "Summarize the current water quality status across all monitored water bodies."
3. See GroundedAnswerPanel with AI text + inline citation markers
4. Click citation → CitationViewer slides in showing referenced observation record
5. See model field ("claude-sonnet-4-6" or "template" if offline)
6. Optionally ask follow-up: "Which water body has the highest bloom risk today?"

**Acceptance:** Answer references at least one observation ID; citation panel shows obs_type, value, evidence_class, created_at.

### Journey 6: New AOI Setup (System Admin)

**Persona:** System administrator adding a new monitoring area.

**Goal:** Register a new AOI and enable domains without editing files on the server.

**Steps:**
1. Open Admin Panel → AOI Manager tab
2. Draw polygon on map or paste GeoJSON → fill name, ID, select domains
3. Click "Add AOI" → POST to backend (Phase 10 scope: UI only; backend may be file-based)
4. See new AOI appear in dropdown immediately
5. Enable/disable domains with DomainToggle switches

**Acceptance:** Form validates AOI geometry (non-empty, valid GeoJSON); domain toggles are visually distinct by domain_id.

### Journey 7: Domain Health Check (Operator)

**Persona:** On-call operator checking system health after a scheduled run.

**Goal:** Confirm all domain runs completed and quota is within limits.

**Steps:**
1. Open Overview Dashboard
2. See DomainStatusCard for each domain: last run time, status (complete/failed), scenes_fetched
3. See CDSE quota bar: MB used today / 1 GB limit
4. See Open-Meteo call counter: calls today / 10,000 limit
5. If domain shows "failed" → click to see error details
6. Read SystemStatusPanel: version, store accessible, last_analysis_run_at

**Acceptance:** Domain run timestamps update without page refresh (10-second poll); quota bars update in sync.

### Journey 8: Anomaly Triage (Emergency Responder)

**Persona:** Emergency responder receiving a HAB alert and needing to act quickly.

**Goal:** Understand what caused the anomaly and what action is recommended.

**Steps:**
1. Click notification link → navigate to Anomaly Explanation screen
2. See ExplanationCard: hypothesis (AI text), advisory (action recommended), confidence badge
3. See citation list referencing the triggering anomaly Prediction record
4. Read advisory: "ADVISORY — not a measurement. Human verification recommended."
5. Share explanation URL with supervisor

**Acceptance:** Confidence badge shows low/medium/high with color; advisory text always visible (not hidden behind accordion).

### Journey 9: GIS Export (Researcher)

**Persona:** Researcher wanting to import oil slick footprints into QGIS.

**Goal:** Export current oil observations and trajectory frames as GeoJSON.

**Steps:**
1. Open Export screen
2. Select domain: Marine Oil; format: GeoJSON; date range: last 7 days
3. Click "Export" → file download begins
4. Optionally export choke-point layer for watershed analysis
5. Optionally export WQ trend as CSV

**Acceptance:** GeoJSON download includes geometry + all schema fields; CSV includes obs_type, value, unit, evidence_class, created_at.

### Journey 10: Weekly Report (Decision Maker)

**Persona:** Regional water authority director reviewing weekly briefing.

**Goal:** Generate a one-page PDF summary for board meeting.

**Steps:**
1. Open Export screen → select "Situation Report PDF"
2. Select AOI and date range (past 7 days)
3. Preview rendered PDF in browser
4. Click "Download PDF"
5. PDF includes: map thumbnail, domain status summary, AI situation text, CC BY 4.0 footer

**Acceptance:** PDF renders in < 10 seconds for a single AOI; includes Open-Meteo attribution in footer.

---

## 4. Navigation Architecture

### 4.1 Route Hierarchy

```
/ (AppShell — persistent header + sidebar)
├── /overview                          Overview Dashboard (default)
├── /waterbody/:targetId               WQ Monitoring (per water body)
│   ├── /waterbody/:targetId           WQ Overview tab
│   ├── /waterbody/:targetId/anomaly/:predictionId   Anomaly Explanation
│   └── /waterbody/:targetId/report    AI Situation Report
├── /hazard                            Hazard Panel (AOI-scoped)
│   ├── /hazard/oil                    Oil Trajectory sub-panel
│   ├── /hazard/flood                  Flood Risk sub-panel
│   └── /hazard/acid                   Acid Risk sub-panel
├── /choke-points                      Choke Points (D4)
├── /ai                                AI Assistant
│   ├── /ai/query                      NL Query
│   └── /ai/report/:targetId           Situation Report viewer
├── /admin                             Admin Panel
│   ├── /admin/aois                    AOI Manager
│   ├── /admin/alerts                  Alert Rules
│   └── /admin/domains                 Domain Toggle
├── /export                            Export & Reporting
│   ├── /export/geojson                GeoJSON Export
│   ├── /export/csv                    CSV Export
│   └── /export/pdf                    PDF Report
└── * → /404                           Not Found
```

### 4.2 AOI Context

AOI selection is global state (Zustand store). All AOI-scoped API calls use `selectedAoiId`.
The AOI selector lives in the persistent header. Changing the AOI resets all query caches
for AOI-scoped keys and re-fetches.

### 4.3 Deep Linking

All routes are deep-linkable. Anomaly explanation pages (`/waterbody/:id/anomaly/:predId`)
must be shareable — they should fetch their own data independently.

### 4.4 Navigation UX Rules

- Active route highlighted in sidebar nav
- Breadcrumb visible on all drill-down screens (WQ → Waterbody Name → Anomaly)
- Back button on explanation and report screens returns to parent
- AOI name always shown in header when an AOI is selected

---

## 5. Complete Dashboard Layout

### 5.1 Overall Shell

```
┌─────────────────────────────────────────────────────────────────┐
│  HEADER (h-14, fixed)                                           │
│  [≡ Logo] Argus Environmental Intelligence    [AOI Selector ▾]  │
│  [Status Indicator]                           [Alert Bell 🔔]   │
└─────────────────────────────────────────────────────────────────┘
┌──────────┬──────────────────────────────────────────────────────┐
│ SIDEBAR  │  MAIN CONTENT AREA                                   │
│ (w-56,   │                                                      │
│  fixed)  │  ┌─────────────────────────────────────────────┐    │
│          │  │  MAP CANVAS (fills remaining space on hazard │    │
│ Nav items│  │  and choke-point screens; hidden on table-   │    │
│          │  │  only screens)                               │    │
│          │  └─────────────────────────────────────────────┘    │
│          │  ┌───────────────────────────────────────────┐      │
│          │  │  CONTENT PANEL (cards, tables, charts)    │      │
│          │  └───────────────────────────────────────────┘      │
└──────────┴──────────────────────────────────────────────────────┘
```

### 5.2 Header

| Element | Description |
|---|---|
| Logo + wordmark | "Argus" in brand font; links to /overview |
| Hamburger (mobile) | Collapses sidebar on < 768px |
| AOI Selector | Dropdown populated from `GET /aois`; persisted in Zustand |
| System Status Dot | Green/amber/red from `GET /health` polled every 30s |
| Alert Bell | Shows count of active alerts; click opens alert drawer |

### 5.3 Sidebar Navigation

```
──────────────────
Overview
Water Quality
  └── [water body list]
Hazard Map
  └── Oil
  └── Flood Risk
  └── Acid Risk
Choke Points
AI Assistant
──────────────────
Admin
Export
──────────────────
```

The WQ section expands to show all `target_ids` from `GET /waterbodies`.
Active item is highlighted with accent color left-border.

### 5.4 Map Canvas (Leaflet)

The map canvas is persistent on hazard/choke-point/overview screens. It is hidden on
admin, export, and AI assistant screens (full panel layout).

**Layer groups (all togglable):**

| Layer group | Default | Controlled by |
|---|---|---|
| `obsLayer` | ON | Observations toggle |
| `trajectoryLayer` | ON | Trajectory player |
| `impactLayer` | ON | Impact toggle |
| `wqLayer` | ON | WQ color coding |
| `chokeLayer` | ON | Choke points toggle |
| `floodRiskLayer` | ON | Flood risk overlay |
| `acidRiskLayer` | ON | Acid risk overlay |

**Map controls:**
- Dark basemap: CartoCDN dark_all (consistent with current viewer)
- Zoom controls top-left
- Layer control top-right
- Fullscreen button
- Scale bar bottom-left

### 5.5 Responsive Breakpoints

| Width | Layout |
|---|---|
| < 640px | Single column; sidebar as bottom nav sheet |
| 640–1024px | Sidebar collapsed (icon-only); map 50vh |
| > 1024px | Full sidebar + map + content panel |

---

## 6. Screen Inventory

### Screen 1: Overview Dashboard (`/overview`)

**Purpose:** At-a-glance system health + all-domain status.

**Primary components:**
- `DomainStatusGrid` — 4 cards (one per domain)
- `WaterBodySummaryTable` — all target_ids with latest risk color
- `AlertFeedPanel` — recent active alerts
- `SystemStatusPanel` — version, store, last run, quota bars
- `QuotaBar` (CDSE) + `QuotaBar` (Open-Meteo)

**Data sources:** `GET /status`, `GET /aois`, `GET /waterbodies`

**Refresh:** Auto-refresh every 60 seconds via React Query `refetchInterval`.

**Key requirements:**
- All domain status cards visible without scrolling on 1080p
- Alert count badge on AlertFeedPanel
- Zero additional clicks to see if anything is wrong

---

### Screen 2: WQ Monitoring (`/waterbody/:targetId`)

**Purpose:** Deep-dive water quality monitoring for one water body.

**Primary components:**
- `WQTrendChart` — chl-a observations over 30 days (line chart)
- `AnomalyTimeline` — anomaly predictions with z-score markers
- `BloomRiskForecastBar` — 7-day WQForecast with 90% CI
- `ObservationTable` — last 20 observations (all obs_types)
- `EvidenceClassBadge` — on every value
- `AIReportCard` — situational report from `GET /waterbody/{id}/report`
- `SituationReportLink` → navigate to `/ai/report/:targetId`

**Data sources:**
- `GET /waterbody/{targetId}/observations?obs_type=chlorophyll_a`
- `GET /waterbody/{targetId}/observations` (all types)
- `GET /waterbody/{targetId}/forecasts`
- `GET /waterbody/{targetId}/anomalies`
- `GET /waterbody/{targetId}/report`

**Refresh:** 5-minute interval on forecasts/anomalies; manual refresh on report.

**Key requirements:**
- `evidence_class` badge on every observation row
- 90% CI shown as shaded band in forecast chart (not just a line)
- Anomaly z-scores displayed numerically (not just color)

---

### Screen 3: Anomaly Explanation (`/waterbody/:targetId/anomaly/:predictionId`)

**Purpose:** Explain a specific anomaly with AI hypothesis and advisory.

**Primary components:**
- `ExplanationCard` — hypothesis text, advisory text, confidence badge
- `CitationList` — list of cited record IDs
- `CitationViewer` — slide-in panel with full cited record
- `EvidenceClassBadge` — on hypothesis and cited records
- `BackButton` → returns to WQ Monitoring

**Data source:** `GET /anomaly/{predictionId}/explanation`

**Key requirements:**
- Advisory text always visible above the fold (not inside accordion)
- Confidence badge: low=amber, medium=blue, high=green
- "ADVISORY — not a measurement. Human verification recommended." always shown when
  advisory field is non-empty
- Citations linkable to original Observation/Prediction records

---

### Screen 4: AI Situation Report (`/ai/report/:targetId` or `/waterbody/:targetId/report`)

**Purpose:** Full AI-generated situation report for one water body.

**Primary components:**
- `ReportViewer` — report text with inline citation markers `[1]`, `[2]`
- `CitationPanel` — numbered list matching inline markers
- `CitationViewer` — click citation number to expand record details
- `ModelBadge` — "claude-sonnet-4-6" or "template" (offline)
- `AttributionFooter` — `_attribution` field rendered
- `ExportReportButton` → triggers PDF export of this report

**Data source:** `GET /waterbody/{targetId}/report`

**Key requirements:**
- Inline citation numbers must be hyperlinks that open CitationViewer
- `model: "template"` renders yellow "Offline mode" banner
- `_attribution` rendered in small text at bottom

---

### Screen 5: NL Query (`/ai/query`)

**Purpose:** Natural language question/answer interface over the store.

**Primary components:**
- `NLQueryBox` — textarea + submit button
- `GroundedAnswerPanel` — answer text + citations
- `QueryHistory` — recent queries (session state only)
- `CitationViewer` — same as report viewer
- `ReadOnlyNotice` — "This interface is read-only. Write actions are not supported." (permanent)

**Data source:** `POST /query` with `{question: string}`

**Key requirements:**
- ReadOnlyNotice always visible (OQ-E resolved: read-only)
- Answer empty state: "No answer available." (not spinner indefinitely)
- Query errors show user-friendly message (not raw 422)
- Query history preserved in session; cleared on page refresh

---

### Screen 6: Hazard Panel — Oil (`/hazard/oil`)

**Purpose:** Marine oil slick detection + trajectory simulation.

**Layout:** Map canvas (left/top) + side panel (right/bottom).

**Primary components:**
- `ObservationLayer` (obsLayer) — GeoJSON polygons, confidence-colored
- `TrajectoryPlayer` — slider + play/pause + frame count
- `FrameInfoCard` — valid_at, particle_count, spread_km for current frame
- `ImpactETAList` — ImpactAssessment cards with eta_hours + metric
- `ConfidenceLegend` — red ≥ 80%, orange ≥ 50%, yellow < 50%

**Data sources:**
- `GET /aois/{id}/observations` (all oil_slick obs)
- `GET /aois/{id}/predictions` (OilTrajectory frames)
- `GET /aois/{id}/impact`

**Key requirements:**
- TrajectoryPlayer plays frames at 1 fps by default; speed control (0.5x, 1x, 2x)
- Opacity of trajectory frames increases with time step (fading out past = clearer future)
- Impact ETA shown in hours with 1 decimal place
- `evidence_class: "measured"` badge on observations; `"modeled"` on trajectory frames

---

### Screen 7: Hazard Panel — Flood Risk (`/hazard/flood`)

**Purpose:** Flood risk level + precipitation context.

**Layout:** Map canvas with choke-point layer + right panel.

**Primary components:**
- `FloodRiskBadge` — color-coded: low=green, medium=amber, high=orange, extreme=red
- `RiskScoreGauge` — 0–1 dial (from `uncertainty.risk_score`)
- `ChokePointLayer` (on map) — circles sized by constriction_score
- `FloodContextCard` — peak_precip_mm, peak_discharge_m3s from attrs
- `HonestyLabel` — "Modeled flood risk at choke point — not a measured flood"
- `AttributionFooter` — "Weather data by Open-Meteo.com (CC BY 4.0)"

**Data sources:**
- `GET /aois/{id}/flood-risk` (RiskPredictionListResponse)
- `GET /aois/{id}/choke-points` (ChokePointListResponse)

**Key requirements:**
- Honesty label always visible (not in tooltip)
- CC BY 4.0 attribution always visible in panel
- risk_level enum maps to: low=green, medium=amber, high=orange, extreme=red

---

### Screen 8: Hazard Panel — Acid Risk (`/hazard/acid`)

**Purpose:** Acid deposition risk index.

**Primary components:**
- `AcidRiskGauge` — 0–10 scale, color coded (< 4 green, 4–7 amber, ≥ 7 red)
- `AcidRiskBadge` — index value + "NOT a pH measurement" label always visible
- `AcidContextCard` — peak_so2_ug_m3, methodology from attrs/uncertainty
- `UncertaintyRange` — `uncertainty.index_range` shown as [min, max]
- `HonestyLabel` — "Modeled acid-deposition risk index (0–10 scale) — NOT a pH measurement"
- `AttributionFooter` — "Weather data by Open-Meteo.com (CC BY 4.0)"

**Data source:** `GET /aois/{id}/acid-risk` (RiskPredictionListResponse)

**Key requirements:**
- "NOT a pH measurement" label always rendered (never behind tooltip)
- Gauge shows uncertainty range as shaded arc
- CC BY 4.0 attribution visible

---

### Screen 9: Choke Points (`/choke-points`)

**Purpose:** D4 hydro choke point visualization and table.

**Layout:** Map (top/left) + table (bottom/right).

**Primary components:**
- `ChokePointLayer` on map — circles, radius = 4 + round(score × 8), blue
- `ChokePointTable` — sortable by constriction_score desc
- `ChokePointDetailCard` — upstream_area_km2, score, dem_source
- `EvidenceClassBadge` — always "inferred" for all choke points

**Data source:** `GET /aois/{id}/choke-points`

**Key requirements:**
- Sort by constriction_score descending (matches API guarantee)
- Evidence class "inferred" badge on every row and map popup
- DEM source shown: "Copernicus GLO-30 DEM"

---

### Screen 10: AI Assistant Hub (`/ai`)

**Purpose:** Entry point for AI features — links to query and reports.

**Primary components:**
- `AICapabilityCard` for each AI function (report, query, anomaly explanation)
- Quick access to `NLQueryBox`
- `RecentReportsList` — last 5 reports by target_id
- `OfflineBanner` — if `ARGUS_AI_OFFLINE=true` reflected in response model field

---

### Screen 11: Admin — AOI Manager (`/admin/aois`)

**Purpose:** View and manage configured AOIs.

**Primary components:**
- `AOITable` — id, name, domains, active status
- `AOIDetailPanel` — geometry preview, full fields
- `DomainTagList` — shows enabled domains as colored tags
- `ActiveToggle` — enable/disable AOI (if backend supports PATCH)

**Data source:** `GET /aois`, `GET /aois/{id}`

**Note:** Phase 10 scope is read UI. Write operations (POST/PATCH AOI) are Phase 11+
unless backend supports them. The form components should be built but may be disabled.

---

### Screen 12: Admin — Alert Rules (`/admin/alerts`)

**Purpose:** View configured alert channels and thresholds.

**Primary components:**
- `AlertThresholdCard` — one per alert type (HAB, flood, acid)
  - HAB: z_score_threshold (2.5), bloom_threshold (25 µg/L)
  - Flood: risk_level trigger values
  - Acid: acid_risk_index_threshold (7.0)
- `AlertChannelList` — webhook URL (masked), email (masked)

**Note:** Alert thresholds are backend-configured. This screen is read-only display.
Alert channel secrets must never be shown in full (mask after first 8 chars).

---

### Screen 13: Admin — Domain Toggle (`/admin/domains`)

**Purpose:** View domain enabled/disabled state per AOI.

**Primary components:**
- `DomainToggleMatrix` — AOIs × domains grid with on/off toggles
- Tooltips showing domain_id, last run status, observations_created

**Data source:** `GET /aois` (domains field), `GET /status` (domain_runs)

---

### Screen 14: Export — GeoJSON (`/export/geojson`)

**Purpose:** Download observations or predictions as GeoJSON.

**Primary components:**
- `ExportForm` — domain selector, obs_type selector, date range picker
- `FieldSelector` — choose which fields to include
- `DownloadButton` — triggers browser download
- `PreviewPanel` — shows first 5 records before download

**Data source:** `GET /aois/{id}/observations?obs_type=X` (with date filter client-side)

**Key requirements:**
- GeoJSON output must include `evidence_class` in every feature's properties
- Preview shows record count before download

---

### Screen 15: Export — CSV (`/export/csv`)

**Purpose:** Download WQ time series as CSV.

**Primary components:**
- Same form structure as GeoJSON export
- CSV columns: id, obs_type, evidence_class, value, unit, area_km2, confidence, created_at

---

### Screen 16: Export — PDF Report (`/export/pdf`)

**Purpose:** Generate a one-page PDF situation report.

**Primary components:**
- `PDFPreview` — iframe or HTML preview of report layout
- `DateRangePicker`
- `AOISelector`
- `SectionToggle` — include/exclude: map thumbnail, WQ trends, AI text, alert list
- `DownloadPDFButton`

**Note:** Phase 10 scope is HTML print preview + browser print-to-PDF.
Server-side PDF generation (reportlab/weasyprint) is Phase 11 (F-051 backend work).

**Key requirements:**
- CC BY 4.0 attribution in PDF footer
- evidence_class badges visible in print CSS

---

### Screen 17: 404 Not Found (`/*`)

**Primary components:**
- `NotFoundCard` — "Page not found" with link back to /overview

---

### Screen 18: Error Boundary

**Purpose:** Catch unhandled React errors.

**Primary components:**
- `ErrorBoundaryCard` — error message, stack (dev mode only), "Reload" button

---

## 7. Component Library

All components are TypeScript. Props interfaces are canonical — implement exactly.

### 7.1 Layout Components

```typescript
// AppShell.tsx
interface AppShellProps {
  children: React.ReactNode;
}

// Header.tsx
interface HeaderProps {
  aoiOptions: { id: string; name: string; active: boolean }[];
  selectedAoiId: string | null;
  onAoiChange: (aoiId: string) => void;
  systemStatus: "healthy" | "degraded" | "unavailable";
  alertCount: number;
}

// Sidebar.tsx
interface SidebarProps {
  waterbodyIds: string[];
  collapsed: boolean;
  onToggle: () => void;
}

// Breadcrumb.tsx
interface BreadcrumbProps {
  items: { label: string; href?: string }[];
}
```

### 7.2 Domain Status Components

```typescript
// DomainStatusCard.tsx
interface DomainStatusCardProps {
  domainId: string;          // "marine_oil" | "inland_wq" | "weather_hydro" | "hydro_chokepoints"
  lastRunAt: string | null;  // ISO8601
  lastRunStatus: "complete" | "failed" | "partial" | "skipped" | null;
  scenesLastRun: number;
  observationsLastRun: number;
  bytesUsed: number;
}

// DomainStatusGrid.tsx
interface DomainStatusGridProps {
  domains: DomainStatusCardProps[];
}

// SystemStatusPanel.tsx
interface SystemStatusPanelProps {
  version: string;
  storeAccessible: boolean;
  lastAnalysisRunAt: string | null;
  cdseQuota: { bytesToday: number; dailyLimitGb: number; remainingBytes: number };
  openMeteoCallsToday: number;
  openMeteoLimit: number; // 10000
}

// QuotaBar.tsx
interface QuotaBarProps {
  label: string;
  used: number;
  limit: number;
  unit: "bytes" | "calls";
  warnAt: number; // fraction 0–1, e.g. 0.8
}
```

### 7.3 Water Quality Components

```typescript
// WQTrendChart.tsx
interface WQTrendChartProps {
  observations: {
    created_at: string;
    value: number | null;
    unit: string;
    evidence_class: "measured" | "modeled" | "inferred";
  }[];
  obsType: string;           // "chlorophyll_a" | "turbidity" | "cdom" | "surface_temp"
  days?: number;             // default 30
}

// BloomRiskForecastBar.tsx
// 7-day forecast from WaterQualityForecast predictor.
// Renders bar chart where each bar represents one forecast day.
// CI band rendered as error bars or shaded area.
interface BloomRiskForecastBarProps {
  prediction: {
    id: string;
    predictor_id: string;
    kind: "forecast";
    evidence_class: string;
    uncertainty: Record<string, unknown>;  // contains ci_lower, ci_upper, daily_values
    created_at: string;
    frames: unknown[];  // WQForecast uses attrs not frames for daily data
    attrs?: Record<string, unknown>;
  };
}

// AnomalyTimeline.tsx
interface AnomalyTimelineProps {
  anomalies: {
    id: string;
    predictor_id: "AnomalyDetector";
    kind: "anomaly";
    uncertainty: {
      sigma?: number;       // z-score magnitude
      direction?: "positive" | "negative";
    };
    created_at: string;
    attrs?: Record<string, unknown>;
  }[];
  onExplainClick: (predictionId: string) => void;
}

// WaterBodySummaryTable.tsx
interface WaterBodySummaryTableProps {
  targets: {
    targetId: string;
    latestAnomalySigma: number | null;
    latestBloomRisk: "low" | "medium" | "high" | null;
    observationCount: number;
    lastObservationAt: string | null;
  }[];
  onRowClick: (targetId: string) => void;
}

// ObservationTable.tsx
interface ObservationTableProps {
  observations: {
    id: string;
    obs_type: string;
    evidence_class: "measured" | "modeled" | "inferred";
    value: number | null;
    unit: string | null;
    area_km2: number;
    confidence: number;
    status: "candidate" | "confirmed" | "dismissed";
    created_at: string;
  }[];
  onRowClick?: (id: string) => void;
}
```

### 7.4 Hazard Components

```typescript
// TrajectoryPlayer.tsx
// Animates OilTrajectory ForecastFrames on the Leaflet map.
interface TrajectoryPlayerProps {
  frames: {
    id: string;
    valid_at: string;
    footprint: GeoJSONGeometry;
    particle_count: number;
    stats: Record<string, number>;
  }[];
  mapRef: React.RefObject<L.Map>;
  onFrameChange?: (frameIndex: number) => void;
}

// FrameInfoCard.tsx
interface FrameInfoCardProps {
  validAt: string;
  particleCount: number;
  spreadKm: number | null;
  driftKm: number | null;
  frameIndex: number;
  totalFrames: number;
}

// ImpactETAList.tsx
interface ImpactETAListProps {
  impacts: {
    id: string;
    exposure_layer_id: string;
    eta_hours: number;
    valid_at: string;
    metrics: Record<string, number>;
  }[];
}

// FloodRiskBadge.tsx
interface FloodRiskBadgeProps {
  riskLevel: "low" | "medium" | "high" | "extreme" | null;
  showLabel?: boolean;
}

// RiskScoreGauge.tsx
interface RiskScoreGaugeProps {
  score: number;       // 0–1
  label?: string;
}

// AcidRiskGauge.tsx
interface AcidRiskGaugeProps {
  index: number;       // 0–10
  uncertaintyRange?: [number, number];
  label?: string;
}

// ChokePointTable.tsx
interface ChokePointTableProps {
  chokePoints: {
    id: string;
    upstream_area_km2: number;
    constriction_score: number;
    dem_source: string;
    evidence_class: "inferred";
  }[];
}

// HonestyLabel.tsx
// Renders honesty disclaimer for modeled/inferred values. Never hidden.
interface HonestyLabelProps {
  text: string;       // from prediction.label or prediction.attrs.label
  evidenceClass: "measured" | "modeled" | "inferred";
}
```

### 7.5 AI Components

```typescript
// NLQueryBox.tsx
interface NLQueryBoxProps {
  onSubmit: (question: string) => void;
  isLoading: boolean;
  placeholder?: string;
}

// GroundedAnswerPanel.tsx
interface GroundedAnswerPanelProps {
  answer: string;
  citations: string[];   // record IDs referenced in text
  model: string;
  attribution: string;
  onCitationClick: (recordId: string) => void;
}

// ReportViewer.tsx
interface ReportViewerProps {
  text: string;
  citations: string[];
  model: string;
  attribution: string;
  onCitationClick: (recordId: string) => void;
}

// CitationViewer.tsx
// Slide-in panel. Fetches record by ID; handles obs/prediction disambiguation.
interface CitationViewerProps {
  recordId: string | null;  // null = closed
  onClose: () => void;
}

// ExplanationCard.tsx
interface ExplanationCardProps {
  hypothesis: string;
  advisory: string;
  confidence: "low" | "medium" | "high";
  citations: string[];
  model: string;
  attribution: string;
  onCitationClick: (recordId: string) => void;
}

// ModelBadge.tsx
interface ModelBadgeProps {
  model: string;   // "claude-sonnet-4-6" | "template" | etc.
}

// OfflineBanner.tsx
// Shown when model === "template".
interface OfflineBannerProps {
  message?: string;
}

// ReadOnlyNotice.tsx
// Permanent notice on NL Query screen per OQ-E.
// No props — renders "This interface is read-only. Write actions are not supported."
```

### 7.6 Shared / Primitive Components

```typescript
// EvidenceClassBadge.tsx
interface EvidenceClassBadgeProps {
  evidenceClass: "measured" | "modeled" | "inferred";
  size?: "sm" | "md";
}
// Renders: measured=no badge, modeled=amber "Modeled", inferred=blue "Inferred"

// AlertBadge.tsx
interface AlertBadgeProps {
  domain: "marine_oil" | "inland_wq" | "weather_hydro" | string;
  message: string;
  confidence: number;
  status: "pending" | "sent" | "failed";
  createdAt: string;
}

// AlertFeedPanel.tsx
interface AlertFeedPanelProps {
  alerts: AlertBadgeProps[];
  maxVisible?: number;  // default 5
}

// AttributionFooter.tsx
interface AttributionFooterProps {
  text: string;    // from API _attribution field; always rendered visibly
}

// ConfidenceColorDot.tsx
interface ConfidenceColorDotProps {
  confidence: number;  // 0–1; ≥0.8=red, ≥0.5=orange, <0.5=yellow
}

// ErrorMessage.tsx
interface ErrorMessageProps {
  message: string;
  retry?: () => void;
}

// LoadingSpinner.tsx
interface LoadingSpinnerProps {
  size?: "sm" | "md" | "lg";
  label?: string;
}

// EmptyState.tsx
interface EmptyStateProps {
  message: string;
  icon?: React.ReactNode;
}

// NotFoundCard.tsx
// No required props. Renders 404 message + link to /overview.

// BackButton.tsx
interface BackButtonProps {
  to: string;
  label?: string;
}
```

### 7.7 Map Components (Leaflet wrappers)

```typescript
// ArgusMap.tsx
// Wraps Leaflet map with React-Leaflet. Exposes ref for imperative layer control.
interface ArgusMapProps {
  center?: [number, number];
  zoom?: number;
  children?: React.ReactNode;
  className?: string;
}

// ObservationLayer.tsx
interface ObservationLayerProps {
  observations: ObservationSchema[];
  visible: boolean;
}

// ChokePointMapLayer.tsx
interface ChokePointMapLayerProps {
  chokePoints: ChokePointSchema[];
  visible: boolean;
  onPointClick?: (id: string) => void;
}

// LayerToggleControl.tsx
interface LayerToggleControlProps {
  layers: {
    id: string;
    label: string;
    visible: boolean;
    onToggle: () => void;
  }[];
}
```

### 7.8 Admin Components

```typescript
// AOITable.tsx
interface AOITableProps {
  aois: { id: string; name: string; domains: string[]; active: boolean }[];
  onSelect: (id: string) => void;
}

// DomainToggleMatrix.tsx
interface DomainToggleMatrixProps {
  aois: { id: string; name: string; domains: string[] }[];
  allDomains: string[];
  // read-only for Phase 10; onToggle wired in Phase 11+
  onToggle?: (aoiId: string, domain: string, enabled: boolean) => void;
}

// AlertThresholdCard.tsx
interface AlertThresholdCardProps {
  alertType: "hab" | "flood_risk" | "acid_risk";
  thresholds: Record<string, number | string>;
  // read-only; no edit in Phase 10
}

// DomainTagList.tsx
interface DomainTagListProps {
  domains: string[];   // ["marine_oil", "inland_wq", ...]
}
```

### 7.9 Export Components

```typescript
// ExportForm.tsx
interface ExportFormProps {
  availableDomains: string[];
  availableObsTypes: string[];
  onSubmit: (params: ExportParams) => void;
  isLoading: boolean;
}

interface ExportParams {
  aoiId: string;
  domain: string;
  obsType: string | null;
  dateFrom: string;
  dateTo: string;
  format: "geojson" | "csv" | "pdf";
}

// PDFPreview.tsx
interface PDFPreviewProps {
  aoiName: string;
  dateRange: { from: string; to: string };
  sections: {
    includeMap: boolean;
    includeWQ: boolean;
    includeAI: boolean;
    includeAlerts: boolean;
  };
}
```

---

## 8. API Integration Guide

Base URL:
- Development: `http://localhost:8000`
- Production: Cloud Run custom domain (from environment variable `VITE_API_BASE_URL`)

All responses include `Content-Type: application/json`. No authentication required for MVP.

### 8.1 Complete Endpoint Table

| # | Method | Path | React Query key | Response type | Notes |
|---|---|---|---|---|---|
| 1 | GET | `/health` | `["health"]` | `HealthResponse` | Poll every 30s |
| 2 | GET | `/ready` | `["ready"]` | `ReadyResponse` | Startup check |
| 3 | GET | `/status` | `["status"]` | `StatusResponse` | Poll every 60s |
| 4 | GET | `/aois` | `["aois"]` | `AOIListResponse` | Populated at startup |
| 5 | GET | `/aois/{id}` | `["aoi", id]` | `AOISchema` | On AOI select |
| 6 | GET | `/aois/{id}/observations` | `["obs", id, status, obsType]` | `ObservationListResponse` | status, obs_type query params |
| 7 | GET | `/aois/{id}/predictions` | `["preds", id]` | `PredictionListResponse` | OilTrajectory frames |
| 8 | GET | `/aois/{id}/impact` | `["impact", id]` | `ImpactListResponse` | ETA assessments |
| 9 | GET | `/aois/{id}/choke-points` | `["choke", id]` | `ChokePointListResponse` | Sorted by score desc |
| 10 | GET | `/aois/{id}/flood-risk` | `["flood", id]` | `RiskPredictionListResponse` | attrs.risk_level |
| 11 | GET | `/aois/{id}/acid-risk` | `["acid", id]` | `RiskPredictionListResponse` | attrs.acid_risk_index |
| 12 | GET | `/waterbodies` | `["waterbodies"]` | `WaterbodyListResponse` | All target_ids with WQ obs |
| 13 | GET | `/waterbody/{id}/observations` | `["wq-obs", id, obsType]` | `ObservationListResponse` | obs_type filter supported |
| 14 | GET | `/waterbody/{id}/forecasts` | `["wq-fore", id]` | `PredictionListResponse` | Skill-gated only |
| 15 | GET | `/waterbody/{id}/raw_predictions` | `["wq-raw", id]` | `PredictionListResponse` | All preds (internal review) |
| 16 | GET | `/waterbody/{id}/anomalies` | `["wq-anom", id]` | `PredictionListResponse` | AnomalyDetector preds |
| 17 | GET | `/waterbody/{id}/report` | `["wq-report", id]` | `AIReportResponse` | May be offline/templated |
| 18 | GET | `/anomaly/{predId}/explanation` | `["explain", predId]` | `ExplanationResponse` | AI advisory |
| 19 | POST | `/query` | (mutation) | `QueryResponse` | Read-only NL query |

### 8.2 Response Type Definitions

```typescript
// From argus/api/schemas.py — canonical; do not invent fields

interface HealthResponse {
  status: string;
  version: string;
}

interface ReadyResponse {
  status: "ready" | "not_ready";
  reason: string | null;
}

interface StatusResponse {
  version: string;
  store_accessible: boolean;
  last_analysis_run_at: string | null;  // ISO8601
  quota: {
    cdse_bytes_today: number;
    cdse_daily_limit_gb: number;
    cdse_remaining_bytes: number;
  };
  domain_runs: {
    domain_id: string;
    aoi_id: string;
    last_run_at: string | null;
    last_run_status: string | null;
    scenes_fetched: number;
    observations_created: number;
    bytes_used: number;
  }[];
  open_meteo_calls_today: number;
}

interface AOISchema {
  id: string;
  name: string;
  geometry: GeoJSONGeometry;
  domains: string[];
  active: boolean;
}

interface AOIListResponse {
  items: AOISchema[];
  count: number;
}

interface ObservationSchema {
  id: string;
  analysis_run_id: string;
  scene_id: string;
  obs_type: string;  // from VALID_OBS_TYPES
  evidence_class: "measured" | "modeled" | "inferred";
  geometry: GeoJSONGeometry;
  area_km2: number;
  confidence: number;  // 0–1
  status: "candidate" | "confirmed" | "dismissed";
  created_at: string;  // ISO8601
}

interface ObservationListResponse {
  items: ObservationSchema[];
  count: number;
}

interface ForecastFrameSchema {
  id: string;
  prediction_id: string;
  valid_at: string;   // ISO8601
  footprint: GeoJSONGeometry;
  particle_count: number;
  stats: Record<string, number>;  // mean_lon, mean_lat, spread_km, drift_km, ...
}

interface PredictionSchema {
  id: string;
  predictor_id: string;  // "OilTrajectory" | "WaterQualityForecast" | "AnomalyDetector" | "FloodRisk" | "AcidDepositionRisk"
  kind: "forecast" | "risk" | "anomaly" | "trajectory";
  evidence_class: "measured" | "modeled" | "inferred";
  uncertainty: Record<string, unknown>;  // INV-9: always non-empty
  created_at: string;
  frames: ForecastFrameSchema[];
  attrs?: Record<string, unknown>;  // domain-specific extras
}

interface PredictionListResponse {
  items: PredictionSchema[];
  count: number;
  _attribution: string;  // "Weather data by Open-Meteo.com (CC BY 4.0)"
}

interface AIReportResponse {
  text: string;
  citations: string[];   // record IDs referenced in text
  model: string;         // "claude-sonnet-4-6" | "template"
  _attribution: string;
}

interface ExplanationResponse {
  hypothesis: string;
  advisory: string;
  confidence: "low" | "medium" | "high";
  citations: string[];
  model: string;
  _attribution: string;
}

interface QueryRequest {
  question: string;
}

interface QueryResponse {
  answer: string;
  citations: string[];
  model: string;
  _attribution: string;
}

interface ChokePointSchema {
  id: string;
  aoi_id: string;
  location: GeoJSONGeometry;   // always Point
  upstream_area_km2: number;
  constriction_score: number;  // 0–1
  dem_source: string;          // "cop_glo30"
  evidence_class: "inferred";  // always inferred (INV-3)
}

interface ChokePointListResponse {
  items: ChokePointSchema[];
  count: number;
}

interface RiskPredictionSchema {
  id: string;
  predictor_id: string;
  kind: "risk";
  evidence_class: "modeled";   // always modeled (INV-3)
  label: string;               // honesty label
  risk_score: number | null;   // 0–1; FloodRisk only
  risk_level: "low" | "medium" | "high" | "extreme" | null;  // FloodRisk only
  acid_risk_index: number | null;  // 0–10; AcidDepositionRisk only
  uncertainty: Record<string, unknown>;
  created_at: string;
}

interface RiskPredictionListResponse {
  items: RiskPredictionSchema[];
  count: number;
}

interface ImpactAssessmentSchema {
  id: string;
  prediction_id: string;
  exposure_layer_id: string;
  valid_at: string;
  eta_hours: number;
  metrics: Record<string, number>;  // coast_length_km | mpa_area_km2
}

interface ImpactListResponse {
  items: ImpactAssessmentSchema[];
  count: number;
}

interface WaterbodyListResponse {
  target_ids: string[];
  count: number;
}

type GeoJSONGeometry = GeoJSONPoint | GeoJSONPolygon | GeoJSONLineString | GeoJSONMultiPolygon;
```

### 8.3 Observation Filter Parameters

`GET /aois/{id}/observations` and `GET /waterbody/{id}/observations` accept:

| Param | Type | Description |
|---|---|---|
| `obs_type` | string | Filter by obs_type (e.g. `chlorophyll_a`) |
| `status` | string | Filter by status (`candidate`, `confirmed`, `dismissed`) |

### 8.4 Error Handling

All backend errors return standard FastAPI JSON error responses:

```typescript
interface HTTPError {
  detail: string;  // or { msg, type } for 422 validation errors
}
```

- 404: resource not found — show `EmptyState` (not an error for lists)
- 422: validation error — show `ErrorMessage` with hint
- 500: internal error — show `ErrorMessage` with retry
- Network error — show `ErrorMessage` "API unavailable"; retry button

### 8.5 _attribution Field Rendering Rule

`_attribution` is present on all prediction and AI response endpoints. It MUST be rendered
as visible text in the corresponding panel — not just stored. Canonical placement: small text
in `AttributionFooter` component at the bottom of the panel. Never omit it.

---

## 9. State Management

### 9.1 Server State — TanStack Query v5

All server-fetched data is managed by TanStack Query. No manual fetch/useEffect for data
that has a React Query hook.

**Query client configuration:**

```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,          // 30 seconds
      gcTime: 5 * 60_000,         // 5 minutes
      retry: 2,
      refetchOnWindowFocus: true,
    },
  },
});
```

**Polling intervals by data type:**

| Data | Hook | refetchInterval |
|---|---|---|
| System health | `useHealth` | 30_000 (30s) |
| System status | `useStatus` | 60_000 (60s) |
| AOI list | `useAOIs` | false (stable) |
| Observations | `useObservations` | 300_000 (5m) |
| Predictions/frames | `usePredictions` | 300_000 (5m) |
| WQ forecasts | `useWQForecasts` | 300_000 (5m) |
| Anomalies | `useAnomalies` | 300_000 (5m) |
| Choke points | `useChokePoints` | false (stable) |
| Flood/acid risk | `useFloodRisk`, `useAcidRisk` | 300_000 (5m) |
| AI report | `useWQReport` | false (manual refresh) |
| AI explanation | `useExplanation` | false (stable) |

**Query key factory:**

```typescript
export const queryKeys = {
  health: () => ["health"] as const,
  status: () => ["status"] as const,
  aois: () => ["aois"] as const,
  aoi: (id: string) => ["aoi", id] as const,
  observations: (aoiId: string, obsType?: string, status?: string) =>
    ["obs", aoiId, obsType, status] as const,
  predictions: (aoiId: string) => ["preds", aoiId] as const,
  impact: (aoiId: string) => ["impact", aoiId] as const,
  chokePoints: (aoiId: string) => ["choke", aoiId] as const,
  floodRisk: (aoiId: string) => ["flood", aoiId] as const,
  acidRisk: (aoiId: string) => ["acid", aoiId] as const,
  waterbodies: () => ["waterbodies"] as const,
  wqObservations: (targetId: string, obsType?: string) =>
    ["wq-obs", targetId, obsType] as const,
  wqForecasts: (targetId: string) => ["wq-fore", targetId] as const,
  wqAnomalies: (targetId: string) => ["wq-anom", targetId] as const,
  wqReport: (targetId: string) => ["wq-report", targetId] as const,
  explanation: (predId: string) => ["explain", predId] as const,
};
```

### 9.2 Client State — Zustand

Three stores:

```typescript
// stores/aoiStore.ts
interface AOIStore {
  selectedAoiId: string | null;
  setSelectedAoiId: (id: string) => void;
}
// Persisted to localStorage key "argus:selectedAoiId"

// stores/mapStore.ts
interface MapStore {
  center: [number, number];
  zoom: number;
  layerVisibility: {
    observations: boolean;
    trajectory: boolean;
    impact: boolean;
    waterQuality: boolean;
    chokePoints: boolean;
    floodRisk: boolean;
    acidRisk: boolean;
  };
  setCenter: (center: [number, number]) => void;
  setZoom: (zoom: number) => void;
  toggleLayer: (layer: keyof MapStore["layerVisibility"]) => void;
}
// NOT persisted (map state resets on reload)

// stores/uiStore.ts
interface UIStore {
  sidebarCollapsed: boolean;
  alertDrawerOpen: boolean;
  citationViewerRecordId: string | null;
  setSidebarCollapsed: (v: boolean) => void;
  setAlertDrawerOpen: (v: boolean) => void;
  setCitationViewerRecordId: (id: string | null) => void;
}
```

### 9.3 AOI Context Invalidation

When `selectedAoiId` changes, invalidate all AOI-scoped queries:

```typescript
// In AOI selector onChange handler:
queryClient.invalidateQueries({ queryKey: ["obs", prevAoiId] });
queryClient.invalidateQueries({ queryKey: ["preds", prevAoiId] });
queryClient.invalidateQueries({ queryKey: ["impact", prevAoiId] });
queryClient.invalidateQueries({ queryKey: ["choke", prevAoiId] });
queryClient.invalidateQueries({ queryKey: ["flood", prevAoiId] });
queryClient.invalidateQueries({ queryKey: ["acid", prevAoiId] });
```

---

## 10. Frontend Architecture

### 10.1 Folder Structure

```
frontend/
├── index.html
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.ts
├── src/
│   ├── main.tsx                  App entry point
│   ├── App.tsx                   Router setup
│   ├── api/
│   │   ├── client.ts             Axios/fetch client with base URL
│   │   ├── endpoints.ts          Typed fetch functions (one per endpoint)
│   │   └── types.ts              All TypeScript response types (from §8.2)
│   ├── hooks/
│   │   ├── useHealth.ts
│   │   ├── useStatus.ts
│   │   ├── useAOIs.ts
│   │   ├── useObservations.ts
│   │   ├── usePredictions.ts
│   │   ├── useImpact.ts
│   │   ├── useChokePoints.ts
│   │   ├── useFloodRisk.ts
│   │   ├── useAcidRisk.ts
│   │   ├── useWaterbodies.ts
│   │   ├── useWQObservations.ts
│   │   ├── useWQForecasts.ts
│   │   ├── useWQAnomalies.ts
│   │   ├── useWQReport.ts
│   │   ├── useExplanation.ts
│   │   └── useNLQuery.ts         (mutation hook)
│   ├── stores/
│   │   ├── aoiStore.ts
│   │   ├── mapStore.ts
│   │   └── uiStore.ts
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppShell.tsx
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── Breadcrumb.tsx
│   │   ├── domain/
│   │   │   ├── DomainStatusCard.tsx
│   │   │   ├── DomainStatusGrid.tsx
│   │   │   └── DomainTagList.tsx
│   │   ├── wq/
│   │   │   ├── WQTrendChart.tsx
│   │   │   ├── BloomRiskForecastBar.tsx
│   │   │   ├── AnomalyTimeline.tsx
│   │   │   ├── WaterBodySummaryTable.tsx
│   │   │   └── ObservationTable.tsx
│   │   ├── hazard/
│   │   │   ├── TrajectoryPlayer.tsx
│   │   │   ├── FrameInfoCard.tsx
│   │   │   ├── ImpactETAList.tsx
│   │   │   ├── FloodRiskBadge.tsx
│   │   │   ├── RiskScoreGauge.tsx
│   │   │   ├── AcidRiskGauge.tsx
│   │   │   ├── ChokePointTable.tsx
│   │   │   └── HonestyLabel.tsx
│   │   ├── ai/
│   │   │   ├── NLQueryBox.tsx
│   │   │   ├── GroundedAnswerPanel.tsx
│   │   │   ├── ReportViewer.tsx
│   │   │   ├── CitationViewer.tsx
│   │   │   ├── ExplanationCard.tsx
│   │   │   ├── ModelBadge.tsx
│   │   │   ├── OfflineBanner.tsx
│   │   │   └── ReadOnlyNotice.tsx
│   │   ├── map/
│   │   │   ├── ArgusMap.tsx
│   │   │   ├── ObservationLayer.tsx
│   │   │   ├── ChokePointMapLayer.tsx
│   │   │   └── LayerToggleControl.tsx
│   │   ├── admin/
│   │   │   ├── AOITable.tsx
│   │   │   ├── DomainToggleMatrix.tsx
│   │   │   └── AlertThresholdCard.tsx
│   │   ├── export/
│   │   │   ├── ExportForm.tsx
│   │   │   └── PDFPreview.tsx
│   │   └── shared/
│   │       ├── EvidenceClassBadge.tsx
│   │       ├── AlertBadge.tsx
│   │       ├── AlertFeedPanel.tsx
│   │       ├── AttributionFooter.tsx
│   │       ├── ConfidenceColorDot.tsx
│   │       ├── QuotaBar.tsx
│   │       ├── SystemStatusPanel.tsx
│   │       ├── ErrorMessage.tsx
│   │       ├── LoadingSpinner.tsx
│   │       ├── EmptyState.tsx
│   │       ├── NotFoundCard.tsx
│   │       └── BackButton.tsx
│   ├── screens/
│   │   ├── OverviewScreen.tsx
│   │   ├── WQMonitoringScreen.tsx
│   │   ├── AnomalyExplanationScreen.tsx
│   │   ├── SituationReportScreen.tsx
│   │   ├── NLQueryScreen.tsx
│   │   ├── HazardOilScreen.tsx
│   │   ├── HazardFloodScreen.tsx
│   │   ├── HazardAcidScreen.tsx
│   │   ├── ChokePointsScreen.tsx
│   │   ├── AIHubScreen.tsx
│   │   ├── AdminAOIsScreen.tsx
│   │   ├── AdminAlertsScreen.tsx
│   │   ├── AdminDomainsScreen.tsx
│   │   ├── ExportGeoJSONScreen.tsx
│   │   ├── ExportCSVScreen.tsx
│   │   ├── ExportPDFScreen.tsx
│   │   ├── NotFoundScreen.tsx
│   │   └── ErrorBoundaryScreen.tsx
│   └── utils/
│       ├── confidenceColor.ts     // ≥0.8=red, ≥0.5=orange, <0.5=yellow
│       ├── riskLevelColor.ts      // extreme=red, high=orange, medium=amber, low=green
│       ├── evidenceLabel.ts       // measured/modeled/inferred → display label
│       ├── formatISODate.ts
│       └── downloadFile.ts        // trigger browser download
└── public/
    └── favicon.ico
```

### 10.2 Vite Configuration

```typescript
// vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
  build: {
    outDir: "../argus/api/static/dist",   // served by FastAPI
    emptyOutDir: true,
  },
});
```

**Note:** FastAPI serves `frontend/dist/` at `/app` (or `/`) via `StaticFiles`. The existing
`index.html` + `app.js` at `argus/api/static/` is replaced by the Vite build output.

### 10.3 Environment Variables

```
VITE_API_BASE_URL=http://localhost:8000   # dev
VITE_API_BASE_URL=https://api.argus.run   # prod (Cloud Run)
```

---

## 11. Design System

### 11.1 Color Palette

```
Background (dark map theme):
  bg-base:     #0f172a   (slate-900)  — main background
  bg-surface:  #1e293b   (slate-800)  — cards, panels
  bg-elevated: #334155   (slate-700)  — hover states, modals

Text:
  text-primary:   #f1f5f9  (slate-100)
  text-secondary: #94a3b8  (slate-400)
  text-muted:     #475569  (slate-600)

Accent (brand):
  accent:      #38bdf8  (sky-400)     — links, active state, trajectory layer
  accent-dark: #0ea5e9  (sky-500)

Status / Risk:
  risk-extreme: #ef4444  (red-500)    — also confidence ≥ 80%
  risk-high:    #f97316  (orange-500) — also confidence ≥ 50%
  risk-medium:  #facc15  (yellow-400) — also confidence < 50%
  risk-low:     #22c55e  (green-500)
  risk-normal:  #22c55e  (green-500)

Evidence class badges:
  measured:  no badge
  modeled:   #f59e0b  (amber-500) background, text white
  inferred:  #60a5fa  (blue-400)  background, text slate-900

AI model badge:
  live:     #818cf8  (indigo-400) — "claude-sonnet-4-6"
  template: #facc15  (yellow-400) — "template" (offline mode)

Attribution text:  #64748b  (slate-500) — small, always visible

Open-Meteo CC:    #64748b italic (rendered in AttributionFooter)
```

### 11.2 Typography

```
Font family:
  Display:  Inter Variable (from Bunny Fonts — zero cost, GDPR-safe)
  Mono:     JetBrains Mono (for IDs, JSON, citation keys)

Scale:
  xs:    0.65rem / 1rem    — quota labels, map attribution
  sm:    0.75rem / 1.1rem  — table cells, observation details
  base:  0.875rem / 1.4rem — body text, panel content
  lg:    1rem / 1.5rem     — section headers, card titles
  xl:    1.125rem / 1.5rem — screen titles
  2xl:   1.5rem / 2rem     — metric values (risk scores, quota numbers)

Weight:
  normal: 400 — body
  medium: 500 — labels
  semibold: 600 — card headers, table headers
  bold: 700 — metric values, risk badges
```

### 11.3 Spacing

Tailwind 4-pixel base. Key layout constants:
- Header height: `h-14` (56px)
- Sidebar width: `w-56` (224px) expanded; `w-14` (56px) collapsed
- Card padding: `p-4` (16px)
- Panel gap: `gap-4` (16px)
- Map canvas: `calc(100vh - 56px)` height when full-screen

### 11.4 Component Styling Conventions

- All cards: `rounded-lg bg-surface border border-slate-700 p-4`
- Tables: `divide-y divide-slate-700`, `hover:bg-slate-700/50`
- Badges: `inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium`
- Buttons: `rounded-md px-3 py-2 text-sm font-medium transition-colors`
  - Primary: `bg-sky-500 hover:bg-sky-400 text-white`
  - Secondary: `bg-slate-700 hover:bg-slate-600 text-slate-100`
  - Danger: `bg-red-600 hover:bg-red-500 text-white`

### 11.5 Motion / Animation

Framer Motion used only for:
- Sidebar collapse/expand: `width` animation, 200ms ease-out
- CitationViewer slide-in: `x` transform, 250ms ease-out
- Alert drawer: `y` transform, 200ms ease-out
- TrajectoryPlayer frame transitions: opacity, 100ms per frame

Do not animate data updates — charts update without animation to avoid confusion with
real-time data changes.

### 11.6 Dark Mode

Argus uses dark mode only (not togglable). The dark basemap and dark UI are a unified
visual system. There is no light mode for Phase 10.

---

## 12. Technology Stack

| Technology | Version | Role | Justification |
|---|---|---|---|
| React | 18 | UI framework | Hooks, concurrent rendering, large ecosystem |
| Vite | 5 | Build tool | Fast HMR, ESBuild, tree-shaking |
| TypeScript | 5 | Type safety | Catch API shape mismatches at compile time |
| TailwindCSS | 3 | Styling | Zero runtime CSS; consistent design tokens |
| shadcn/ui | latest | Primitive components | Accessible, unstyled base; Tailwind compatible |
| TanStack Query | 5 | Server state | Caching, polling, mutation lifecycle |
| React Router | 7 | Routing | Nested routes, data loaders, deep linking |
| Leaflet | 1.9.4 | Map rendering | Consistent with existing viewer; zero cost |
| React-Leaflet | 4 | Leaflet bindings | Declarative layer management |
| Recharts | 2 | Data visualization | SVG-based, composable, zero cost |
| React Hook Form | 7 | Form state | AOI form, export form, query form |
| Zod | 3 | Schema validation | Validate API responses at runtime |
| Framer Motion | 11 | Micro-animations | Sidebar, drawers only |
| Zustand | 4 | Client state | Lightweight; AOI selection, map state, UI state |
| Vitest | 1 | Unit tests | Vite-native, fast |
| React Testing Library | 14 | Component tests | Behavior-driven testing |
| Playwright | 1 | E2E tests | Phase 11; cross-browser |

**Zero-cost compliance:** All technologies above are MIT or Apache 2.0 licensed and have no
recurring cost for development or hosting. Leaflet CDN replaced by npm package in Phase 10.

---

## 13. Data Visualization Guide

### 13.1 WQ Trend Chart (Recharts LineChart)

**Component:** `WQTrendChart`
**Data:** `GET /waterbody/{id}/observations?obs_type=chlorophyll_a` (last 30 days)
**Chart type:** Line chart, time X axis, value Y axis
**Axes:** X = created_at (day ticks), Y = value (unit label from obs)
**Data point color:** confidence-based (red/orange/yellow per `confidenceColor` util)
**Tooltip:** date, value, evidence_class badge, confidence %
**Empty state:** "No observations in the selected period"

```
Chl-a (µg/L)
40 │          ●
30 │       ●  │
20 │    ●──●──●──●
10 │
   └──────────────── Date
```

### 13.2 Bloom Risk Forecast Bar (Recharts BarChart)

**Component:** `BloomRiskForecastBar`
**Data:** `GET /waterbody/{id}/forecasts` (WaterQualityForecast kind=forecast)
**Chart type:** Bar chart, 7 bars (one per day), error bars for CI
**Y axis:** bloom risk probability 0–1 (or µg/L if available)
**Error bars:** `uncertainty.ci_lower` / `uncertainty.ci_upper` as errorbar lines
**Bar color:** gradient from green (low) to red (high) based on value
**Footer:** "90% confidence interval shown" + `_attribution`

### 13.3 Anomaly Timeline (custom SVG or Recharts ScatterChart)

**Component:** `AnomalyTimeline`
**Data:** `GET /waterbody/{id}/anomalies` (AnomalyDetector predictions)
**Visualization:** Horizontal timeline; anomaly markers sized by |z-score|
**Marker color:** z ≥ 3 = red, z ≥ 2 = orange, z < 2 = yellow
**Tooltip:** date, z-score value, direction (positive/negative)
**Click:** `onExplainClick(predictionId)` → navigate to Anomaly Explanation

### 13.4 Trajectory Player (Leaflet + custom controls)

**Component:** `TrajectoryPlayer`
**Data:** `GET /aois/{id}/predictions` (OilTrajectory frames)
**Visualization:** GeoJSON polygons on Leaflet; each frame = one timestamp
**Animation:** clearLayers() + addLayer() at 1 fps default
**Controls:** play/pause, frame slider, speed selector (0.5x/1x/2x)
**Opacity:** `0.08 + 0.3 * (i / max(n-1, 1))` — increasing opacity as time progresses
**Color:** `#38bdf8` (sky-400) consistent with current viewer

### 13.5 Risk Score Gauge (Recharts RadialBarChart)

**Component:** `RiskScoreGauge`
**Data:** `uncertainty.risk_score` from FloodRisk prediction (0–1)
**Visualization:** Semi-circular gauge, 0–1 scale
**Color:** same risk color mapping as FloodRiskBadge
**Label:** numeric score centered

### 13.6 Acid Risk Gauge (custom SVG arc)

**Component:** `AcidRiskGauge`
**Data:** `acid_risk_index` from AcidDepositionRisk (0–10)
**Visualization:** Arc gauge 0–10; uncertainty_range shown as shaded arc segment
**Thresholds:** 0–4 green, 4–7 amber, 7–10 red
**Label:** index value + "/10" + "NOT a pH measurement" (always visible)

### 13.7 Quota Bar (linear progress bar)

**Component:** `QuotaBar`
**Data:** StatusResponse quota / open_meteo_calls_today
**Visualization:** Horizontal progress bar
**Color:** < 60% = green, 60–80% = amber, > 80% = red
**Warn behavior:** Pulsing border at > 80%

### 13.8 Choke Point Map (Leaflet circleMarkers)

**Component:** `ChokePointMapLayer`
**Data:** `GET /aois/{id}/choke-points`
**Visualization:** Blue circle markers on map
**Size:** `radius = 4 + Math.round(score * 8)` — consistent with existing viewer
**Opacity:** `0.4 + score * 0.5` fill opacity
**Color:** `#60a5fa` (blue-400)
**Popup:** upstream_area_km2, constriction_score, dem_source, evidence_class

### 13.9 Observation Confidence Map (Leaflet GeoJSON polygons)

**Component:** `ObservationLayer`
**Data:** `GET /aois/{id}/observations`
**Visualization:** GeoJSON polygons, color from `confidenceColor(obs.confidence)`
**Popup:** obs_type, confidence %, area_km2, status badge, evidence_class

### 13.10 Impact ETA Cards (custom card list)

**Component:** `ImpactETAList`
**Data:** `GET /aois/{id}/impact`
**Visualization:** Vertical list of cards; each shows exposure_layer_id + eta_hours
**ETA formatting:** `${eta_hours.toFixed(1)} h` — 1 decimal place
**Metric display:** first key from `metrics` dict + formatted value

### 13.11 Domain Status Grid (4-up cards)

**Component:** `DomainStatusGrid`
**Data:** `GET /status` → `domain_runs`
**Visualization:** 2×2 grid of `DomainStatusCard`
**Status indicator:** green dot = complete, red dot = failed, amber = partial
**Shows:** domain_id, last_run_at (relative time), scenes_fetched, observations_created

### 13.12 System Quota Summary (inline with status)

Two `QuotaBar` components in `SystemStatusPanel`:
- CDSE: bytes_today / (daily_limit_gb × 1e9)
- Open-Meteo: calls_today / 10000

### 13.13 AI Confidence Badge (inline text badge)

**Component:** used inside `ExplanationCard`
**Values:** `"low"` | `"medium"` | `"high"` from ExplanationResponse
**Colors:** low=amber, medium=blue, high=green (not risk colors — confidence is different)

---

## 14. AI Experience

### 14.1 Citation Rendering

All AI text (`text`, `answer`, `hypothesis`) may contain inline citation references.
Citations are record IDs from the store (Observation IDs or Prediction IDs).

**Rendering rule:** The `citations` array in AI responses lists record IDs in order of
first appearance. Render inline markers as superscript numbers: `text[1]`, `text[2]`.
Superscripts are clickable → open `CitationViewer` with that record ID.

**CitationViewer lookup:** Record IDs are UUIDs. The viewer tries:
1. `GET /waterbody/{id}/observations` where obs id matches — if found, show ObservationSchema fields
2. Falls back to showing the raw ID if not resolvable

The citation panel is a slide-in drawer (not a modal) to preserve context.

### 14.2 Offline Mode Handling

When `model === "template"`:
- Render `OfflineBanner` at top of AI panel: "AI offline — showing templated report"
- Yellow background, visible without scrolling
- Report/answer text is still rendered (templated text is still useful)
- Do NOT show spinner indefinitely

### 14.3 Advisory Honesty Pattern

`ExplanationResponse.advisory` is the human-action recommendation from the AI. It must:
- Always be rendered above the fold (not inside an accordion)
- Prefix with "ADVISORY:" in bold
- Include the human-in-the-loop note: "Human verification recommended before action."
- The confidence badge must appear adjacent to the advisory, not separated

### 14.4 Read-Only Query Interface

Per OQ-E (resolved), the NL query interface is read-only. `POST /query` never executes
write actions. The `ReadOnlyNotice` component renders a permanent banner:

> "This interface is read-only. Write actions are not supported."

This notice must be visible without scrolling, above the query input box.

### 14.5 Loading States for AI

AI endpoints (report, explanation, query) can take 2–8 seconds. Use:
1. Skeleton placeholder (not spinner) for report text
2. "Generating…" text in the query submit button while request is in flight
3. Disable submit button during loading (prevent double submission)
4. On error: clear loading state + show `ErrorMessage` with "AI query failed. Retry?"

---

## 15. Phase 10 Implementation Plan

### F-045: Frontend Scaffold

**Goal:** `frontend/` directory with working Vite build served by FastAPI.

**Files created:**
- `frontend/package.json`
- `frontend/vite.config.ts`
- `frontend/tsconfig.json`
- `frontend/tailwind.config.ts`
- `frontend/src/main.tsx`
- `frontend/src/App.tsx` (router setup)
- `frontend/index.html`
- `argus/api/app.py` — add StaticFiles mount for `frontend/dist/`

**Acceptance criteria:**
- `npm run build` in `frontend/` produces `argus/api/static/dist/`
- FastAPI serves the React app at `/`
- React Router routes render without 404 on direct navigation
- All 14 dependencies installed with correct versions
- TypeScript strict mode enabled, no type errors

**Dependencies to install:**
```
react react-dom react-router-dom @tanstack/react-query zustand
leaflet react-leaflet recharts framer-motion react-hook-form zod
@types/react @types/react-dom @types/leaflet
tailwindcss @tailwindcss/vite autoprefixer
shadcn-ui vitest @testing-library/react
```

---

### F-046: Overview Dashboard

**Goal:** `/overview` screen showing all-domain health at a glance.

**Files created:**
- `frontend/src/screens/OverviewScreen.tsx`
- `frontend/src/components/domain/DomainStatusCard.tsx`
- `frontend/src/components/domain/DomainStatusGrid.tsx`
- `frontend/src/components/shared/SystemStatusPanel.tsx`
- `frontend/src/components/shared/QuotaBar.tsx`
- `frontend/src/components/shared/AlertFeedPanel.tsx`
- `frontend/src/components/wq/WaterBodySummaryTable.tsx`
- `frontend/src/hooks/useStatus.ts`
- `frontend/src/hooks/useAOIs.ts`
- `frontend/src/hooks/useWaterbodies.ts`

**Acceptance criteria:**
- All 4 domain status cards visible without scrolling on 1080p
- CDSE and Open-Meteo quota bars displayed with correct values
- Auto-refresh every 60 seconds (SystemStatusPanel)
- WaterBodySummaryTable shows all target_ids from `GET /waterbodies`
- `last_analysis_run_at` formatted as relative time ("2h ago")
- Empty state when no AOI configured: "No AOIs configured. Add an AOI in Admin → AOIs."

---

### F-047: WQ Monitoring Panel

**Goal:** `/waterbody/:targetId` with trend chart, anomaly timeline, forecast bar.

**Files created:**
- `frontend/src/screens/WQMonitoringScreen.tsx`
- `frontend/src/screens/AnomalyExplanationScreen.tsx`
- `frontend/src/screens/SituationReportScreen.tsx`
- `frontend/src/components/wq/WQTrendChart.tsx`
- `frontend/src/components/wq/BloomRiskForecastBar.tsx`
- `frontend/src/components/wq/AnomalyTimeline.tsx`
- `frontend/src/components/wq/ObservationTable.tsx`
- `frontend/src/components/ai/ReportViewer.tsx`
- `frontend/src/components/ai/ExplanationCard.tsx`
- `frontend/src/components/ai/CitationViewer.tsx`
- `frontend/src/components/shared/EvidenceClassBadge.tsx`
- `frontend/src/hooks/useWQObservations.ts`
- `frontend/src/hooks/useWQForecasts.ts`
- `frontend/src/hooks/useWQAnomalies.ts`
- `frontend/src/hooks/useWQReport.ts`
- `frontend/src/hooks/useExplanation.ts`

**Acceptance criteria:**
- Chl-a trend chart renders with 30-day window; evidence_class badge on tooltip
- 90% CI shown as shaded band in BloomRiskForecastBar (not just a line)
- Anomaly z-scores displayed numerically in AnomalyTimeline
- "Explain" button on each anomaly navigates to `/waterbody/:id/anomaly/:predId`
- ExplanationCard advisory text is above the fold, prefixed "ADVISORY:"
- AI report renders with clickable citation numbers
- `model: "template"` triggers OfflineBanner

---

### F-048: Hazard Prediction Panel

**Goal:** `/hazard/*` sub-panels for oil, flood risk, acid risk.

**Files created:**
- `frontend/src/screens/HazardOilScreen.tsx`
- `frontend/src/screens/HazardFloodScreen.tsx`
- `frontend/src/screens/HazardAcidScreen.tsx`
- `frontend/src/screens/ChokePointsScreen.tsx`
- `frontend/src/components/hazard/TrajectoryPlayer.tsx`
- `frontend/src/components/hazard/FrameInfoCard.tsx`
- `frontend/src/components/hazard/ImpactETAList.tsx`
- `frontend/src/components/hazard/FloodRiskBadge.tsx`
- `frontend/src/components/hazard/RiskScoreGauge.tsx`
- `frontend/src/components/hazard/AcidRiskGauge.tsx`
- `frontend/src/components/hazard/ChokePointTable.tsx`
- `frontend/src/components/hazard/HonestyLabel.tsx`
- `frontend/src/components/map/ArgusMap.tsx`
- `frontend/src/components/map/ObservationLayer.tsx`
- `frontend/src/components/map/ChokePointMapLayer.tsx`
- `frontend/src/components/map/LayerToggleControl.tsx`
- `frontend/src/hooks/usePredictions.ts`
- `frontend/src/hooks/useImpact.ts`
- `frontend/src/hooks/useChokePoints.ts`
- `frontend/src/hooks/useFloodRisk.ts`
- `frontend/src/hooks/useAcidRisk.ts`

**Acceptance criteria:**
- TrajectoryPlayer plays at 1 fps; speed control (0.5x/1x/2x) works
- Trajectory opacity increases with frame index (later = more opaque)
- FloodRisk risk_level color matches spec: extreme=red, high=orange, medium=amber, low=green
- HonestyLabel "Modeled flood risk at choke point — not a measured flood" always visible
- AcidRiskGauge shows uncertainty range as shaded arc
- "NOT a pH measurement" label always visible (not in tooltip)
- CC BY 4.0 attribution in panel footer for flood and acid screens
- Choke points sorted by constriction_score descending

---

### F-049: AI Assistant Interface

**Goal:** `/ai/*` screens for NL query, report viewing, AI hub.

**Files created:**
- `frontend/src/screens/AIHubScreen.tsx`
- `frontend/src/screens/NLQueryScreen.tsx`
- `frontend/src/components/ai/NLQueryBox.tsx`
- `frontend/src/components/ai/GroundedAnswerPanel.tsx`
- `frontend/src/components/ai/ModelBadge.tsx`
- `frontend/src/components/ai/OfflineBanner.tsx`
- `frontend/src/components/ai/ReadOnlyNotice.tsx`
- `frontend/src/components/shared/AttributionFooter.tsx`
- `frontend/src/hooks/useNLQuery.ts`

**Acceptance criteria:**
- `ReadOnlyNotice` visible above the query box, always (cannot be dismissed)
- Submit button disabled during loading; shows "Generating…" text
- Answer renders with clickable citation markers
- `CitationViewer` slides in from right on citation click
- `OfflineBanner` shown when `model === "template"`
- Session query history shown below the form (newest first, max 10)
- Error state: "AI query failed. Please try again." with retry button

---

### F-050: Admin Panel

**Goal:** `/admin/*` read-only admin screens.

**Files created:**
- `frontend/src/screens/AdminAOIsScreen.tsx`
- `frontend/src/screens/AdminAlertsScreen.tsx`
- `frontend/src/screens/AdminDomainsScreen.tsx`
- `frontend/src/components/admin/AOITable.tsx`
- `frontend/src/components/admin/DomainToggleMatrix.tsx`
- `frontend/src/components/admin/AlertThresholdCard.tsx`
- `frontend/src/components/domain/DomainTagList.tsx`

**Acceptance criteria:**
- AOITable lists all AOIs from `GET /aois` with domains shown as DomainTagList
- AlertThresholdCard shows HAB (z > 2.5σ, bloom > 25 µg/L), Flood (high/extreme), Acid (≥ 7.0)
- Alert channel URLs masked (first 8 chars + "***")
- DomainToggleMatrix is read-only in Phase 10 (toggles disabled, shows current state)
- "Admin controls are read-only in this version" notice on admin pages

---

### F-051: Export and Reporting UI

**Goal:** `/export/*` screens with GeoJSON/CSV/PDF download.

**Files created:**
- `frontend/src/screens/ExportGeoJSONScreen.tsx`
- `frontend/src/screens/ExportCSVScreen.tsx`
- `frontend/src/screens/ExportPDFScreen.tsx`
- `frontend/src/components/export/ExportForm.tsx`
- `frontend/src/components/export/PDFPreview.tsx`
- `frontend/src/utils/downloadFile.ts`
- `frontend/src/utils/toGeoJSON.ts`
- `frontend/src/utils/toCSV.ts`

**Acceptance criteria:**
- GeoJSON export includes `evidence_class` in every feature properties object
- CSV export includes: id, obs_type, evidence_class, value, unit, area_km2, confidence, created_at
- GeoJSON and CSV exports are client-side (no new backend endpoint in Phase 10)
- PDF export uses `window.print()` with print CSS; server PDF is Phase 11
- Print CSS hides sidebar and header; shows map screenshot placeholder
- CC BY 4.0 attribution in print footer

**Note:** `argus/api/routers/export.py` (server-side PDF with reportlab/weasyprint) is
deferred to Phase 11. Phase 10 delivers the client-side download pathway.

---

## 16. Phase 11 Frontend Requirements

Phase 11 (F-052–F-056) requires the following frontend work:

### F-052: E2E Integration Tests (Playwright)

- E2E test suite in `frontend/e2e/` using Playwright
- Tests for each primary user journey (§3)
- Offline mode test: verify OfflineBanner shown when API returns `model: "template"`
- Citation rendering test: verify citation numbers are clickable and CitationViewer opens
- Attribution test: verify CC BY 4.0 text is present on flood/acid screens

### F-053: Performance Validation

- Lighthouse score ≥ 90 for Performance on `/overview`
- First Contentful Paint < 2 seconds on localhost
- Time to Interactive < 3 seconds on localhost
- All React Query cache hits measured; no redundant fetches on route transitions

### F-054: Documentation

- `frontend/README.md` — setup, build, environment variables
- `docs/api/API_SPEC.md` update — confirm all 19 endpoints are documented with Phase 10 examples
- `docs/features/phase-10.md` update — mark all F-045–F-051 as DONE

### F-055: Demo Dataset Validation

- Run demo dataset through full pipeline; verify all 4 domains produce observations
- Verify AI reports render with real record IDs as citations (not mocked)
- Verify trajectory player animates correctly with real frames

### F-056: MVP Sign-off Checklist (Frontend)

- [ ] All 18 screens render without console errors
- [ ] All 19 API endpoints consumed by the UI
- [ ] `evidence_class` badge visible for every displayed observation
- [ ] CC BY 4.0 attribution visible on all weather/hydro panels
- [ ] "NOT a pH measurement" honesty label visible on acid risk screen
- [ ] Honesty label visible on flood risk screen
- [ ] ReadOnlyNotice visible on AI query screen
- [ ] `OfflineBanner` shown when `model === "template"`
- [ ] CitationViewer opens on citation click
- [ ] TrajectoryPlayer plays and pauses
- [ ] Export downloads a valid file
- [ ] All user journeys (§3) achievable without backend source inspection
- [ ] Lighthouse Performance ≥ 90 on `/overview`

---

## 17. Traceability Matrix

### 17.1 Screen → PRD Requirement → API Endpoint

| Screen | PRD FR | API endpoints used |
|---|---|---|
| Overview Dashboard | FR-18 | /status, /aois, /waterbodies |
| WQ Monitoring | FR-5, FR-10, FR-13 | /waterbody/{id}/observations, /forecasts, /anomalies, /report |
| Anomaly Explanation | FR-15 | /anomaly/{id}/explanation |
| Situation Report | FR-13 | /waterbody/{id}/report |
| NL Query | FR-14 | /query |
| Hazard — Oil | FR-8 | /aois/{id}/observations, /predictions, /impact |
| Hazard — Flood | FR-11 | /aois/{id}/flood-risk, /choke-points |
| Hazard — Acid | FR-11 | /aois/{id}/acid-risk |
| Choke Points | FR-7 | /aois/{id}/choke-points |
| AI Assistant Hub | FR-13, FR-14, FR-15 | all AI endpoints |
| Admin — AOIs | FR-1 | /aois, /aois/{id} |
| Admin — Alerts | FR-19 | /status (domain_runs) |
| Admin — Domains | FR-1 | /aois |
| Export — GeoJSON | FR-19 | /aois/{id}/observations |
| Export — CSV | FR-19 | /waterbody/{id}/observations |
| Export — PDF | FR-19 | /waterbody/{id}/report + print CSS |

### 17.2 Component → INV Rule

| Component | INV rule enforced |
|---|---|
| `EvidenceClassBadge` | INV-3: every value carries evidence_class |
| `HonestyLabel` | INV-3: modeled/inferred values never implied measured |
| `AttributionFooter` | INV-4: all claims attributed; CC BY 4.0 for Open-Meteo |
| `ReadOnlyNotice` | OQ-E: NL query is read-only |
| `OfflineBanner` | INV-4: AI offline fallback visible (not hidden) |
| `AcidRiskGauge` label | INV-3: "NOT a pH measurement" never omitted |
| `FloodRiskBadge` + `HonestyLabel` | INV-3: modeled badge + honesty label |
| `ChokePointMapLayer` popup | INV-3: evidence_class="inferred" shown |
| `ModelBadge` | INV-4: model provenance always visible |
| `CitationViewer` | INV-4: every cited claim resolvable to a record |

### 17.3 Feature → Component Mapping

| Feature | Key components |
|---|---|
| F-045 | AppShell, Header, Sidebar, ArgusMap, Router |
| F-046 | DomainStatusGrid, SystemStatusPanel, QuotaBar, AlertFeedPanel, WaterBodySummaryTable |
| F-047 | WQTrendChart, BloomRiskForecastBar, AnomalyTimeline, ExplanationCard, ReportViewer, CitationViewer |
| F-048 | TrajectoryPlayer, FloodRiskBadge, RiskScoreGauge, AcidRiskGauge, ChokePointTable, HonestyLabel, all map layers |
| F-049 | NLQueryBox, GroundedAnswerPanel, CitationViewer, ModelBadge, OfflineBanner, ReadOnlyNotice |
| F-050 | AOITable, DomainToggleMatrix, AlertThresholdCard |
| F-051 | ExportForm, PDFPreview, downloadFile, toGeoJSON, toCSV |

---

## 18. Presentation Assets Checklist

For demo, stakeholder review, or deployment:

### 18.1 Screenshots Required

- [ ] Overview Dashboard — all 4 domain cards + WQ summary table
- [ ] WQ Monitoring — chl-a chart + anomaly timeline + bloom forecast bar
- [ ] Anomaly Explanation — ExplanationCard with advisory visible
- [ ] AI Query — question + grounded answer + citation panel open
- [ ] Hazard Oil — oil slick on map + trajectory player paused at frame 3
- [ ] Hazard Flood — risk badge + choke point map layer
- [ ] Hazard Acid — acid gauge + "NOT a pH measurement" label
- [ ] Choke Points — blue circle markers on map + table
- [ ] Export — GeoJSON form + download trigger
- [ ] Admin AOIs — AOI table with domain tags

### 18.2 Demo Data Requirements

- At least 1 AOI configured (tobago.geojson is the reference AOI)
- At least 5 oil_slick observations with different confidence values
- At least 1 OilTrajectory prediction with 6+ ForecastFrames
- At least 1 ImpactAssessment with eta_hours
- At least 10 chlorophyll_a observations spanning 14 days
- At least 1 WaterQualityForecast prediction with 7 day values
- At least 1 AnomalyDetector prediction with sigma > 2.5
- At least 1 FloodRisk prediction with risk_level="high"
- At least 1 AcidDepositionRisk prediction with acid_risk_index > 7.0
- At least 3 ChokePoint records with varying constriction_score
- At least 1 AI report per target_id in the store

### 18.3 Deployment Steps (Production)

1. Build: `cd frontend && npm run build` → produces `argus/api/static/dist/`
2. Verify `VITE_API_BASE_URL` set to Cloud Run URL
3. Deploy FastAPI to Cloud Run (`ARGUS_ENV=production`)
4. Verify FastAPI serves `/` → React SPA
5. Verify React Router deep links work (FastAPI must serve index.html for all `/` paths)
6. Add `StaticFiles` catch-all in `argus/api/app.py` for SPA routing

### 18.4 FastAPI SPA Mount (Required in F-045)

```python
# In argus/api/app.py (F-045 scope):
from fastapi.staticfiles import StaticFiles
from pathlib import Path

_DIST = Path(__file__).parent / "static" / "dist"
if _DIST.exists():
    # Serve the React SPA; must be mounted AFTER all API routers
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="frontend")
```

---

## 19. Living Document Rules

### 19.1 When to Update This Document

Update this document (and increment the version number) when:

- A new screen is added to the navigation
- A component's TypeScript props interface changes
- A new API endpoint is added or an existing endpoint's response shape changes
- A design token (color, spacing) changes
- A technology is added, removed, or version-pinned
- A user journey changes materially
- An INV rule is added or modified that affects the UI

Do NOT update this document for:
- Implementation detail changes within an existing component
- Bug fixes that don't change the component's contract
- CSS class changes that don't affect the design system tokens

### 19.2 Versioning

Format: `MAJOR.MINOR`
- MAJOR: navigation structure change, new domain, or breaking API change
- MINOR: new component, updated props, new screen, design token change

Current version: **1.0**

### 19.3 Change Log

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-06-28 | Initial document — Phase 10 blueprint complete |

### 19.4 Governance

This document is owned by the project lead (Josh). Changes that affect:
- Navigation architecture → require review before implementation
- INV rule enforcement in UI → require review and may require a new ADR
- Technology stack additions → require zero-cost compliance check (INV-1)

Deferred items (not in this version):
- Server-side PDF generation (`argus/api/routers/export.py`) — Phase 11
- Write operations in Admin panel (PATCH/POST AOI, alert config) — post-MVP
- Live alert feed via WebSocket — post-MVP
- Multi-tenant / multi-user support — post-MVP
- Dark/light mode toggle — post-MVP
