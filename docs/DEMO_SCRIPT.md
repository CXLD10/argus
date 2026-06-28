# Argus — Live Demo Script

- **Duration:** 8–10 minutes
- **Audience:** Technical evaluators, clients, hiring managers, investors
- **Setup:** Option A or B from DEMO_MODE.md; browser at `http://localhost:5173`
- **Key message:** Free public satellite data → multi-domain hazard intelligence → plain-English answers

---

## Before You Start (5 min prior)

- [ ] Backend running: `argus serve` (check `http://localhost:8000/health` returns `{"status":"ok"}`)
- [ ] Frontend running: `cd frontend && pnpm dev`
- [ ] Browser open at `http://localhost:5173`
- [ ] Gulf of Paria selected in the AOI dropdown (top-left of header)
- [ ] If using Option B: database seeded with `argus run --aoi gulf-paria-tt --since 2026-06-17`
- [ ] Terminal visible in background (optional, impressive for technical audiences)

---

## Script

### Opening (30 seconds)

> "This is Argus — a water health intelligence platform that fuses free satellite imagery and
> open weather data into actionable environmental intelligence. What you're looking at is the
> full system running on a laptop, with zero recurring cost for data. Let me walk you through
> an active incident scenario."

**[Click the header AOI dropdown, confirm "Gulf of Paria — Trinidad & Tobago" is selected]**

---

### 1. Overview Page — The full picture (1 minute)

**[You should be on `/` — the Overview page]**

> "The overview gives the duty officer a complete situational picture in one screen. At the
> top: live KPIs across all four monitoring domains — an active oil slick, flood risk at high,
> acid deposition index at 6.8, two active alerts."

**[Point to the KPI bar]**

> "The map shows everything we've detected for this AOI. The amber polygon is a 5.1 square
> kilometre oil slick detected this morning. The violet markers are hydrological choke points —
> narrow flow sections that concentrate flood risk."

**[Point to the map, then to the right panel]**

> "On the right: a live events list sorted by severity — red border means extreme, orange is
> high. And below it, an AI-generated brief. Every sentence in that brief is grounded to a
> specific observation ID from our store. The AI cannot invent a value."

---

### 2. Map Page — Spatial awareness (45 seconds)

**[Click "Map" in the sidebar — route `/map`]**

> "The full-screen map. We can toggle layers independently."

**[Click the layer manager icon (top-right of map)]**

> "Turn off the choke points layer... and back on. Each layer toggle controls a GeoJSON group
> served live from the API."

**[Click on the oil slick polygon]**

> "Clicking any observation opens the detail drawer — evidence class 'measured', that means
> directly detected in Sentinel-1 SAR imagery. Confidence 85%, area 5.1 square kilometres,
> detected 02:14 UTC this morning."

---

### 3. Oil Monitoring — Domain depth (1 minute)

**[Click "Oil Monitoring" in the sidebar — route `/oil`]**

> "The oil domain page goes deeper. Left panel: a map with the slick polygons and — when a
> trajectory is available — the drift forecast footprints overlaid."

**[Point to the observations list on the right]**

> "Two slicks in the store. The larger one, five-point-one km² at 85% confidence, was just
> detected. The smaller one at 72% is two days old — you can see it fading on the map."

> "Below that: the trajectory prediction. This is our OilTrajectory predictor — it runs an
> OpenDrift particle simulation using Copernicus ocean current data and Open-Meteo wind forcing.
> The uncertainty grows over time: by T+72h, the particle spread is 18 kilometres. The system
> is honest about what it doesn't know."

---

### 4. Water Quality — Inland domain (45 seconds)

**[Click "Water Quality" in the sidebar — route `/water-quality`]**

> "Switching domains entirely — inland water quality. Sentinel-2 and Sentinel-3 optical imagery,
> processed into chlorophyll-a, turbidity, CDOM, and surface temperature."

**[Click on a water body in the left sidebar if available, or point to the trend chart]**

> "The trend chart shows chlorophyll-a in Lake Nariva over the last 30 days. That red marker
> at the right edge is today's reading: 28.4 micrograms per litre — 2.8 standard deviations
> above the seasonal baseline. That's a triggered HAB early warning."

**[Point to the AI report panel on the right]**

> "And here's the AI situation report — those superscript numbers are numbered citations.
> Each one links to a specific observation ID. The AI assistant cannot make a claim without
> citing a record. That's enforced at the code level."

---

### 5. Hydro + Choke Points — Multi-hazard (1 minute)

**[Click "Hydro" in the sidebar — route `/hydro`]**

> "The hydro page shows two risk indices. FloodRisk is a weighted combination: 50%
> precipitation forecast, 30% river discharge, 20% choke-point constriction. Right now it's
> 0.71 — in the 'high' band. The label says 'modeled flood risk, not a measured flood.'
> That's intentional. We're rigorous about what we know versus what we've modelled."

**[Click "Choke Points" in the sidebar — route `/choke-points`]**

> "Three choke points for this AOI, derived from the Copernicus 30m digital elevation model.
> The Caroni River outlet has a constriction score of 0.87 — the highest. That means
> essentially all of the 1,240 km² upstream catchment drains through a single narrow point.
> That's why the flood risk is high: heavy rain + constrained outlet."

---

### 6. Predictions — Time-stepping (45 seconds)

**[Click "Predictions" in the sidebar — route `/predictions`]**

> "The predictions page has the trajectory frame player. I'll step through the frames."

**[Click Next frame a few times]**

> "Each frame is a six-hour step. The footprint grows — that's the uncertainty interval, not
> slippage. By frame 12 — T+72h — the probable contact zone covers this stretch of coastline."

**[Point to the gauges below]**

> "The flood and acid risk gauges are also here. All of these come from validated predictors.
> The skill gate in our evaluation harness filters out any predictor that doesn't beat a
> persistence baseline on historical data. If it's displayed, it's been validated."

---

### 7. AI Assistant — Natural language (1.5 minutes)

**[Click "AI" in the sidebar — route `/ai`]**

> "This is the part people always want to know about."

**[Type in the NL query box:]** `"What are the most urgent hazards in the current AOI?"`

> "The AI reads from the store — it's read-only by design. Watch this."

**[Wait for response, then type:]** `"Run a new domain analysis for Gulf of Paria"`

> "The system refuses. Write actions are blocked. The AI can answer questions about the data
> but it cannot trigger runs, change configuration, or modify the store. That refusal happens
> before any LLM call — it's a keyword guard, not a politeness filter."

**[Click on a water body to load its situation report in the right panel]**

> "The situation report on the right is the AI's full synthesis — three paragraphs, numbered
> citations, a triage recommendation. Advisory, not a decision. Humans stay in the loop."

---

### 8. Admin — Observability (30 seconds)

**[Click "Admin" in the sidebar — route `/admin`]**

> "The admin page shows quota health. CDSE has a 1 GB per day satellite download limit. The
> gauge is green at 12% today. Open-Meteo: 847 of our 10,000 daily API calls used. The domain
> run summary shows all four domains completed successfully in the last run cycle."

---

### 9. Exports (20 seconds)

**[Click "Exports" in the sidebar — route `/exports`]**

> "Everything is exportable as GeoJSON with evidence_class on every record. Suitable for
> loading into QGIS, ArcGIS, or any geospatial tool."

---

### Closing (30 seconds)

> "What you've just seen is the full platform — four observation domains, five validated
> predictors, a grounded AI assistant, twelve dashboard pages — running on publicly available
> satellite data with zero data cost. The entire system runs end-to-end for a new area of
> interest in under ten minutes on this laptop."

> "The architecture is designed so that adding a fifth domain requires implementing three
> methods and touching zero existing files. The platform is designed to scale — Vercel for
> the frontend, GCP Cloud Run for the API, which scales to zero when no one is using it."

**[Pause for questions]**

---

## Common Questions and Answers

**Q: How long does a real analysis run take?**
A: Phase 11 is implementing the performance validation, but preliminary runs complete all four
domains for a 200×200 km AOI in 4–8 minutes on a modern laptop. Target is under 10 minutes.

**Q: How much does this cost to operate?**
A: In development, zero. In production (GCP Cloud Run + Vercel), near-zero at idle — Cloud Run
scales to zero between requests. The main cost would be satellite download during active runs,
which is bounded by the CDSE 1 GB/day quota.

**Q: How does this compare to paid services like Maxar or Planet?**
A: Paid services offer higher resolution and more frequent revisit times. Argus is designed for
organizations that need environmental intelligence at zero data cost and are willing to work
with Sentinel's 10–40m resolution and ~5-day revisit.

**Q: Can this run unattended?**
A: Yes. The APScheduler in Phase 8 runs domain analyses on a configured schedule. The alert
pipeline fires webhooks or emails when thresholds are crossed.

**Q: Can you add another geographic area?**
A: Yes — create a GeoJSON file in `config/aois/` with the bounding box and enabled domains.
The new AOI appears in the dropdown on the next server restart.

**Q: What data can the AI access?**
A: Only what's in the platform store. It cannot search the internet, access external databases,
or make real-time API calls during a response. It reads observations, predictions, impact
assessments, and situation reports generated by the platform's own pipeline.

---

## Backup Slides (if demo environment fails)

If the live demo fails, fall back to this description of key screens:

1. **Architecture diagram** — show `docs/architecture/ARCHITECTURE.md` §2 (component map)
2. **API spec** — open `docs/api/API_SPEC.md` — 21 endpoints, 4 domain groups
3. **Test suite** — `pytest tests/ -v` (offline, runs in ~30 seconds)
4. **Code walkthrough** — `argus/domains/marine_oil/detector.py` → `argus/api/routes/` →
   `frontend/src/pages/OverviewPage.tsx`

---

## Timing Reference

| Section | Target Time | Cumulative |
|---|---|---|
| Opening | 0:30 | 0:30 |
| 1. Overview | 1:00 | 1:30 |
| 2. Map | 0:45 | 2:15 |
| 3. Oil Monitoring | 1:00 | 3:15 |
| 4. Water Quality | 0:45 | 4:00 |
| 5. Hydro + Choke Points | 1:00 | 5:00 |
| 6. Predictions | 0:45 | 5:45 |
| 7. AI Assistant | 1:30 | 7:15 |
| 8. Admin | 0:30 | 7:45 |
| 9. Exports | 0:20 | 8:05 |
| Closing | 0:30 | 8:35 |
| Buffer for questions | — | ~10:00 |
