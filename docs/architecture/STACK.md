# Argus — Technology Stack

- **Status:** Active
- **Last updated:** 2026-06-27
- **Owner:** Architecture Governance
- **Related:** [ADR-0002](../adr/ADR-0002-data-and-simulation-stack.md) · [QUOTAS.md](../standards/QUOTAS.md) · PRD NFR-1

**Zero-cost constraint:** Every entry in this table must be free. Any addition that incurs
recurring cost requires explicit approval and PRD amendment.

---

## Core Language + Tooling

| Concern | Choice | License | Cost |
|---|---|---|---|
| Language | Python 3.11+ | PSF | Free |
| Package manager | `uv` (preferred) / Poetry | MIT / MIT | Free |
| Formatter | `ruff format` | MIT | Free |
| Linter | `ruff check` | MIT | Free |
| Type checker | `mypy` | MIT | Free |
| Test runner | `pytest` | MIT | Free |
| CLI framework | `typer` / `click` | MIT | Free |
| Config | `pydantic-settings` | MIT | Free |

---

## Earth Observation Data Access

| Concern | Choice | License | Cost | Attribution |
|---|---|---|---|---|
| S1/S2/S3/S5P search | `pystac-client`, `sentinelhub-py`, CDSE OData | MIT / Apache | Free (general-user quota ≤1GB/day) | Copernicus Programme |
| S1/S2 subset download | CDSE Process API (eval script) | — | Free within quota | Copernicus Programme |
| Weather/flood/air quality | Open-Meteo HTTP API | non-commercial | Free ≤10k calls/day | **CC BY 4.0 required** |
| Metocean currents | CMEMS (Copernicus Marine) | non-commercial | Free with registration | Copernicus Marine |
| DEM | Copernicus GLO-30 / HydroSHEDS | open | Free | Copernicus Programme |

---

## Raster + GIS Processing

| Concern | Choice | License | Cost |
|---|---|---|---|
| Raster I/O | `rasterio` | BSD | Free |
| Numerical | `numpy`, `scipy` | BSD | Free |
| Image processing | `scikit-image` | BSD | Free |
| Vector/GIS | `shapely`, `geopandas`, `pyproj` | BSD/MIT | Free |
| DEM processing | `pysheds` (MIT) or `richdem` (Apache) | MIT/Apache | Free |

---

## Machine Learning

| Concern | Choice | License | Cost |
|---|---|---|---|
| Classical ML | `scikit-learn` | BSD | Free |
| Gradient boosting | `lightgbm` or `xgboost` | MIT/Apache | Free |
| Time series | `statsmodels` | BSD | Free |
| STL decomposition | `statsmodels.tsa.seasonal` | BSD | Free |

**No deep learning. No GPU required. All CPU-trainable.**

---

## Simulation (GPL-isolated)

| Concern | Choice | License | Cost | Isolation |
|---|---|---|---|---|
| Oil drift simulation | `opendrift` (OpenOil) | **GPLv2** | Free | **Subprocess boundary required** (ADR-0002 D2) |

---

## Storage

| Concern | Choice | License | Cost |
|---|---|---|---|
| Metadata store | SQLite (via Python stdlib) | Public Domain | Free |
| Store accessor | `argus.core.store` (custom) | — | Free |
| Time series / rasters | Local filesystem (parquet, GeoTIFF, netCDF) | — | Free |
| Future (post-MVP) | PostgreSQL + PostGIS | PostgreSQL License | Free (self-hosted) |

---

## API + Web

| Concern | Choice | License | Cost |
|---|---|---|---|
| HTTP API | `FastAPI` | MIT | Free |
| ASGI server | `uvicorn` | BSD | Free |
| Map viewer (Phase 0–9) | Leaflet / MapLibre GL JS | BSD / MIT | Free |
| UI framework (Phase 10) | React + Vite + Tailwind CSS | MIT | Free |
| Charts (Phase 10) | Recharts or Chart.js | MIT | Free |
| PDF export | `reportlab` or `weasyprint` | BSD/LGPL | Free |

---

## AI Layer

| Concern | Choice | License | Cost |
|---|---|---|---|
| LLM | Anthropic API (Claude) | Commercial | **Free/educational credits only** (OQ-D pending) |
| Fallback | Templated reports (`argus/ai/fallback.py`) | — | Zero cost |

**If Anthropic API has no free tier for the chosen model tier:** investigate local open-source
LLM (Mistral, Llama via Ollama) as zero-cost alternative. Grounding quality may differ — document if adopted.

---

## Alerting

| Concern | Choice | License | Cost |
|---|---|---|---|
| Webhook delivery | `httpx` | BSD | Free |
| Email delivery | `smtplib` (stdlib) | — | Free (requires SMTP server; use free provider) |

---

## Production Deployment (Post-MVP)

See [ADR-0008](../adr/ADR-0008-deployment-strategy.md) for full rationale and cost analysis.

| Concern | Choice | Cost model |
|---|---|---|
| Frontend hosting | Vercel (Hobby) | Free; zero ops; automatic HTTPS |
| API hosting | GCP Cloud Run | Scales to zero; ~$0 at low traffic; billed per-request |
| Artifact store | GCP Cloud Storage | 5 GB free; ~$0.02/GB/month beyond |
| Database (dev) | SQLite (local) | Free |
| Database (prod, TBD) | Cloud SQL (PostgreSQL) or Supabase | ~$0–15/month; decision deferred to Phase 11 |
| Secrets | GCP Secret Manager | Free tier (≤6 secret versions, ≤10k access ops/month) |
| CI/CD | GitHub Actions | Free for public repositories |
| Container registry | GCP Artifact Registry | Negligible; lifecycle policy applied |

**Credit conservation:** GCP $300 credits must last many months. Rules: no always-on VMs,
Cloud Run min-instances=0, GCS lifecycle policies, budget alerts at $20 and $50/month.

---

## Cost Validation Summary

**Development (local/WSL):** Zero recurring cost. All data sources, libraries, and tooling are
free or open-source.

**Production (post-MVP):** Expected ~$0/month at MVP scale (Cloud Run scales to zero; GCS
≤5 GB free tier; Vercel Hobby free). Worst case ~$5–10/month at active use. Well within GCP
credit lifespan. The only open cost is the Anthropic API for the AI layer — controlled by
OQ-D resolution and `ARGUS_AI_OFFLINE` fallback mode.
