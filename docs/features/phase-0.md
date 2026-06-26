# Phase 0 — Foundation & Spike (ready-to-build tasks)

- **Status:** Ready for execution
- **Priority:** P0 (MVP critical)
- **Last updated:** 2026-06-27 (v2.0 entity names corrected from v1.0)
- **Owner:** First coding agent
- **Related:** [ROADMAP.md](../../ROADMAP.md) · [ARCHITECTURE.md](../architecture/ARCHITECTURE.md) · [DATA_MODELS.md](../architecture/DATA_MODELS.md) · [TESTING.md](../standards/TESTING.md) · [BOARD.md](../../BOARD.md) · [CLAUDE.md](../../CLAUDE.md)
- **Checkpoint:** CP-1 begins here (oil pipeline)

**Goal:** Thread one curated historical spill from "AOI defined" to "detection exported as a
map artifact." Everything that can be stubbed is stubbed. Phase 0 closes when a single
`EvalCase` produces a visible detection GeoJSON + PNG.

> **Package root:** `argus/` · **Tests:** `tests/` · **Artifacts:** `.argus/` (gitignored)
> **Eval references:** `data/eval/`

---

## v1.0 → v2.0 Entity Name Corrections Applied in This Spec

**IMPORTANT:** This file was originally written for v1.0. All v1.0 names below have been
corrected. If you see `DetectionRun`, `Detection` (standalone), `Detector`, or `hazard_types`
anywhere in code: those are v1.0 names. Use the v2.0 names listed here.

| v1.0 (WRONG) | v2.0 (CORRECT) |
|---|---|
| `DetectionRun` | `AnalysisRun` |
| `Detection` (standalone entity) | `Observation(obs_type="oil_slick")` |
| `Detector` protocol | `Domain` protocol |
| `argus/detect/base.py` | `argus/domains/base.py` |
| `argus/detect/oil_darkspot.py` | `argus/domains/marine_oil/detector.py` |
| `AOI.hazard_types` | `AOI.domains` |

---

## F-000 — Repo & Tooling Scaffold

**Why:** Every later task needs a working package, test runner, and lint gate.

**Owns / creates:**
- `pyproject.toml`
- `argus/__init__.py`, `argus/core/__init__.py`
- `argus/cli.py` (Typer/Click entry point; `argus version`)
- `tests/__init__.py`, `tests/test_smoke.py`
- `.gitignore` (`.argus/`, `data/`, `*.nc`, `__pycache__`, `*.db`)
- `.github/workflows/ci.yml`
- `Makefile` (targets: `install`, `lint`, `test`, `run`)
- `scripts/harness/` (placeholder directory with README)

**Implementation notes:**
- `uv` preferred. Python 3.11+.
- Lint: `ruff`. Type check: `mypy` (lenient). Format: `ruff format`.
- `argus version` prints package version.

**Acceptance criteria:**
- `argus version` exits 0 and prints a version string
- `make test` passes (test_smoke.py green)
- `make lint` passes clean
- `.gitignore` includes `.argus/`, `*.db`, `data/static/`, `data/eval/` large files

**Tests:** `tests/test_smoke.py` — imports package, asserts `argus version` exits 0.

---

## F-001 — Configuration System + AOI Model & Loader

**Why:** AOIs and config are inputs to every stage.

**Depends on:** F-000

**Owns / creates:**
- `argus/core/config.py`
- `argus/core/models.py` (begin with `AOI`, `MonitorTarget`)
- `argus/aoi/__init__.py`, `argus/aoi/loader.py`
- `config/aois/tobago.geojson`
- `config/settings.yaml` (quota limits, artifact dir, default horizon)
- `tests/test_config.py`, `tests/test_aoi_loader.py`

**Data model (v2.0):**
`AOI`: id, name, geometry, `domains` (not hazard_types), params, active, created_at
`MonitorTarget`: id, aoi_id, kind (water_body|region), name, geometry, domains,
resolution_status (eligible|below_resolution), calibration_state, attrs

**Implementation notes:**
- `AOI.domains: list[str]` e.g. `["marine_oil"]`
- Validate AOI polygon is valid and within size cap; reject with clear error
- CDSE credentials from env only — never commit; log missing creds, not the values

**Acceptance criteria:**
- Loading `tobago.geojson` yields valid `AOI` with correct bbox and `domains=["marine_oil"]`
- Missing CDSE credentials → typed `ConfigError` with remediation text (no secrets in output)
- Oversized polygon → clear rejection error

**Tests:** `test_config.py`, `test_aoi_loader.py`

---

## F-002 — CDSE Catalogue Client (Auth + STAC/OData Search)

**Why:** We must find the right Sentinel-1 products before fetching pixels.

**Depends on:** F-001

**Owns / creates:**
- `argus/ingest/__init__.py`
- `argus/ingest/cdse_auth.py` (OAuth token acquisition + refresh)
- `argus/ingest/catalogue.py` (`search_s1_grd(aoi, t0, t1) -> list[SourceRef]`)
- `argus/core/models.py` (add `SourceRef`)
- `tests/test_catalogue.py` (mocked HTTP only — no live network in unit tests)
- `tests/fixtures/cdse_s1_search_tobago.json` (recorded response)

**Implementation notes:**
- Use `sentinelhub-py` and/or `pystac-client`/`requests` against CDSE endpoints
- Filters: Sentinel-1 GRD, intersects AOI, date range, IW mode
- Return: product id, footprint, sensing time, polarizations
- Token handling in `cdse_auth.py` only; never log tokens

**Acceptance criteria:**
- Mocked CDSE response → parsed `SourceRef`s sorted by sensing time
- Auth failure → typed `CdseAuthError` with remediation text
- Empty catalogue result → empty list (not exception)

**Tests:** `test_catalogue.py` — parse fixture; auth failure path; empty result path.
Separate opt-in live test in `tests/integration/`.

---

## F-003 — Scene Acquisition + Persistence

**Why:** Turn a `SourceRef` into local pixels and a durable `Scene` row.

**Depends on:** F-002

**Owns / creates:**
- `argus/ingest/acquire.py`
- `argus/ingest/process_api.py`
- `argus/core/store.py` (SQLite bootstrap + `Scene` CRUD)
- `argus/core/models.py` (add `Scene`)
- `tests/test_acquire.py`, `tests/test_store_scene.py`

**Implementation notes:**
- Default: Process API evalscript for AOI bbox → calibrated σ⁰ GeoTIFF subset
- Fallback: OData/S3 full download (behind a `--full-download` flag; large)
- Record `Scene.bytes_or_calls` (from HTTP Content-Length header)
- Refuse if `bytes_or_calls + daily_total > CDSE_DAILY_LIMIT_BYTES`
- Store creates SQLite DB at `config.artifact_dir / "argus.db"`

**Acceptance criteria:**
- Mocked Process API → raster artifact + `Scene(ingest_status="ready", bytes_or_calls > 0)`
- SQLite store: `Scene` write → read by id → identical
- Oversized AOI refused with clear error

**Tests:** `test_acquire.py`, `test_store_scene.py`

---

## F-004 — SAR Preprocessing to Masked σ⁰ dB Raster

**Why:** Detection needs a clean, calibrated, land-masked raster.

**Depends on:** F-003

**Owns / creates:**
- `argus/preprocess/__init__.py`
- `argus/preprocess/sar.py` (`preprocess(scene) -> PreprocessedScene`)
- `argus/preprocess/landmask.py` (apply coastline/DEM-derived land mask)
- `data/static/coastline.geojson` (small clipped coastline for anchor AOI)
- `tests/test_preprocess.py`, `tests/test_landmask.py`
- `tests/fixtures/synthetic_sar_100x100.npy`

**Implementation notes:**
- If Process API returned calibrated dB: speckle filter + normalization + masking
- Speckle: Lee/median filter via `scipy`/`scikit-image`
- Land mask: rasterize coastline polygon; set land pixels to nodata
- Output `PreprocessedScene` with masked-dB raster ref + transform + CRS

**Acceptance criteria:**
- Synthetic raster fixture → finite dB over water, nodata over land
- Deterministic: same input → identical output raster (hash check)

**Tests:** `test_preprocess.py`, `test_landmask.py`

---

## F-005 — Domain Protocol + Naive Dark-Spot Detector + Observation Persistence

**Why:** Prove the detection→record path; fix the stable `Domain` interface; intentionally
naive (Phase 1 makes it real).

**Depends on:** F-004

**v2.0 REQUIRED entities (do not use v1.0 names):**
- Create `argus/domains/base.py` with `Domain` protocol (NOT `argus/detect/base.py` with `Detector`)
- Create `AnalysisRun` (NOT `DetectionRun`)
- Create `Observation(obs_type="oil_slick")` (NOT a standalone `Detection` class)
- Oil detection = `Observation` with `obs_type="oil_slick"`, `evidence_class="measured"`

**Owns / creates:**
- `argus/domains/__init__.py`
- `argus/domains/base.py` (`Domain` protocol — stable interface)
- `argus/domains/marine_oil/__init__.py`
- `argus/domains/marine_oil/detector.py` (`OilDomainV0`: global threshold + morphology + polygonize)
- `argus/core/store.py` (add `AnalysisRun` + `Observation` CRUD)
- `argus/core/models.py` (add `AnalysisRun`, `Observation`)
- `tests/test_oil_detector.py`, `tests/test_store_observation.py`

**Domain protocol (v2.0):**
```python
class Domain(Protocol):
    domain_id: str
    def search(self, target: MonitorTarget, t0, t1) -> list[SourceRef]: ...
    def acquire(self, ref: SourceRef) -> Acquisition: ...
    def analyze(self, acq: Acquisition) -> list[Observation]: ...
```

**Honesty:** `Observation` must have `evidence_class="measured"` for SAR oil detection.
Set `confidence` as a simple function of dark-area contrast. Mark as `status="candidate"`.

**Acceptance criteria:**
- Synthetic raster with planted dark blob → ≥1 `Observation(obs_type="oil_slick", evidence_class="measured")`
- Detected polygon covers the planted blob; area_km2 in expected range
- `AnalysisRun` + `Observation` persist and round-trip from SQLite
- Uniform raster (no dark blob) → zero Observations

**Tests:** `test_oil_detector.py`, `test_store_observation.py`

---

## F-006 — Static Product Export + EvalCase + CLI Run

**Why:** Make the spike visible; seed the evaluation dataset.

**Depends on:** F-005

**Owns / creates:**
- `argus/export/__init__.py`, `argus/export/products.py`
- `argus/cli.py` (add `argus run --aoi <name> --since <date> [--live]`)
- `data/eval/tobago_2024.json` (anchor `EvalCase` with oil_type field per ADR-0006)
- `tests/test_export.py`, `tests/test_phase0_e2e.py`

**EvalCase (tobago_2024.json) must include:**
```json
{
  "id": "tobago_2024",
  "domain": "marine_oil",
  "oil_type": "crude_medium",
  "event_name": "Tobago 2024 spill",
  "refs": {"cdse_product_id": "...", "bbox": [...], "sensing_date": "..."},
  "event_time": "2024-02-07T...",
  "truth_geometry": {...},
  "provenance": "..."
}
```

**Implementation notes:**
- GeoJSON: FeatureCollection of Observation polygons with properties
- PNG: masked dB raster with observation polygons overlaid
- `argus run` threads F-001→F-006; network behind `--live` flag

**Acceptance criteria:**
- `argus run --aoi tobago --since 2024-02-07` (offline fixture mode) writes GeoJSON + PNG
- `test_phase0_e2e.py` runs offline on fixtures; both artifacts exist; GeoJSON has ≥1 feature

**Tests:** `test_export.py`, `test_phase0_e2e.py`

---

## Phase 0 Definition of Done

- [ ] F-000 through F-006 acceptance criteria all met
- [ ] `tests/test_phase0_e2e.py` is green **offline** (no live CDSE)
- [ ] One opt-in `--live` path run manually; result recorded in BOARD.md HANDOFF
- [ ] `BOARD.md` reflects every task status with HANDOFF note
- [ ] `Domain` protocol in `argus/domains/base.py` is stable (F-007 can swap internals without changing callers)
- [ ] `AnalysisRun` + `Observation` in store match DATA_MODELS.md exactly
- [ ] `evidence_class="measured"` set on all oil detections
- [ ] `EvalCase` tobago_2024.json includes `oil_type` field (ADR-0006)
