# Argus — System Architecture

- **Status:** v2.2 (Phases 0–10 implemented; Phase 11 pending)
- **Last updated:** 2026-06-29
- **Supersedes:** root `ARCHITECTURE.md` (v2.0)
- **Related:** [PRD.md](../product/PRD.md) · [DATA_MODELS.md](DATA_MODELS.md) · [STACK.md](STACK.md) · [ADR index](../adr/)
- **Change log v2.2:** Phase 10 dashboard implemented (React 19, Vite 8, Tailwind v4, 12 pages, design system v2);
  OQ-B resolved 2026-06-28; all 4 domains + 5 predictors + AI layer implemented.
- **Change log v2.1:** MVP redefined to full platform per ADR-0005; OQ-A resolved; Phase 10/11 added.

---

## 1. Architectural Style

Argus is a **staged, event-producing pipeline** behind a thin service layer, with a
**domain-agnostic spine** and three plug-in axes:

1. **Observation domains** — `(source + analyzer)` plug-ins that write observations into the
   shared store (marine oil, inland water quality, weather/hydro, choke points).
2. **Predictors** — numerical/ML models that consume observation history + weather and emit
   forecasts/risk with uncertainty (trajectory, WQ forecast, flood risk, acid-risk, anomaly).
3. **AI assistant** — a grounded LLM layer that turns structured outputs into NL reports and
   answers NL queries.

The metadata store is the backbone: stages communicate by writing/reading durable records,
never shared in-memory state — so every step is inspectable, re-runnable, and idempotent.

Three invariants drive every boundary:
- **Domains are additive plug-ins** (INV-2/NFR-4): adding one never edits the spine, the
  `Predictor` interface, or the AI layer.
- **Isolate copyleft** (INV-7/NFR-7): `OpenDrift` (GPLv2) and any copyleft hydrology tool run
  behind a subprocess boundary. Only `argus/domains/marine_oil/sim_worker.py` imports opendrift.
- **Honesty invariant** (INV-3/NFR-8) and **AI grounding** (INV-4/NFR-9): measured / modeled /
  inferred stay distinct; the LLM never originates a value.

---

## 2. Component Map

```
┌──────────────────────────────── ARGUS Environmental Intelligence Platform ─────────────────────────────────────┐
│                                                                                                                  │
│  OBSERVATION DOMAINS (plug-in: Domain protocol)                                                                  │
│  ┌─────────────┐ ┌──────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐                          │
│  │ D1 marine   │ │ D2 inland water  │ │ D3 weather & hydro  │ │ D4 choke points     │                          │
│  │ oil (S1 SAR)│ │ quality (S2/S3)  │ │ (Open-Meteo, S5P)   │ │ (DEM/HydroSHEDS)    │                          │
│  └──────┬──────┘ └────────┬─────────┘ └──────────┬──────────┘ └──────────┬──────────┘                          │
│         └─────────────────┴───────────┬──────────┴───────────────────────┘                                     │
│                                       ▼                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐   │
│  │                SPINE: tasking · ingestion · METADATA + ARTIFACT STORE · impact · delivery                │   │
│  └─────────────────────────────────────┬───────────────────────────────────────────────────────────────────┘   │
│                     ┌──────────────────┼────────────────────────┐                                               │
│                     ▼                  ▼                        ▼                                                │
│  TIER A — PREDICTION ENGINE (Predictor plug-ins)       TIER B — AI ASSISTANT (grounded LLM)                     │
│  ┌──────────────┐ ┌──────────────────┐ ┌───────────────┐   ┌───────────────────────────────────────────┐       │
│  │ OilTrajectory│ │ WaterQualityFcst  │ │ FloodRisk /   │   │ NL reports · NL query · anomaly explain   │       │
│  │ (OpenOil,iso)│ │ + AnomalyDetector │ │ AcidRiskIndex │   │ · alert summary  (records-grounded)       │       │
│  └──────┬───────┘ └────────┬──────────┘ └──────┬────────┘   └────────────────────┬──────────────────────┘       │
│         │                  │                   │                                  │                              │
│         ▼                  ▼                   ▼                                  ▼                              │
│  ┌──────────────────┐  ┌──────────────────────────────┐              ┌────────────────────┐                     │
│  │ metocean forcing │  │ Open-Meteo (precip, ERA5,    │              │   API (FastAPI)     │──▶ Phase 10 UI      │
│  │ (CMEMS, winds)   │  │ GloFAS, air-quality)         │              │   + Phase 10        │    (React/Vite)     │
│  └──────────────────┘  └──────────────────────────────┘              └────────┬───────────┘                     │
│                                                                                ▼                                 │
│                                                                          Alerting & products                    │
│  Cross-cutting: config · structured logging · run records · eval harness · honesty/grounding guards             │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Stage and Layer Responsibilities

### Spine (domain-agnostic) — `argus.core`, `argus.tasking`, `argus.ingest`, `argus.impact`, `argus.api`, `argus.alert`

- **Tasking** holds AOIs and water bodies; decides what each domain fetches.
- **Ingestion** wraps each source (CDSE Sentinel-1/2/3/5P; Open-Meteo HTTP; DEM/HydroSHEDS),
  quota-aware, preferring subsets (INV-6).
- **Store** (`argus.core.store`) is the single accessor for all records (INV-6/ADR-0002 D5).
  No module outside `argus.core.store` imports sqlite3 directly.
- **Impact** intersects forecasts/risk with exposure layers.
- **Delivery/API/alerting** export products, serve the API, and emit alerts (explicit config).

### Observation Domains (plug-in) — `argus.domains.*`

Each domain implements the `Domain` protocol: `search → acquire → analyze → Observation[]`.

- **D1 `marine_oil`** — S1 SAR dark-spot detection → `Observation(obs_type="oil_slick")`.
- **D2 `inland_wq`** — S2/S3 → chlorophyll-a, turbidity/TSS, CDOM, surface-temp observations,
  each with a `calibration_state` (relative vs. calibrated). See [D2 spec](../domains/D2-inland-wq.md).
- **D3 `weather_hydro`** — Open-Meteo (precip, ERA5, GloFAS, air-quality) + S5P + S1 inundation
  → hazard-input `Observation`s + `WeatherSeries`. See [D3 spec](../domains/D3-weather-hydro.md).
- **D4 `hydro_chokepoints`** — DEM → flow-direction/accumulation → choke-point nodes.
  BLOCKED on OQ-B. See [D4 spec](../domains/D4-choke-points.md).

### Tier A — Prediction Engine (plug-in) — `argus.predict.*`

A `Predictor` interface; implementations: `OilTrajectory` (OpenOil, isolated subprocess),
`WaterQualityForecast`, `AnomalyDetector`, `FloodRisk`, `AcidDepositionRisk`. Every output is a
`Prediction` with **uncertainty + provenance**, history-validated before UI trust
(ADR-0004 D1, INV-8). API never shows a prediction without `passed_gate=True` (F-029).

### Tier B — AI Assistant (grounded) — `argus.ai.*`

An `Assistant` service over the store + Tier A outputs: NL situation reports, NL query
(text → store-query → grounded answer), anomaly explanation/triage, alert summarization.
**Reads only structured records; every claim cited; no invented values** (INV-4/ADR-0004 D2).
Depends on the store/predictors, never the reverse. Falls back to templated reports when
offline (`ARGUS_AI_OFFLINE=true`). See [AI Assistant spec](../ai/ASSISTANT.md).

### Phase 10 Production UI — `frontend/` — IMPLEMENTED

React 19 + Vite 8 + Tailwind CSS v4 unified dashboard. All data flows through the FastAPI HTTP
API — no direct store access from the frontend. Built to `frontend/dist/` and served by FastAPI's
`StaticFiles` mount.

**Technology:** React 19, Vite 8, TypeScript (strict), Tailwind CSS v4 (`@theme` tokens,
`@tailwindcss/vite` plugin), shadcn/ui (New York, Neutral), TanStack Query v5 (server state),
Zustand v5 (client state), React Leaflet (map), Recharts (charts), Lucide Icons, pnpm.

**12 pages (React Router routes):**

| Route | Page | Primary data |
|---|---|---|
| `/` | Overview | `/status`, `/aois/{id}/observations` |
| `/map` | MapPage | `/aois/{id}/observations`, `/aois/{id}/choke-points` |
| `/oil` | OilMonitoringPage | `/aois/{id}/observations?obs_type=oil_slick`, `/predictions` |
| `/water-quality` | WaterQualityPage | `/waterbody/{id}/observations`, `/waterbody/{id}/report` |
| `/hydro` | HydroPage | `/aois/{id}/flood-risk`, `/aois/{id}/acid-risk` |
| `/choke-points` | ChokePointsPage | `/aois/{id}/choke-points` |
| `/alerts` | AlertsPage | `/aois/{id}/observations` (all domains) |
| `/predictions` | PredictionsPage | `/aois/{id}/predictions` (ForecastFrames) |
| `/ai` | AIAssistantPage | `POST /query`, `/waterbody/{id}/report` |
| `/admin` | AdminPage | `/status`, `/aois` |
| `/settings` | SettingsPage | static config display |
| `/exports` | ExportsPage | `/aois/{id}/observations`, `/aois/{id}/predictions` etc. |

**Design system v2:** Inter + JetBrains Mono via Google Fonts; CSS shadow token system
(`--shadow-xs` through `--shadow-xl`); type scale utility classes; page-enter route animations;
left-border severity pattern; Perplexity-style citation badges; card variants (elevated, interactive,
inset, ghost); Zustand stores for AOI selection, map layer state, sidebar state.

**Demo data:** `frontend/src/lib/fixtures.ts` — Gulf of Paria, Trinidad scenario with 6
observations (2 oil slicks, 2 chl-a, 1 turbidity, 1 precip), flood risk high (0.71), acid
risk 6.8, 3 choke points, complete AI situation report.

**State management:**
- `aoiStore` — `selectedAOI`, `selectedObservation`
- `mapStore` — `activeLayers: Set<string>` (toggleable map layer visibility)
- `uiStore` — `sidebarOpen: boolean`

### Cross-cutting — `argus.core`

Config, structured logging, store accessor, run records, eval harness, honesty/grounding guards.
All evidence_class tagging is enforced at the store boundary (VAL-004).

---

## 4. End-to-End Data Flows

**D1 Marine Oil:**
```
AOI → S1 search → acquire subset → preprocess(σ⁰ dB, mask) → oil detection
  └→ OilTrajectory(OpenOil subprocess + forcing) → ForecastFrames → impact → products + alert
```

**D2 Inland Water Quality:**
```
water body + time window
  └→ S2/S3 search → acquire AOI subset → atmospheric/water masking
        └→ inland_wq analyzer → Observation(chl-a, turbidity, CDOM, temp; calibration_state)
              ├→ AnomalyDetector → Prediction(anomaly vs. seasonal baseline)
              └→ WaterQualityForecast → Prediction(n-day bloom-risk + CI)
                    └→ impact (intake/recreation exposure) → products + AI report + alert
```

**D3/D4 Hydro:**
```
DEM → flow accumulation → choke-point nodes
Open-Meteo precip forecast + GloFAS → FloodRisk @ choke points → impact + alert
SO₂/NO₂ (S5P / Open-Meteo) × precip → AcidDepositionRisk index (modeled, labeled)
```

---

## 5. Key Interfaces (Stable — Do Not Modify Without ADR)

```python
# argus/domains/base.py
class Domain(Protocol):
    domain_id: str           # "marine_oil"|"inland_wq"|"weather_hydro"|"hydro_chokepoints"
    def search(self, target: MonitorTarget, t0, t1) -> list[SourceRef]: ...
    def acquire(self, ref: SourceRef) -> Acquisition: ...
    def analyze(self, acq: Acquisition) -> list[Observation]: ...

# argus/predict/base.py
class Predictor(Protocol):
    predictor_id: str
    def predict(self, ctx: PredictContext, rng_seed: int) -> Prediction: ...
    def validate(self, history: EvalSet) -> SkillReport: ...

# argus/ai/base.py
class Assistant(Protocol):
    def report(self, scope: Scope) -> GroundedText: ...
    def answer(self, question: str, scope: Scope) -> GroundedAnswer: ...
```

Adding a domain = implement `Domain` + register + (optional) a `Predictor` + an exposure layer.
Spine, `Predictor` interface, and AI layer are untouched (INV-2).

---

## 6. Technology Stack

See [STACK.md](STACK.md) for the complete stack with license and cost validation.

**Summary:** Python 3.11+, SQLite + filesystem (MVP), FastAPI, React+Vite+Tailwind (Phase 10),
Copernicus/Open-Meteo free tiers, OpenDrift (subprocess-isolated), scikit-learn (CPU-only ML).

Zero recurring cost. All tools open-source or free-tier. See [QUOTAS.md](../standards/QUOTAS.md).

---

## 7. Deployment and Runtime

### Development (local WSL — all phases)

```bash
argus run --domain inland_wq --target lake_x --since 2026-01-01
argus serve  # FastAPI + viewer; React dev server in Phase 10
```

State is a local SQLite DB + `data/artifacts/` directory, rebuildable from product IDs / API
params. OpenDrift and copyleft hydrology tools run as isolated subprocesses.

### Production (post-MVP — ADR-0008)

The platform is intended to run continuously for real users after the MVP sign-off:

```
Frontend   → Vercel (React dashboard; free Hobby plan; automatic HTTPS + CDN)
API        → GCP Cloud Run (FastAPI container; scales to zero; pay per request)
Artifacts  → GCP Cloud Storage bucket (persistent across Cloud Run instances)
Secrets    → GCP Secret Manager (injected as env vars at Cloud Run startup)
CI/CD      → GitHub Actions → Artifact Registry → Cloud Run deploy
```

**Scale-to-zero is mandatory** (INV-10): Cloud Run min-instances = 0. No always-on VMs.
GCP $300 credits are expected to last many months at this usage pattern.

Database migration from SQLite → PostgreSQL (Cloud SQL or Supabase) is deferred to Phase 11
and will be documented in a separate ADR before provisioning. The `argus.core.store` accessor
makes this a single-file swap (ADR-0002 D5).

---

## 8. Internal Checkpoints (Not MVP Milestones)

See [ADR-0005](../adr/ADR-0005-mvp-redefinition.md). MVP = CP-4 only.

| Checkpoint | End of Phase | Scope |
|---|---|---|
| CP-1 | Phase 3 | Oil pipeline complete, API live |
| CP-2 | Phase 7 | WQ + prediction + AI operational |
| CP-3 | Phase 9 | All 4 domains + automation |
| CP-4 = **MVP** | Phase 11 | Production UI, full validation, Josh sign-off |

---

## 9. Deferred Complexity

| Deferred | Why Safe | When |
|---|---|---|
| PostGIS / object storage | SQLite+FS at MVP scale | post-MVP |
| Scheduler / unattended | manual per-event run for MVP | Phase 8 |
| In-situ calibration ingestion | relative/anomaly works without it | when reference data exists |
| Deep-learning detection | classic CV + GBM hits CPU targets | post-MVP, optional |
| D4 choke points full depth | blocked on OQ-B | Phase 9 |
| Multi-tenant auth / HA | single-operator local tool | out of scope |

---

## 10. Open Architectural Questions

See [OPEN_QUESTIONS.md](../product/OPEN_QUESTIONS.md) for current status.

- **OQ-B:** Choke-point definition → blocks Phase 9 / F-040
- **OQ-C:** In-situ calibration source → blocks absolute WQ metrics in F-026
- **OQ-D:** LLM model tier and token budget → blocks F-030
- **OQ-E:** NL-query read-only confirmation → blocks F-032 (default: yes)
