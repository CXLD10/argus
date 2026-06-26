# Domain D2 — Inland Water Quality (`inland_wq`)

- **Status:** Specced; Phase 4 implements this domain
- **Last updated:** 2026-06-27
- **Code:** `argus/domains/inland_wq/`
- **Related:** [phase-4.md](../features/phase-4.md) · [WaterQualityForecast.md](../prediction/WaterQualityForecast.md) · [AnomalyDetector.md](../prediction/AnomalyDetector.md) · [ADR-0003](../adr/ADR-0003-water-health-platform-and-domains.md)

---

## Purpose

Monitor per-water-body optical proxies (chlorophyll-a, turbidity/TSS, CDOM, surface
temperature) from Sentinel-2/3 imagery. Provide the input time series for anomaly detection
and water-quality forecasting.

---

## Responsibilities

- Enforce resolution eligibility: water bodies below minimum size → `below_resolution` (not processed)
- Search CDSE for S2/S3 scenes intersecting each `MonitorTarget(kind="water_body")`
- Acquire AOI subsets; apply atmospheric correction, cloud/shadow masking, water masking
- Compute per-pixel spectral indices; aggregate to per-water-body scalars
- Tag `evidence_class` and `calibration_state` correctly on every Observation
- Persist `Observation` records per index per water body per scene

---

## Honesty Rules (Binding — ADR-0003 D3)

| Observable | evidence_class | Reported as |
|---|---|---|
| Chlorophyll-a (NDCI proxy) | `measured` | chl-a proxy; relative trend |
| Turbidity (NDTI proxy) | `measured` | turbidity proxy; relative trend |
| CDOM (ratio proxy) | `measured` | CDOM proxy; relative trend |
| Surface temperature | `measured` (if thermal available) | proxy; calibrated if `calibration_state="calibrated"` |
| Bloom presence | `inferred` | bloom-risk indicator derived from chl-a |
| Dissolved N/P | NOT OBSERVABLE | Never computed; never stored; never reported |
| pH, metals, pathogens | NOT OBSERVABLE | Never computed; never stored; never reported |

Absolute concentrations only reported when `MonitorTarget.calibration_state="calibrated"`.
In all other cases: relative trend and anomaly only.

---

## Spectral Indices

- **NDCI** (Normalized Difference Chlorophyll Index):
  `(Band_RedEdge - Band_Red) / (Band_RedEdge + Band_Red)` — S2 B5 vs B4
- **NDTI** (Normalized Difference Turbidity Index):
  `(Band_Red - Band_Green) / (Band_Red + Band_Green)` — S2 B4 vs B3
- **CDOM proxy:** `Band_Blue / Band_Green` — S2 B2 / B3
- **Surface Temp:** S3 SLSTR thermal (if available; else omit — do not estimate)

---

## Data Models

**Inputs:** `MonitorTarget(kind="water_body", resolution_status="eligible")`, time window
**Outputs:**
- `Observation(obs_type="chlorophyll_a", evidence_class="measured", calibration_state=..., unit="ug_l_equiv")`
- `Observation(obs_type="turbidity", evidence_class="measured", unit="ntu_equiv")`
- `Observation(obs_type="cdom", evidence_class="measured", unit="m_1_equiv")`
- `Observation(obs_type="surface_temp", evidence_class="measured", unit="degC")`
- `Observation(obs_type="bloom_presence", evidence_class="inferred", confidence=0–1)`

**Error case:** `MonitorTarget.resolution_status="below_resolution"` → `BelowResolutionError` raised before any CDSE call

---

## Sources and Quota

| Source | Purpose | Quota |
|---|---|---|
| CDSE S2 L2A | 10/20m optical | ≤1 GB/day |
| CDSE S3 OLCI | 300m optical (large lakes) | ≤1 GB/day (shared) |
| CDSE Process API | Subset evalscript | Counted in bytes |

---

## Open Questions

- **OQ-C:** In-situ calibration data for absolute concentrations? Default: relative-only.
  Calibration hooks built into F-026.

---

## Future Extensions

- Sentinel-3 fluorescence for more sensitive chl-a
- Sentinel-2 L2A direct download (non-Process-API path)
- In-situ data ingestion for calibration (when reference data available)
- MODIS Aqua/Terra as complementary source for larger lakes
