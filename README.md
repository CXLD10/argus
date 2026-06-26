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
| **OilTrajectory** | OpenOil particle simulation | Hourly footprint frames + particle spread uncertainty |
| **WaterQualityForecast** | Gradient-boosted regression | 14-day bloom-risk forecast + confidence interval |
| **AnomalyDetector** | STL decomposition / z-score | Statistically significant departures from per-lake seasonal baseline |
| **FloodRisk** | Discharge threshold + precipitation | Risk level (low/medium/high/extreme) at choke points |
| **AcidDepositionRisk** | SO₂ × NO₂ × precipitation index | 0–10 risk index (labeled: not a pH measurement) |

Every prediction carries uncertainty. No predictor is shown in the UI until it has passed a
history-based skill gate against real observations.

### AI Assistant (Tier B)

- **NL situation reports** — grounded plain-language summary for any water body or district
- **NL query** — ask questions in plain English; answers cite only records in the store
- **Anomaly explanation** — candidate hypothesis + recommended actions (advisory; human-in-the-loop)
- **Alert summarization** — ranked digest of the day's alerts for operator review

---

## Architecture

```
┌──────────────────────────────── Argus Environmental Intelligence Platform ─────────────────────┐
│                                                                                                  │
│  OBSERVATION DOMAINS  (Domain protocol plug-ins)                                                 │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────────┐  ┌─────────────────────┐     │
│  │ D1 Marine    │  │ D2 Inland water  │  │ D3 Weather & hydro   │  │ D4 Choke points     │     │
│  │ oil (S1 SAR) │  │ quality (S2/S3)  │  │ (Open-Meteo, S5P)    │  │ (DEM/HydroSHEDS)    │     │
│  └──────┬───────┘  └────────┬─────────┘  └──────────┬───────────┘  └──────────┬──────────┘     │
│         └──────────────────┴────────────┬───────────┴──────────────────────────┘                │
│                                         ▼                                                        │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────┐   │
│  │       SPINE: tasking · ingestion · STORE · impact assessment · API · alerting            │   │
│  └──────────────────────────────────────┬───────────────────────────────────────────────────┘   │
│                        ┌────────────────┼──────────────────────┐                                │
│                        ▼                ▼                       ▼                               │
│  TIER A — Prediction engine      TIER B — AI assistant    API + Production UI                   │
│  OilTrajectory                   NL reports               FastAPI (HTTP)                        │
│  WaterQualityForecast            NL query                 React + Vite dashboard                │
│  AnomalyDetector                 Anomaly explain          Leaflet map viewer                    │
│  FloodRisk                       Alert summaries          Webhook / email alerts                │
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
│   ├── product/
│   │   ├── PRD.md               Product requirements (v2.1)
│   │   └── OPEN_QUESTIONS.md    Outstanding decisions blocking implementation
│   ├── architecture/
│   │   ├── ARCHITECTURE.md      System architecture (v2.1)
│   │   ├── DATA_MODELS.md       Canonical entity schemas (v2.1)
│   │   └── STACK.md             Technology stack with license + cost validation
│   ├── adr/                     Architecture Decision Records (ADR-0001 → ADR-0007)
│   ├── domains/                 D1–D4 domain specifications
│   ├── prediction/              Predictor specifications (5 predictors)
│   ├── ai/ASSISTANT.md          AI assistant specification
│   ├── features/                Phase specs: phase-0.md through phase-11.md
│   ├── standards/
│   │   ├── TESTING.md           Testing requirements and patterns
│   │   ├── CODING.md            Coding conventions
│   │   └── QUOTAS.md            Free-tier quota rules
│   ├── governance/
│   │   ├── VALIDATORS.md        22 pre-session architecture validators
│   │   └── HARNESS.md           Validation harness specification
│   ├── status/
│   │   ├── DASHBOARD.md         Project health dashboard
│   │   ├── program_log.md       Session log
│   │   ├── decision_log.md      Decision history
│   │   └── change_log.md        Structural changes
│   └── spec_graph.{md,yaml}     Human + machine-readable specification graph
│
├── scripts/
│   └── harness/                 Validation scripts (implemented in Phase 3.5)
│
└── argus/                       Python package (created in Phase 0 / F-000)
    tests/                       Test suite (created in Phase 0 / F-000)
```

---

## Current Status

**Phase: Pre-implementation.** All specifications, architecture decisions, governance
documents, and domain/predictor/AI specs are complete. No implementation code exists yet.

The first build task is **F-000 (Repo & Tooling Scaffold)**.

| Phase | Name | Status |
|---|---|---|
| 0 | Foundation & spike (D1 oil) | TODO |
| 1 | Detection vertical (oil) | TODO |
| 2 | Simulation vertical (oil) | TODO |
| 3 | Impact, delivery & viewer — CP-1 | TODO |
| 3.5 | Foundation hardening | TODO |
| 4 | Domain D2: inland water quality | TODO |
| 5 | Prediction engine: water quality | TODO |
| 6 | AI layer | TODO |
| 7 | Platform integration — CP-2 | TODO |
| 8 | Automation & scheduling | TODO |
| 9 | Domains D3 & D4 — CP-3 | TODO |
| 10 | Production dashboard | TODO |
| 11 | System validation & MVP sign-off — **CP-4 = MVP** | TODO |

Live progress: [`BOARD.md`](BOARD.md) · Full roadmap: [`ROADMAP.md`](ROADMAP.md)

---

## Setup

> **Prerequisites:** Python 3.11+, `uv` (recommended) or pip, WSL2 (Windows) or Linux/macOS.
> No cloud account required to start. CDSE, CMEMS, and Anthropic credentials are needed only
> for live data runs.

```bash
# 1. Clone
git clone <repo-url>
cd argus

# 2. Create virtual environment and install
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"     # once pyproject.toml exists (Phase 0 / F-000)

# 3. Copy and fill in your settings
cp config/settings.yaml config/settings.local.yaml
# Edit settings.local.yaml with CDSE credentials, etc.
# Never commit settings.local.yaml

# 4. Run the test suite (offline; no credentials needed)
pytest tests/
```

> The Python package and `pyproject.toml` are created in **F-000**. Until then, the
> repository contains specification and governance documents only.

---

## Development Workflow

This project is **spec-driven**: every feature is fully specified before implementation.
Read the specifications before writing any code.

**Session start (every time):**
1. Read [`CLAUDE.md`](CLAUDE.md) (the agent operating guide)
2. Read [`docs/status/DASHBOARD.md`](docs/status/DASHBOARD.md) (current state)
3. Check [`BOARD.md`](BOARD.md) for your task
4. Read the feature spec in [`docs/features/`](docs/features/)
5. Read [`docs/standards/TESTING.md`](docs/standards/TESTING.md) and [`CODING.md`](docs/standards/CODING.md)

**Session end (every time):**
- Update `BOARD.md` with task status
- Append a HANDOFF note to `BOARD.md` (see format in file)
- Append to `docs/status/program_log.md`

**Architecture rules (binding):**
- All DB access through `argus.core.store` — never import `sqlite3` elsewhere
- OpenDrift imports only in `argus/domains/marine_oil/sim_worker.py` (GPL isolation)
- Oil type is always specified explicitly — never hardcoded, no default (ADR-0006)
- Every `Observation` and `Prediction` carries `evidence_class`
- Unit tests are offline by default; use `--live` flag for network tests

**Code quality:**
```bash
ruff check .          # lint
ruff format .         # format
mypy argus/           # type check
pytest tests/         # test (offline)
pytest tests/ --live  # test with live data (requires credentials)
```

---

## Documentation

| Document | Purpose |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | Agent/developer operating guide — start here |
| [`docs/product/PRD.md`](docs/product/PRD.md) | Product requirements (v2.1) |
| [`docs/architecture/ARCHITECTURE.md`](docs/architecture/ARCHITECTURE.md) | System architecture |
| [`docs/architecture/DATA_MODELS.md`](docs/architecture/DATA_MODELS.md) | Entity schemas |
| [`docs/architecture/STACK.md`](docs/architecture/STACK.md) | Technology stack |
| [`docs/adr/`](docs/adr/) | Architecture Decision Records |
| [`docs/domains/`](docs/domains/) | D1–D4 domain specifications |
| [`docs/prediction/`](docs/prediction/) | Predictor specifications |
| [`docs/ai/ASSISTANT.md`](docs/ai/ASSISTANT.md) | AI assistant specification |
| [`docs/standards/TESTING.md`](docs/standards/TESTING.md) | Testing requirements |
| [`docs/standards/CODING.md`](docs/standards/CODING.md) | Coding conventions |
| [`docs/standards/QUOTAS.md`](docs/standards/QUOTAS.md) | Free-tier quota rules |
| [`docs/governance/VALIDATORS.md`](docs/governance/VALIDATORS.md) | 22 architecture validators |
| [`docs/status/DASHBOARD.md`](docs/status/DASHBOARD.md) | Project health dashboard |
| [`docs/product/OPEN_QUESTIONS.md`](docs/product/OPEN_QUESTIONS.md) | Outstanding decisions |

---

## License

MIT License — see `LICENSE` file (to be created in F-000).

Data used by Argus carries its own terms:
- Copernicus Sentinel data: [Copernicus Sentinel Data Terms and Conditions](https://sentinel.esa.int/web/sentinel/terms-conditions)
- Open-Meteo: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) — **attribution required in all outputs**
- Copernicus Marine: [Copernicus Marine Terms of Use](https://marine.copernicus.eu/user-corner/terms-conditions)

---

## Contributing

This project is spec-driven. Before submitting a pull request:

1. Check that the feature exists in [`BOARD.md`](BOARD.md) with status `TODO`.
2. Read the corresponding spec in [`docs/features/`](docs/features/).
3. Ensure your implementation satisfies all acceptance criteria in the spec.
4. Add tests per [`docs/standards/TESTING.md`](docs/standards/TESTING.md).
5. Update `BOARD.md` and add a `HANDOFF` note.

Bug reports and open-question resolutions are welcome as GitHub Issues.
