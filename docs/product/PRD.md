# Argus — Product Requirements Document

- **Status:** v2.1 — MVP definition updated (supersedes v2.0 two-tier milestone model)
- **Owner:** Josh
- **Last updated:** 2026-06-27
- **Related:** [ARCHITECTURE.md](../architecture/ARCHITECTURE.md) · [ROADMAP.md](../../ROADMAP.md) · [DATA_MODELS.md](../architecture/DATA_MODELS.md) · [adr/](../adr/) · [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)
- **Governed by:** ADR-0003, ADR-0004, ADR-0005, ADR-0006

---

## 1. Summary

Argus is a **water health intelligence platform**. It fuses free Earth-observation and weather
data into actionable intelligence about the state and near-future of water bodies: it monitors
lakes/reservoirs for deteriorating quality (algal blooms, turbidity), predicts rain-driven
flooding, models acid-deposition risk, finds hydrological choke points, and detects marine oil
slicks with drift forecasts. A **prediction engine** turns observation history + weather into
forecasts and risk with uncertainty; an **AI layer** turns those structured outputs into
plain-language reports and natural-language answers. Everything runs on **free tiers** in
**WSL** with a **zero-budget** constraint.

---

## 2. Problem Statement

Water health is monitored today in fragments: a city environmental office tracks a few lakes
by occasional manual sampling; a stormwater team models flooding in a separate GIS tool; air
quality lives in another system; nobody has a forward-looking, water-centric picture that is
cheap to run. The raw ingredients are free and open — Sentinel optical/SAR imagery, Copernicus
DEM, Open-Meteo weather/flood/air-quality — but nobody has assembled
**observe → predict → assess → explain** into one platform a municipal user can run.

Argus does, and it does so **without over-claiming**.

---

## 3. Target Users & Jobs-to-be-Done

| Persona | Job-to-be-done | What Argus gives them |
|---|---|---|
| Municipal water/environmental officer | "Catch water-quality decline in my lakes early." | Per-water-body chl/turbidity trends + anomaly alerts + bloom-risk forecast |
| Watershed/lake-management district | "Prioritize sampling across many water bodies." | Ranked water bodies by deterioration/risk + NL summary report |
| Stormwater/drainage engineer | "Know where flooding will concentrate before the storm." | Rain-flood risk at DEM choke points from precip + discharge forecasts |
| Public-health official | "Get warned about HABs near recreation/drinking sources." | HAB early-warning alerts with confidence + plain-language brief |
| Spill-response coordinator (marine) | "Confirm a spill and predict its drift." | Oil detection + 6–72h trajectory + impact ETA |
| Environmental NGO / researcher | "Study events cheaply and ask questions in plain language." | Historical re-runs + NL query over the platform's records |

**Non-users (MVP):** the general public, certified evidence-grade reporting, real-time vessel tracking.

---

## 4. Goals and Non-Goals

### 4.1 Goals

- **G1** Multi-domain observation across D1–D4 behind a shared spine
- **G2** Prediction engine: forecasts/risk with uncertainty, history-validated
- **G3** Anomaly early-warning: flag departures from per-water-body baseline
- **G4** AI layer: grounded NL reports and NL queries
- **G5** Impact & alerting: tie risks to exposure; deliver alerts + products
- **G6** Honesty by design: never conflate measured / modeled / not-observable
- **G7** Zero budget: runs end-to-end on free tiers in WSL

### 4.2 Non-Goals (MVP)

- Full chemical assay (dissolved N/P, metals, pathogens, pH not observable from orbit)
- Deep-learning detection needing GPU budget
- Production HA / multi-tenant auth / SLAs
- Real-time (sub-hourly) processing
- Any recurring infrastructure cost

---

## 5. MVP Definition (Authoritative — ADR-0005)

The MVP is the **complete Argus Environmental Intelligence Platform**. There is no
"Vertical-Slice MVP" or "Platform MVP." Those terms are retired.

The MVP is achieved only when **all** of the following are true:

**Observation coverage:**
- D1 marine oil: operational (SAR detection + trajectory + impact)
- D2 inland water quality: operational (chl-a/turbidity/CDOM/temp + anomaly + forecast)
- D3 weather/hydro: operational (precip/discharge/SO₂/NO₂ ingestion)
- D4 choke points: operational (DEM-derived drainage + choke nodes)

**Prediction engine:**
- OilTrajectory: validated (SkillReport.passed_gate = True)
- WaterQualityForecast: validated, beats persistence baseline
- AnomalyDetector: validated, low false-alarm rate
- FloodRisk: validated against historical storm events
- AcidDepositionRisk: implemented (modeled, labeled)

**AI layer:**
- NL situation reports: grounded, 100% citation rate
- NL query: grounded, read-only, cited answers
- Anomaly explanation: advisory, confidence-labeled, human-in-the-loop
- Alert summarization: functional

**Data integrations:**
- CDSE (Sentinel-1/2/3/5P): functional, quota-aware
- Open-Meteo (forecast/ERA5/GloFAS/air-quality): functional, CC BY 4.0 attributed
- Copernicus DEM/HydroSHEDS: functional
- CMEMS metocean forcing: functional (oil trajectory)

**Delivery:**
- HTTP API: all endpoints documented + tested
- Alert delivery: webhook + email, explicit config
- Product export: GeoJSON + PNG for all domains
- Automated scheduling: per-domain polling, quota-aware, idempotent

**UI/UX Dashboard:**
- Production-quality frontend (not a prototype)
- Multi-domain overview
- Per-lake water quality monitoring panel
- Hazard prediction maps (flood risk, acid risk, oil trajectory)
- AI assistant interface (NL query + reports)
- System administration panel (AOI config, domain config, alert rules)
- Export/reporting UI

**Validation:**
- All 22 architecture validators pass
- End-to-end run < 10 min per AOI on a laptop
- Zero recurring cost confirmed
- F-056 MVP sign-off checklist complete

---

## 6. What Is and Is Not Observable (Binding Design Constraint — ADR-0003 D3)

| Quantity | Status | How Argus treats it |
|---|---|---|
| Chlorophyll-a, turbidity/TSS, CDOM, surface temp | **Measured optical proxy** (calibration-dependent) | Reported as trend/anomaly; absolute values only with in-situ calibration |
| Algal/cyanobacteria bloom presence | **Inferred** from chlorophyll/spectral indices | Reported as bloom-risk with confidence |
| Dissolved N/P, heavy metals, pathogens, pH | **NOT observable from orbit** | Never reported as measurement; eutrophication inferred via proxies, flagged as inference |
| Acid rain | **Not measured; modeled** | Reported only as modeled acid-deposition risk index (precursors × precip), labeled as model output |
| Rain-flood occurrence | **Predicted risk** | Probabilistic risk at choke points; observed inundation confirmed post-hoc via SAR |
| Water bodies below ~0.1–0.5 ha | **Below resolution** (Sentinel-2 10m) | Marked `below_resolution`; not silently estimated |

---

## 7. Functional Requirements

### Spine
- **FR-1** Define AOIs and water bodies (polygons) with domain(s), hazard config, resolution eligibility
- **FR-2** Search/ingest source data per domain (CDSE S1/2/3/5P; Open-Meteo; DEM), quota-aware
- **FR-3** Persist scenes/observations/detections in a queryable store keyed by domain, water body, time, type, status

### Domains
- **FR-4 (D1)** Detect oil slicks in Sentinel-1 SAR with configurable oil-type input
- **FR-5 (D2)** Compute per-water-body chl-a, turbidity/TSS, CDOM, surface temp from S2/S3
- **FR-6 (D3)** Ingest precip forecast/history, GloFAS discharge, SO₂/NO₂
- **FR-7 (D4)** Derive drainage network + choke-point nodes from free DEM

### Prediction Engine (Tier A)
- **FR-8** Forecast oil drift with configurable oil type; uncertainty + provenance
- **FR-9** Forecast water-quality indices / bloom-risk with CI
- **FR-10** Detect anomalies vs. per-water-body seasonal baseline
- **FR-11** Compute flood risk at choke points + acid-deposition risk index
- **FR-12** Every prediction carries uncertainty + provenance; history-validated before UI trust

### AI Layer (Tier B)
- **FR-13** Generate grounded NL reports; every claim cited to a record id
- **FR-14** Answer NL queries by translating to store queries; grounded, cited answers
- **FR-15** Draft advisory anomaly explanations + recommended actions (human-in-the-loop)

### Impact, Delivery, Alerting
- **FR-16** Intersect forecasts/risk with exposure layers; report ETA
- **FR-17** HTTP API exposing all data, forecasts, reports
- **FR-18** Web map + dashboard UI (all domains, predictions, AI)
- **FR-19** Alert delivery (webhook/email) + portable products (GeoJSON/PNG)
- **FR-20** Automated per-domain polling on schedule, idempotent, quota-aware

---

## 8. Non-Functional Requirements

- **NFR-1 Cost:** zero recurring spend; all sources free tier; Open-Meteo CC BY 4.0 attributed
- **NFR-2 Environment:** runs bare in WSL on a laptop
- **NFR-3 Reproducibility:** pinned product IDs + fixed RNG seeds
- **NFR-4 Domain modularity:** adding a domain never edits the spine or prediction/AI interfaces
- **NFR-5 Quota safety:** track transfer/calls per source; prefer subsets; back off near limits
- **NFR-6 Observability:** structured logs + run records per stage; recoverable, re-runnable
- **NFR-7 Licensing:** copyleft components isolated behind process/service boundaries
- **NFR-8 Honesty:** measured/modeled/not-observable distinct in data, API, and UI
- **NFR-9 AI grounding:** generated text references only structured records; no invented values

---

## 9. Success Metrics

| Metric | MVP Target |
|---|---|
| Oil detection P/R | ≥ 0.70 each |
| WQ proxy agreement | Establishes baseline vs. reference |
| Anomaly precision | Low false-alarm (tuned on eval set) |
| WQ forecast skill | Beats persistence baseline |
| Flood-risk skill | Reports hit/false-alarm vs. observed inundation |
| Trajectory self-consistency | Reports km error at T+24/48h |
| AI grounding rate | 100% (ungrounded = defect) |
| Time-to-alert | < 10 min, one AOI, laptop |
| Recurring cost | $0 |

---

## 10. Evaluation Datasets

- **D1 oil:** historical spills with SAR coverage (e.g. Tobago 2024) + clean negative
- **D2 inland WQ:** lakes with documented bloom events + stable reference lake
- **D3 weather/hydro:** historical storm events with known flooding, scored vs. SAR inundation
- EvalCases store references only (product IDs, API params) — no raw imagery

---

## 11. Open Questions

Canonical tracking: [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)

- OQ-A: resolved (ADR-0005)
- OQ-B: choke-point definition — OPEN
- OQ-C: in-situ calibration data — OPEN
- OQ-D: LLM model tier — OPEN
- OQ-E: NL-query read-only — OPEN (default yes)
- OQ-F: resolved (ADR-0006)
