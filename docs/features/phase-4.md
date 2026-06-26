# Phase 4 — Domain D2: Inland Water Quality

- **Status:** Specced; waiting for Phase 3.5
- **Priority:** P0
- **Last updated:** 2026-06-27
- **Features:** F-024–F-026
- **Depends on:** Phase 3.5 complete; OQ-A resolved ✓; OQ-C resolved (default: relative-only)
- **Related:** [D2-inland-wq.md](../domains/D2-inland-wq.md) · [DATA_MODELS.md](../architecture/DATA_MODELS.md)
- **Checkpoint:** Starts CP-2 (water quality + prediction + AI)

**Goal:** Add the D2 inland water quality domain as the first plug-in on the generalized
spine. Prove that adding a domain = implement `Domain` + register + extend ingest, with no
changes to the spine.

---

## F-024 — Water-Body Model + Monitor Targets + Resolution Gate

**Why:** D2 needs per-water-body targets with resolution eligibility and calibration state.

**Depends on:** F-023

**Owns / creates:**
- `argus/aoi/loader.py` (extend: load water_body targets from config)
- `config/water_bodies/reference_lake.geojson`
- `config/water_bodies/reference_lake_meta.yaml` (calibration state, trophic class, etc.)
- `argus/core/models.py` (verify MonitorTarget matches DATA_MODELS.md; add helpers)
- `tests/test_water_body_loader.py`

**Resolution gate (binding — ADR-0003 D3):**
```python
MIN_WATER_BODY_AREA_HA = 1.0  # default (10×10 Sentinel-2 pixels at 10m)
if water_body_area_ha < MIN_WATER_BODY_AREA_HA:
    target.resolution_status = "below_resolution"
    # never processed; never silently estimated
```

**Acceptance criteria:**
- reference_lake target loads with `resolution_status="eligible"` (it must be > 1 ha)
- A synthetic <0.1 ha polygon loads with `resolution_status="below_resolution"`
- `below_resolution` targets raise `BelowResolutionError` if passed to `Domain.search()`

---

## F-025 — Sentinel-2/3 Optical Ingestion

**Why:** D2 needs Sentinel-2 (10m) and Sentinel-3 OLCI (300m) imagery — different bands
and different Process API evalscripts from Sentinel-1.

**Depends on:** F-024

**Owns / creates:**
- `argus/ingest/catalogue.py` (extend: `search_s2()`, `search_s3()`)
- `argus/ingest/process_api.py` (extend: S2 evalscript, S3 evalscript)
- `argus/preprocess/optical.py` (atmospheric correction stub; water + cloud masking)
- `tests/test_s2_catalogue.py`, `tests/test_s3_catalogue.py`
- `tests/fixtures/cdse_s2_search_reference_lake.json`
- `tests/fixtures/s2_water_body_100x100.npy` (synthetic optical scene)

**S2 Bands:** B2 (Blue), B3 (Green), B4 (Red), B5 (Red Edge), B8A (NIR), B11 (SWIR)
**S3 Bands:** Oa03–Oa12 (visible to NIR for OLCI water products)

**Acceptance criteria:**
- Mocked CDSE S2 search → `SourceRef` list with S2-specific fields
- Synthetic S2 optical scene → water-masked subset (land = nodata)
- Quota tracking: S2 subset bytes counted in `Scene.bytes_or_calls`

---

## F-026 — `inland_wq` Analyzer: Optical Index Computation + Observation Persistence

**Why:** This is the D2 domain's core analysis step — computing per-water-body optical
proxies and persisting them as Observations with correct honesty tags.

**Depends on:** F-025

**Owns / creates:**
- `argus/domains/inland_wq/__init__.py`
- `argus/domains/inland_wq/analyzer.py` (implements `Domain` protocol)
- `argus/domains/inland_wq/indices.py` (spectral index algorithms)
- `tests/test_inland_wq_analyzer.py`
- `tests/test_optical_indices.py`

**Spectral indices:**
- Chlorophyll-a proxy: NDCI (Normalized Difference Chlorophyll Index) — (Red Edge - Red) / (Red Edge + Red)
- Turbidity proxy: NDTI (Normalized Difference Turbidity Index) — (Red - Green) / (Red + Green)
- CDOM proxy: ratio-based (Blue / Green)
- Surface temperature: SST if thermal band available (S3 only); else omit

**Honesty rules (binding):**
- All index observations: `evidence_class="measured"` (optical proxy — physical measurement)
- `calibration_state` copied from `MonitorTarget.calibration_state` into each Observation
- Bloom presence (chl-a above threshold): `evidence_class="inferred"`, `obs_type="bloom_presence"`
- DO NOT report dissolved nutrients, metals, pH — these have no obs_type and are never computed

**Acceptance criteria:**
- Synthetic S2 scene (with known spectral values) → correct NDCI/NDTI values within tolerance
- All Observations have `evidence_class="measured"` (except bloom_presence = "inferred")
- `calibration_state` matches target's state
- A water body with `resolution_status="below_resolution"` → `BelowResolutionError` before any CDSE call

## Phase 4 Definition of Done

- [ ] F-024–F-026 acceptance criteria met
- [ ] D2 domain registered in the domain registry alongside D1
- [ ] `argus run --domain inland_wq --target reference_lake --since ...` works in offline mode
- [ ] All Observations carry correct `evidence_class` and `calibration_state`
- [ ] No spine code modified (INV-2 verified)
