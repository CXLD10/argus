# Argus User Guide

- **Platform:** Argus Environmental Intelligence Platform v0.1.0
- **Last updated:** 2026-06-29
- **Audience:** Platform operators, environmental officers, analysts

---

## What Argus Does

Argus is a water health monitoring platform. It automatically gathers satellite imagery and
weather data, analyzes it for environmental hazards, and turns the results into plain-language
summaries you can act on.

In plain English, Argus watches for:
- **Oil spills** in coastal and marine waters — where the slick is now, where it will drift,
  and which shorelines are at risk
- **Harmful algal blooms** — lakes and reservoirs with elevated chlorophyll-a, turbidity, or
  other markers of deteriorating water quality
- **Flood risk** — where rainfall and river discharge are converging at flow constriction points
  in a watershed
- **Acid deposition risk** — atmospheric SO₂ and NO₂ combined with precipitation, which can
  acidify sensitive water bodies

Argus does not measure pH, dissolved nutrients, heavy metals, or pathogens — those require
physical sampling. It tells you *where to look*, not what you'll find when you get there.

---

## Starting the System

### Backend API

```bash
# Activate the Python environment
source .venv/bin/activate

# Start the API server (default: http://localhost:8000)
argus serve

# With a custom database path
argus serve --db-path /path/to/argus.db --port 8000
```

The API is ready when you see: `Uvicorn running on http://127.0.0.1:8000`.

### Frontend Dashboard

```bash
cd frontend
pnpm dev     # development mode: http://localhost:5173
# OR
pnpm build   # build for production
```

In production, the backend serves the frontend automatically at `http://localhost:8000/`.

---

## The Dashboard — Page by Page

### Overview (`/`)

The **home screen**. Gives you a complete situational picture at a glance.

**What you see:**
- **KPI bar** (top row, 4 cards): live counts from all active domains — observations detected,
  flood risk level, acid risk index, active alerts
- **Map** (left, 60%): all detected observations for the selected AOI, color-coded by type
- **Right panel** (40%): Live Events list, AI Brief summary, System Health indicators

**How to use it:**
1. Select your Area of Interest (AOI) from the dropdown in the header
2. The map and panels update automatically
3. Click any event in the Live Events list to see its detail on the map
4. The AI Brief is a one-paragraph grounded summary — click "View Full Report" for citations

**Left-border colors on events:**
- Red border = extreme severity
- Orange = high
- Yellow = medium
- Green = low / informational

---

### Map (`/map`)

Full-screen interactive map with all observation layers.

**What you see:**
- All observations for the selected AOI, plotted as GeoJSON polygons
- Oil slicks in amber/red (color intensity = confidence)
- Water quality observations as point markers
- Choke points as violet circle markers (size ∝ constriction score)
- Layer toggle panel (top-right): show/hide individual layers

**How to use it:**
- Click any observation polygon to open the **detail drawer** (top-right)
- The drawer shows: obs_type, confidence %, evidence class, status, area, ID
- Use the Layer Manager to show/hide specific observation types
- Press Escape to dismiss the Layer Manager

---

### Oil Monitoring (`/oil`)

Detailed view for the marine oil domain (D1).

**What you see:**
- Map panel showing detected oil slicks and (when available) trajectory prediction footprints
- Oil slick list: each slick shows confidence, area (km²), evidence class, detection date
- Trajectory section: latest OilTrajectory prediction with frame-by-frame drift footprints

**Understanding the data:**
- `evidence_class: measured` — the dark patch was detected in Sentinel-1 SAR imagery
- Trajectory footprints show the probable drift path at T+6h, T+12h, …, T+72h
- Uncertainty grows with time: the footprint expands because particle spread increases

---

### Water Quality (`/water-quality`)

Inland water body monitoring (D2: chlorophyll-a, turbidity, CDOM, surface temperature).

**What you see:**
- **Water body selector** (left sidebar): list of all water bodies with WQ observations in the store
- **Trend chart** (main): time series of the selected observation type over the last 30 days
- **Observations table** (below chart): raw observations with evidence class and confidence
- **AI Report panel** (right): grounded situation report for the selected water body

**How to use it:**
1. Click a water body in the left sidebar
2. Select the observation type (chlorophyll-a, turbidity, etc.) from the tabs
3. The chart updates to show that metric's history
4. The AI Report auto-loads on the right — scroll down for numbered citations

**Understanding the data:**
- `evidence_class: measured` here means "optical proxy" — derived from satellite reflectance,
  not a direct chemical measurement. Calibration affects absolute accuracy.
- Anomalies (red/orange markers on the chart) indicate statistically significant departures
  from the seasonal baseline for that water body

---

### Hydro (`/hydro`)

Flood risk and acid deposition risk for the selected AOI.

**What you see:**
- **FloodRisk gauge**: 0–1 score with risk level badge (low/medium/high/extreme)
- **AcidDepositionRisk gauge**: 0–10 scale

**Understanding the data:**

**FloodRisk** combines three components:
- 50% precipitation forecast (Open-Meteo)
- 30% river discharge (GloFAS)
- 20% maximum choke-point constriction

Risk levels: low < 0.35 · medium 0.35–0.55 · high 0.55–0.75 · extreme ≥ 0.75

**This is not a measured flood.** It is a modeled risk index. Act on it by alerting downstream
operators and monitoring choke points — not by assuming inundation has occurred.

**AcidDepositionRisk** combines SO₂, NO₂, and precipitation accumulation into a 0–10 index.
**This is not a pH measurement.** It is an atmospheric precursor indicator. Water body pH
requires physical sampling.

---

### Choke Points (`/choke-points`)

Hydrological flow constriction points derived from DEM analysis (D4).

**What you see:**
- Map showing choke point locations as violet markers
- Sorted list of choke points by constriction score (highest first)
- Each card shows: constriction score (0–1), upstream catchment area (km²), DEM source

**Understanding the data:**
- `constriction_score = 1.0` means maximum flow restriction — all upstream water passes through
  a single narrow point
- `evidence_class: inferred` — these points are derived from flow-accumulation modelling on
  a 30m digital elevation model, not directly observed from orbit
- Use for flood response prioritization: high-score choke points are where flow concentrates first

---

### Alerts (`/alerts`)

Consolidated alert list across all domains.

**What you see:**
- Sorted list of alerts with left-border severity (extreme/high/medium/low)
- Each alert shows: domain label (e.g. "D1 · Marine Oil"), description, timestamp
- Filter by severity or domain (planned Phase 11)

**Alert types:**
| Alert | Domain | Trigger |
|---|---|---|
| Oil slick detected | D1 Marine Oil | Detection confidence above threshold |
| HAB early warning | D2 Inland WQ | Chl-a anomaly z-score > 2.5σ AND forecast > 25 µg/L |
| Flood risk elevated | D3 Weather/Hydro | risk_level ∈ {high, extreme} |
| Acid deposition risk | D3 Weather/Hydro | acid_risk_index ≥ 7.0 |

---

### Predictions (`/predictions`)

All model prediction outputs for the selected AOI.

**What you see:**
- **Trajectory frame player**: step through OilTrajectory forecast frames (T+0 through T+72h)
  - Previous/next frame buttons, frame counter (e.g. "T+3/12")
- **FloodRisk gauge** and **AcidRisk gauge** from the latest predictions

**How to use the trajectory player:**
- Use Previous/Next to step through frames
- The footprint polygon grows and shifts as time progresses
- The frame timestamp tells you when that footprint is valid

---

### AI Assistant (`/ai`)

Natural-language interface to the platform data.

**Left panel — Chat:**
Type a question in plain English. The AI reads from the store and answers with citations.

**Example questions:**
- "What oil slick detections happened in the last 7 days?"
- "Which choke point has the highest constriction score?"
- "Is the chlorophyll-a level in Lake Nariva elevated?"
- "What is the current flood risk and what's driving it?"

**Right panel — Situation Reports:**
Select a water body from the list to load a full AI-generated situation report with numbered
citation references.

**Important: this AI is advisory only.**
- It reads data from the store — it does not run domain analyses or change any configuration
- It will refuse write-action questions ("run the oil domain", "update the AOI")
- Every factual claim in the answer is numbered and links to a specific observation or prediction
- Citation `¹` means the AI is citing a real record from the store, not generating from memory
- The advisory label means a human must review and decide before any action is taken

**When the AI is offline** (`ARGUS_AI_OFFLINE=true`), responses are generated from a
deterministic template. The `model` field reads `"template"` in this case.

---

### Admin (`/admin`)

System status and configuration overview.

**What you see:**
- **System Status card**: version, store accessibility, last analysis run timestamp, Open-Meteo call count
- **CDSE Daily Quota gauge**: bytes downloaded today vs. 1 GB limit
- **Open-Meteo Calls gauge**: calls today vs. 10,000 limit
- **Domain Run Summary**: last run per domain, scenes fetched, observations created, status
- **Areas of Interest**: list of configured AOIs with enabled domains and active status

**Quota gauges:**
- Green = below 60% used
- Amber = 60–80%
- Red = above 80% (risk of hitting daily limit)

If CDSE usage approaches the 1 GB limit, domain runs that fetch new imagery will be refused
by the quota guard until the next UTC day.

---

### Settings (`/settings`)

Environment configuration and data source reference.

**What you see:**
- Environment configuration table (read-only in development)
- Data source quota reference: CDSE 1 GB/day, Open-Meteo 10k calls/day, etc.

This page is informational only. Configuration changes require editing `config/settings.yaml`
and restarting the server.

---

### Exports (`/exports`)

Download platform data as JSON.

**What you see:**
- Export buttons for: Observations, Flood Risk Predictions, Acid Risk Predictions, Choke Points

**How to use it:**
- Click "Download" on any export type
- The button is disabled (greyed out) if no data exists for that type in the current AOI
- Downloads are client-side JSON snapshots of the current store state

**What's in each export:**
| Export | Contents |
|---|---|
| Observations | All observations for the AOI with obs_type, evidence_class, geometry, confidence |
| Flood Risk | FloodRisk predictions with risk_score, risk_level, uncertainty |
| Acid Risk | AcidDepositionRisk predictions with acid_risk_index, uncertainty |
| Choke Points | Choke point locations with constriction_score, upstream_area_km2 |

All exports include `evidence_class` on every record per the platform honesty invariant (INV-3).
GeoJSON geometries are in EPSG:4326 (WGS-84, lon/lat order).

---

## Understanding Evidence Classes

Every observation and prediction in Argus carries an `evidence_class` tag. This tells you
how the value was produced and how much to trust it:

| Class | Meaning | Example |
|---|---|---|
| `measured` | Directly observed from satellite imagery, via optical or SAR analysis | Oil slick area from Sentinel-1 SAR; chlorophyll-a from Sentinel-2 reflectance |
| `modeled` | Computed by a numerical or statistical model | Flood risk score; acid deposition risk index; oil trajectory prediction |
| `inferred` | Derived or interpreted from other data | Choke point locations from DEM flow-accumulation; bloom presence from spectral indices |

**Practical guidance:**
- `measured` values can be used for incident reporting but carry calibration uncertainty
- `modeled` values are useful for risk assessment but should not be reported as measurements
- `inferred` values are analytical products — useful for prioritization but require ground-truth verification

---

## Understanding the AI Citations

When the AI assistant or situation report produces a numbered citation (like `¹` or `[obs-abc123]`),
this means the AI found a specific record in the platform store that supports that claim.

**What to do with citations:**
1. Note the record ID (e.g. `obs-abc123`)
2. You can fetch the full record from the API: `GET /aois/{aoi_id}/observations`
3. Look for the matching `id` in the response to see the raw observation data

Citations in the AI Assistant use a numbered format: `¹`, `²`, `³`. Each number links to the
observation or prediction that backs the claim.

If the AI says something without a citation, that is a defect to report — the grounding guard
should have caught it.

---

## Frequently Asked Questions

**Q: Why does the map show nothing after I select an AOI?**
A: The store is empty for that AOI. You need to run a domain analysis first:
`argus run --aoi <slug> --since YYYY-MM-DD`. See the Developer Onboarding guide.

**Q: The AI report says "template" for the model. Is something wrong?**
A: The platform is running in offline mode (`ARGUS_AI_OFFLINE=true`) or the Anthropic API
is unavailable. Template mode produces deterministic reports without LLM inference. The
content is less nuanced but structurally valid.

**Q: The flood risk gauge shows "high" but I don't see actual flooding. Should I evacuate?**
A: No — flood risk is a modeled index, not a measured flood. It indicates elevated probability
based on rainfall, discharge, and choke-point constriction. Use it to alert downstream
operators and increase monitoring frequency, not as a direct flood determination.

**Q: Can I ask the AI to trigger a new domain run?**
A: No. The AI assistant is read-only by design. Write actions (running domains, updating
configuration) require direct CLI or API access. The AI will politely refuse any write-action
question.

**Q: What does the CDSE quota gauge measure?**
A: Copernicus Data Space Ecosystem download quota. The free general-user tier allows up to
1 GB of Sentinel imagery per day. The gauge shows today's (UTC) consumption. If you hit the
limit, domain runs that require downloading new imagery will be blocked until midnight UTC.

**Q: The acid risk index is 7.2. What does that mean for water pH?**
A: Nothing directly. The acid deposition risk index measures atmospheric precursors (SO₂ and NO₂)
combined with precipitation — it indicates *potential* for acid rain, not measured water pH.
Actual water pH requires in-situ sampling. A high index is a signal to collect samples, not
a pH reading.

**Q: How do I add a new Area of Interest?**
A: Create a GeoJSON file at `config/aois/<slug>.geojson` with the required fields (`id`,
`name`, `geometry`, `domains`, `active`). Restart the server. The new AOI will appear in
the header dropdown. See the Developer Onboarding guide for the schema.
