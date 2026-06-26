# ADR-0002 — Data and Simulation Stack

- **Status:** Accepted (supplemented by ADR-0003, ADR-0004; core decisions retained)
- **Date:** 2026-06-01 (estimated; original date unknown)
- **Deciders:** Josh
- **Note:** RECONSTRUCTED STUB. Original document unavailable. Decisions reconstructed from
  references: ADR-0002 D5 (store accessor) cited in ARCHITECTURE.md; OpenDrift GPLv2 isolation
  cited in README, PRD, ARCHITECTURE, ADR-0003. Treat as informational.
- **Related:** [ADR-0001](ADR-0001-vertical-and-pipeline.md) · [ADR-0003](ADR-0003-water-health-platform-and-domains.md) · [ADR-0004](ADR-0004-prediction-and-ai-layer.md)

---

## Context

Choosing the data access stack, local storage strategy, and simulation toolchain for a
zero-budget, WSL-native platform. Three constraints drove the decisions:

1. Zero recurring cost
2. All computation on a laptop CPU
3. Copyleft licensing must not contaminate the core codebase

---

## Decisions

### D1 — OpenDrift / OpenOil for Oil Trajectory Simulation

Use `opendrift` (`OpenOil` model) for oil drift simulation. It is open-source, well-validated
against historical spills, and free. The critical constraint: OpenDrift is **GPLv2**. Any
binary that links against it inherits the GPL.

**Implication (D2 below):** Isolate OpenDrift behind a process boundary.

### D2 — Subprocess Isolation for GPL Components (BINDING)

OpenDrift and any other copyleft-licensed tool run as **isolated subprocesses** — never
imported into the main `argus` Python process. The main process communicates with them via
stdin/stdout, files, or local sockets. This prevents GPL contamination.

**Applies to:** OpenDrift (GPLv2). Must also apply to any hydrology tool found to have a
copyleft license (pysheds/richdem/WhiteboxTools — confirm before F-040).

### D3 — CDSE (Copernicus Data Space Ecosystem) for EO Data

Sentinel-1, -2, -3, -5P accessed via CDSE: STAC/OData catalogue + Process API (subset
download). General-user quota (free). Authentication via OAuth token.

### D4 — Open-Meteo for Weather, Flood, and Air Quality

Open-Meteo HTTP API (forecast, ERA5 history, GloFAS Flood, Air Quality SO₂/NO₂). Free
non-commercial tier (≤10,000 calls/day). **Attribution required: CC BY 4.0.** All platform
outputs derived from Open-Meteo data must carry attribution.

### D5 — Single Store Accessor (BINDING — widely cited)

All database access goes through `argus.core.store`. No stage, domain, predictor, or AI
module imports SQLite directly or uses raw cursor calls. This ensures:
- Schema migration (SQLite → PostGIS later) is a swap behind the accessor
- Testability (store can be replaced with a test double)
- No store logic leaking into domain/predictor code

### D6 — SQLite + Filesystem for MVP Storage

SQLite for metadata (entities, records, statuses). Local filesystem for artifact blobs
(rasters, parquet files, reports). This is free, local, and requires no managed service.
Geometries stored as GeoJSON text in SQLite (EPSG:4326). Migration path to PostGIS noted
but deferred post-MVP.

### D7 — Raster and GIS Processing Stack

`rasterio`, `numpy`, `scipy`, `scikit-image` for raster operations.
`shapely`, `geopandas`, `pyproj` for vector/GIS operations.
All open-source, CPU-only, free.

### D8 — ML: scikit-learn + Gradient Boosting

CPU-trainable ML only (scikit-learn, gradient boosting via `lightgbm`/`xgboost`/sklearn).
No deep learning, no GPU required. Model artifacts stored locally. This satisfies the
zero-budget + laptop constraint.

---

## Consequences

- Every copyleft tool must be identified and isolated before implementation begins
- The store accessor pattern is an architectural invariant; violation is caught by VAL-008
- Open-Meteo CC BY 4.0 attribution must appear in any output/product using its data

## Cost Validation

All tools listed are open-source or free-tier services. No recurring cost. CDSE and
Open-Meteo are free within documented quotas (tracked per NFR-5).

---

*[STUB] If the original ADR-0002 is recovered, this document should be replaced.*
