# Argus

**Environmental Intelligence Platform — observe, predict, assess, explain.**

Argus fuses free Earth-observation and weather data into actionable intelligence about
water bodies and water-related hazards. It monitors lakes and reservoirs for deteriorating
water quality, predicts rain-driven flooding, models acid-deposition risk, locates hydrological
choke points, and detects marine oil slicks with drift forecasts — then surfaces everything in
plain-language reports and answers questions in natural language.

Everything runs on **free public data** in **WSL** at **zero recurring cost**.

---

## Why Argus

Water health is monitored in fragments today: periodic manual lake sampling here, a separate
flood GIS there, air quality in another system. The raw ingredients to do better already exist
and are free — Sentinel optical and SAR imagery, Copernicus DEM, Open-Meteo weather and flood
forecasts — but nobody has assembled **observe → predict → assess → explain** into one
water-centric platform a municipal team can actually operate. Argus does, without requiring a
cloud budget, a data-science team, or overconfident outputs.

---

## Honesty by Design

Argus is explicit about what is **measured**, what is **modeled**, and what is **not
observable from orbit**. This is a binding design invariant, not a disclaimer.

| What Argus reports | How it is labeled |
|---|---|
| Chlorophyll-a, turbidity, CDOM, surface temperature | `measured` — optical proxy (calibration-dependent) |
| Algal bloom presence | `inferred` — derived from spectral indices |
| Oil drift forecast | `modeled` — trajectory simulation |
| Flood risk at choke points | `modeled` — probabilistic risk |
| Acid-deposition risk | `modeled` — atmospheric precursor index (0–10 scale) |
| pH, dissolved N/P, metals, pathogens | **Not reported** — not observable from orbit |

Every value-bearing record carries `evidence_class ∈ {measured, modeled, inferred}`.
The AI layer reads only from the structured store and cites every factual claim to a record id.
It never originates an environmental value.

---

## Capabilities

### Observation Domains

| Domain | Source | What it produces |
|---|---|---|
| **D1 Marine oil** | Sentinel-1 SAR | Oil slick detections + 6–72 h drift trajectory + exposure ETA |
| **D2 Inland water quality** | Sentinel-2/3 optical | Per-lake chlorophyll-a, turbidity, CDOM, surface temperature; anomaly detection |
| **D3 Weather & hydro** | Open-Meteo, Sentinel-5P | Precipitation forecasts, GloFAS river discharge, SO₂/NO₂ atmospheric concentrations |
| **D4 Hydrological choke points** | Copernicus DEM / HydroSHEDS | Drainage network + constriction nodes at flood-concentration points |

### Prediction Engine (Tier A)

| Predictor | Method | Output |
|---|---|---|
| **OilTrajectory** | OpenOil particle simulation (subprocess-isolated) | Hourly footprint frames + particle spread uncertainty |
| **WaterQualityForecast** | Gradient-boosted regression + Open-Meteo drivers | 14-day bloom-risk forecast + confidence interval |
| **AnomalyDetector** | STL decomposition / z-score | Statistically significant departures from per-lake seasonal baseline |
| **FloodRisk** | 3-component score (precip + discharge + choke constriction) | Risk level (low/medium/high/extreme) at choke points |
| **AcidDepositionRisk** | SO₂ × NO₂ × precipitation index | 0–10 risk index (labeled: not a pH measurement) |

Every prediction carries uncertainty quantification. No predictor is shown in the UI until it has
passed a history-based skill gate against real observations.

### AI Assistant (Tier B)

- **NL situation reports** — grounded plain-language summary for any water body or district
- **NL query** — ask questions in plain English; answers cite only records in the store (read-only)
- **Anomaly explanation** — candidate hypothesis + recommended actions (advisory; human-in-the-loop)

---

## Architecture

```
┌──────────────────────────────── Argus Environmental Intelligence Platform ─────────────────────┐
│                                                                                                  │
│  OBSERVATION DOMAINS  (Domain protocol plug-ins)                                                 │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────────┐  ┌─────────────────────┐     │
│  │ D1 Marine    │  │ D2 Inland water  │  │ D3 Weather & hydro   │  │ D4 Choke points     │     │
│  │ oil (S1 SAR) │  │ quality (S2/S3)  │  │ (Open-Meteo, S5P)    │  │ (Copernicus DEM)    │     │
│  └──────┬───────┘  └────────┬─────────┘  └──────────┬───────────┘  └──────────┬──────────┘     │
│         └──────────────────┴────────────┬───────────┴──────────────────────────┘                │
│                                         ▼                                                        │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────┐   │
│  │       SPINE: tasking · ingestion · STORE (SQLite) · impact · API (FastAPI) · alerting   │   │
│  └──────────────────────────────────────┬───────────────────────────────────────────────────┘   │
│                        ┌────────────────┼──────────────────────┐                                │
│                        ▼                ▼                       ▼                               │
│  TIER A — Prediction engine      TIER B — AI assistant    Production UI                         │
│  OilTrajectory                   NL reports               React + Vite (12 pages)               │
│  WaterQualityForecast            NL query (read-only)     Leaflet map viewer                    │
│  AnomalyDetector                 Anomaly explanation      Recharts dashboards                   │
│  FloodRisk                       (all grounded + cited)   TanStack Query + Zustand              │
│  AcidDepositionRisk                                                                             │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

**Key design rules:**
- Adding a domain = implement the `Domain` protocol + register it. The spine, prediction
  interface, and AI layer are never modified for a new domain.
- All database access goes through `argus.core.store`. No module imports SQLite directly.
- OpenDrift (GPLv2) is isolated behind a subprocess boundary; it never contaminates the spine.
- Every prediction carries `uncertainty`. No prediction appears in the UI without a
  history-validated `SkillReport(passed_gate=True)`.

Full architecture: [`docs/architecture/ARCHITECTURE.md`](docs/architecture/ARCHITECTURE.md)

---

## Data Sources

All sources are **free**. Open-Meteo requires CC BY 4.0 attribution in all outputs.

| Source | What it provides | Quota / license |
|---|---|---|
| [Copernicus Data Space Ecosystem](https://dataspace.copernicus.eu/) | Sentinel-1/2/3/5P imagery | Free ≤ 1 GB/day (general-user) |
| [Open-Meteo](https://open-meteo.com/) | Forecast, ERA5 reanalysis, GloFAS discharge, air quality | Free ≤ 10k calls/day · **CC BY 4.0** |
| [Copernicus Marine (CMEMS)](https://marine.copernicus.eu/) | Ocean currents, sea-state (for oil trajectory) | Free with registration |
| [Copernicus DEM GLO-30 / HydroSHEDS](https://www.copernicus.eu/) | 30 m global DEM + hydrological network | Free / open |

---

## Repository Structure

```
argus/
├── CLAUDE.md                    Agent operating guide (read before any code)
├── BOARD.md                     Live task board — single source of truth for progress
├── ROADMAP.md                   Feature roadmap F-000 → F-056
├── FRONTEND_BLUEPRINT.md        Authoritative frontend implementation record
│
├── config/
│   ├── oil_types.yaml           Oil type registry (required; no default — ADR-0006)
│   ├── settings.yaml            Platform settings template (copy to settings.local.yaml)
│   └── aois/                    AOI definition files (per deployment)
│
├── data/
│   ├── eval/                    Eval case references (product IDs, no raw imagery)
│   └── static/                  Small static fixtures (coastline, exposure layers)
│
├── docs/
│   ├── product/PRD.md           Product requirements (v2.1)
│   ├── architecture/            ARCHITECTURE.md, DATA_MODELS.md, STACK.md
│   ├── adr/                     Architecture Decision Records (ADR-0001 → ADR-0008)
│   ├── domains/                 D1–D4 domain specifications
│   ├── prediction/              Predictor specifications (5 predictors)
│   ├── ai/ASSISTANT.md          AI assistant specification
│   ├── api/API_SPEC.md          Complete API reference (all 21 endpoints)
│   ├── features/                Phase specs: phase-0.md through phase-11.md
│   ├── standards/               TESTING.md, CODING.md, QUOTAS.md
│   ├── governance/              VALIDATORS.md, HARNESS.md
│   ├── status/                  DASHBOARD.md, program_log.md, decision_log.md
│   ├── user_guide/USER_GUIDE.md End-user guide for all 12 pages
│   ├── PROJECT_WALKTHROUGH.md   Technical + product tour for developers
│   ├── DEMO_MODE.md             Demo data, fixtures, presentation workflow
│   └── DEMO_SCRIPT.md           Polished 5–10 min live demo script
│
├── frontend/                    React + Vite dashboard (Phase 10)
│   ├── src/
│   │   ├── pages/               12 page components
│   │   ├── components/          ui/, layout/, map/, charts/, ai/, domain/
│   │   ├── api/                 typed fetch functions + Pydantic-mirrored types
│   │   ├── store/               Zustand stores (aoiStore, mapStore, uiStore)
│   │   └── lib/fixtures.ts      Gulf of Paria demo data
│   └── ...
│
├── argus/                       Python package
│   ├── api/                     FastAPI app + routers + schemas
│   ├── domains/                 D1–D4 domain implementations
│   ├── predict/                 5 predictor implementations
│   ├── ai/                      Grounded AI assistant layer
│   ├── core/                    models, store, config, errors, logging
│   ├── tasking/                 scheduler + quota guard
│   └── cli.py                   argus CLI (version / run / serve)
│
└── tests/                       56 test files · 1072 tests (offline default)
```

---

## Current Status

**Phase 10 complete. All implementation done through F-051. Phase 11 (system validation) is next.**

| Phase | Name | Status |
|---|---|---|
| 0 | Foundation & spike (D1 oil) | **DONE** |
| 1 | Detection vertical (oil) | **DONE** |
| 2 | Simulation vertical (oil) | **DONE** |
| 3 | Impact, delivery & viewer — CP-1 | **DONE** |
| 3.5 | Foundation hardening | **DONE** |
| 4 | Domain D2: inland water quality | **DONE** |
| 5 | Prediction engine: water quality | **DONE** |
| 6 | AI layer | **DONE** |
| 7 | Platform integration — CP-2 | **DONE** |
| 8 | Automation & scheduling | **DONE** |
| 9 | Domains D3 & D4 — CP-3 | **DONE** |
| 10 | Production dashboard | **DONE** |
| 11 | System validation & MVP sign-off — **CP-4 = MVP** | **TODO** (next) |

Live progress: [`BOARD.md`](BOARD.md) · Full roadmap: [`ROADMAP.md`](ROADMAP.md)

---

## Setup

> **Prerequisites:** Python 3.11+, `uv` (recommended) or pip, Node 20+, pnpm, WSL2 (Windows) or Linux/macOS.
> No cloud account required to start. CDSE, CMEMS, and Anthropic credentials are needed only
> for live data runs.

### Backend

```bash
# 1. Clone
git clone https://github.com/CXLD10/argus.git
cd argus

# 2. Create virtual environment and install
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# 3. Configure credentials (optional — not needed for tests or demo)
cp .env.example .env
# Edit .env: set ARGUS_CDSE_USER/PASSWORD for satellite downloads,
#            set ANTHROPIC_API_KEY for live AI reports,
#            set ARGUS_AI_OFFLINE=true to use templated fallback (recommended for local dev)

# 4. Run the test suite (fully offline; no credentials needed)
pytest tests/

# 5. Start the API server
argus serve                          # http://localhost:8000 (db: data/argus.db)
argus serve --port 8001              # custom port
argus serve --db-path /data/prod.db  # custom database path
```

### Frontend

```bash
cd frontend
pnpm install
pnpm dev      # http://localhost:5173 — connects to http://localhost:8000 by default
pnpm build    # production bundle → frontend/dist/
```

### CLI

```bash
argus version                                              # print version
argus run --aoi tobago --since 2024-02-01                 # offline synthetic run
argus run --aoi gulf-paria-tt --since 2024-02-01          # Gulf of Paria demo AOI
argus run --aoi tobago --since 2024-02-01 --live          # live CDSE data (requires credentials)
argus serve                                                # start FastAPI server
```

### Docker (optional)

```bash
cp .env.example .env   # fill in credentials
docker compose up      # API at http://localhost:8000
```

See `Dockerfile` and `docker-compose.yml` for the full container setup.

---

## Development Workflow

**Session start (every time):**
1. Read [`CLAUDE.md`](CLAUDE.md) (the agent operating guide)
2. Read [`docs/status/DASHBOARD.md`](docs/status/DASHBOARD.md) (current state)
3. Check [`BOARD.md`](BOARD.md) for your task
4. Read the feature spec in [`docs/features/`](docs/features/)
5. Read [`docs/standards/TESTING.md`](docs/standards/TESTING.md) and [`CODING.md`](docs/standards/CODING.md)

**Session end (every time):**
- Update `BOARD.md` with task status
- Append a HANDOFF note to `BOARD.md`
- Append to `docs/status/program_log.md`

**Architecture rules (binding):**
- All DB access through `argus.core.store` — never import `sqlite3` elsewhere (INV-6)
- OpenDrift imports only in `argus/domains/marine_oil/sim_worker.py` (GPL isolation, INV-1)
- Oil type is always specified explicitly — never hardcoded, no default (ADR-0006, INV-5)
- Every `Observation` and `Prediction` carries `evidence_class` (INV-3)
- Every `Prediction` carries `uncertainty` — no exception (INV-9)
- Unit tests are offline by default; use `--live` flag for network tests (INV-7)

**Code quality:**
```bash
ruff check .          # lint
ruff format .         # format
mypy argus/           # type check
pytest tests/         # test (offline; 1072 tests)
pytest tests/ --live  # test with live data (requires credentials)
```

---

## Documentation

| Document | Purpose |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | Agent/developer operating guide — start here |
| [`docs/DEVELOPER_ONBOARDING.md`](docs/DEVELOPER_ONBOARDING.md) | New developer setup + architecture rules |
| [`docs/user_guide/USER_GUIDE.md`](docs/user_guide/USER_GUIDE.md) | End-user guide for all 12 pages |
| [`docs/PROJECT_WALKTHROUGH.md`](docs/PROJECT_WALKTHROUGH.md) | Technical tour for evaluators + contributors |
| [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md) | Polished 5–10 min live demo script |
| [`docs/DEMO_MODE.md`](docs/DEMO_MODE.md) | Demo data, fixtures, presentation workflow |
| [`docs/api/API_SPEC.md`](docs/api/API_SPEC.md) | Complete API reference (21 endpoints) |
| [`FRONTEND_BLUEPRINT.md`](FRONTEND_BLUEPRINT.md) | Frontend implementation record |
| [`docs/product/PRD.md`](docs/product/PRD.md) | Product requirements (v2.1) |
| [`docs/architecture/ARCHITECTURE.md`](docs/architecture/ARCHITECTURE.md) | System architecture |
| [`docs/architecture/DATA_MODELS.md`](docs/architecture/DATA_MODELS.md) | Entity schemas |
| [`docs/architecture/STACK.md`](docs/architecture/STACK.md) | Technology stack |
| [`docs/adr/`](docs/adr/) | Architecture Decision Records (ADR-0001–ADR-0008) |
| [`docs/domains/`](docs/domains/) | D1–D4 domain specifications |
| [`docs/prediction/`](docs/prediction/) | Predictor specifications |
| [`docs/ai/ASSISTANT.md`](docs/ai/ASSISTANT.md) | AI assistant specification |
| [`docs/standards/TESTING.md`](docs/standards/TESTING.md) | Testing requirements |
| [`docs/standards/CODING.md`](docs/standards/CODING.md) | Coding conventions |
| [`docs/standards/QUOTAS.md`](docs/standards/QUOTAS.md) | Free-tier quota rules |
| [`docs/status/DASHBOARD.md`](docs/status/DASHBOARD.md) | Project health dashboard |

---

## License

MIT License — see `LICENSE`.

Data used by Argus carries its own terms:
- Copernicus Sentinel data: [Copernicus Sentinel Data Terms and Conditions](https://sentinel.esa.int/web/sentinel/terms-conditions)
- Open-Meteo: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) — **attribution required in all outputs**
- Copernicus Marine: [Copernicus Marine Terms of Use](https://marine.copernicus.eu/user-corner/terms-conditions)

---

## Contributing

Before submitting a pull request:

1. Check that the feature exists in [`BOARD.md`](BOARD.md) with status `TODO`.
2. Read the corresponding spec in [`docs/features/`](docs/features/).
3. Ensure your implementation satisfies all acceptance criteria in the spec.
4. Add tests per [`docs/standards/TESTING.md`](docs/standards/TESTING.md).
5. Update `BOARD.md` and add a `HANDOFF` note.

Bug reports and open-question resolutions are welcome as GitHub Issues.
