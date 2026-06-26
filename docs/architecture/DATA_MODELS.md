# Argus — Data Models

- **Status:** v2.1 (authoritative; supersedes root `DATA_MODELS.md` v2.0)
- **Last updated:** 2026-06-27
- **Related:** [ARCHITECTURE.md](ARCHITECTURE.md) · [PRD.md](../product/PRD.md)
  · [ADR-0003](../adr/ADR-0003-water-health-platform-and-domains.md)
  · [ADR-0004](../adr/ADR-0004-prediction-and-ai-layer.md)
- **Change log v2.1:** `EvalCase` gains `oil_type` field (ADR-0006); section 0 adds v1.0→v2.0 naming table;
  root file is now a stub pointing here.

---

## 0. Entity Name Migration (v1.0 → v2.0)

Use v2.0 names everywhere. v1.0 names are dead — they do not exist in code or specs.

| v1.0 (DEAD) | v2.0 (canonical) |
|---|---|
| `DetectionRun` | `AnalysisRun` |
| `Detection` (standalone) | `Observation(obs_type="oil_slick")` |
| `Detector` (protocol) | `Domain` (protocol) |
| `AOI.hazard_types` | `AOI.domains` |
| `hazard` | `domain` |

---

## Conventions

- IDs are ULIDs/UUIDs; timestamps are UTC ISO-8601; `geometry` is GeoJSON (EPSG:4326).
- `*_ref` fields are filesystem paths (MVP) / object-store URIs (later) — never inline blobs.
- JSON columns hold open, additive structures.
- **Honesty tagging is mandatory (INV-3/NFR-8):** every value-bearing record carries
  `evidence_class ∈ {measured, modeled, inferred}`. Nothing not-observable is stored as `measured`.
- All DB access goes through `argus.core.store`. No raw `sqlite3` imports elsewhere (INV-6).

---

## Entity-Relationship Overview

```
AOI 1─* MonitorTarget(WaterBody|Region) 1─* Scene/Acquisition 1─* AnalysisRun 1─* Observation
                      │                                                               │
                      │                                      Observation(obs_type="oil_slick") = oil detection
                      │
                      *─ WeatherSeries (D3)        ChokePoint (D4) ─* (on MonitorTarget)
                      │
 Observation 1─* Prediction ──{Forecast | RiskAssessment | AnomalyResult | ForecastFrame}─* ImpactAssessment *─1 ExposureLayer
                      │
 Alert   AIReport / AIQueryLog (grounded; reference records by id)   EvalCase (scoring)
```

---

## AOI — Area of Interest

| Field | Type | Notes |
|---|---|---|
| `id` | str (PK) | |
| `name` | str | unique label |
| `geometry` | geojson | polygon, EPSG:4326 |
| `domains` | json[str] | enabled domains, e.g. `["marine_oil","inland_wq"]` |
| `params` | json | per-domain overrides |
| `active` | bool | scheduler monitors it |
| `created_at` | ts | |

---

## MonitorTarget — The Thing Being Watched

Generalizes "what we observe." A target is a **WaterBody** (lake/pond/reservoir/coastal cell)
or a **Region** (for area hazards like floods).

| Field | Type | Notes |
|---|---|---|
| `id` | str (PK) | |
| `aoi_id` | str (FK→AOI) | |
| `kind` | enum | `water_body` / `region` |
| `name` | str | |
| `geometry` | geojson | polygon |
| `domains` | json[str] | domains applicable to this target |
| `resolution_status` | enum | `eligible` / `below_resolution` (Sentinel-2 min-size gate) |
| `calibration_state` | enum | `relative_only` / `calibrated` (optical proxies; ADR-0003 D3) |
| `attrs` | json | e.g. trophic class, nearby intakes, upstream land use, acid_sensitivity |

---

## Scene / Acquisition — Acquired Source Data Over a Target

| Field | Type | Notes |
|---|---|---|
| `id` | str (PK) | |
| `target_id` | str (FK→MonitorTarget) | |
| `domain` | str | `marine_oil` / `inland_wq` / `weather_hydro` / `hydro_chokepoints` |
| `source` | str | `S1`/`S2`/`S3`/`S5P`/`open_meteo`/`dem` |
| `product_id` | str? | CDSE product id / API request signature (reproducibility) |
| `acquired_at` | ts | sensing/valid time |
| `footprint` | geojson | |
| `ingest_status` | enum | `pending`/`fetching`/`ready`/`failed`/`quota_blocked` |
| `bytes_or_calls` | int | quota/call accounting (NFR-5) |
| `raw_ref` | str? | path to acquired raster/series |

---

## AnalysisRun — One Execution of a Domain Analyzer on an Acquisition

| Field | Type | Notes |
|---|---|---|
| `id` | str (PK) | |
| `scene_id` | str (FK→Scene) | |
| `domain` | str | |
| `analyzer` | str | e.g. `oil_darkspot.v1`, `inland_wq.v1` |
| `params` | json | |
| `status` | enum | `running`/`succeeded`/`failed` |
| `artifact_ref` | str? | preprocessed/intermediate raster |
| `started_at`/`finished_at` | ts | |
| `log_ref` | str? | structured log |

---

## Observation — A Characterized Result

> `Detection` = `Observation(obs_type="oil_slick")`. There is no separate `Detection` entity.

| Field | Type | Notes |
|---|---|---|
| `id` | str (PK) | |
| `run_id` | str (FK→AnalysisRun) | |
| `target_id` | str (FK→MonitorTarget) | |
| `domain` | str | |
| `obs_type` | str | `oil_slick` / `chlorophyll_a` / `turbidity` / `cdom` / `surface_temp` / `inundation` … |
| `value` | float? | for scalar indices (e.g. chl-a proxy) |
| `unit` | str? | `ug_l_equiv` / `ntu_equiv` / `degC` / null |
| `geometry` | geojson? | polygon (detections) or target footprint (indices) |
| `evidence_class` | enum | **`measured`/`modeled`/`inferred`** (INV-3/NFR-8) |
| `confidence` | float | 0–1 |
| `features` | json | shape/contrast/spectral features (audit + look-alike rejection) |
| `status` | enum | `candidate`/`confirmed`/`dismissed` (detections) / `valid` (indices) |
| `created_at` | ts | |

**Evidence class guidance:**
- `measured`: optical proxy from satellite, SAR backscatter, reanalysis (inherently uncertain but observational origin)
- `modeled`: forecast output, risk index, trajectory
- `inferred`: derived from measured values by logic (e.g. bloom_presence inferred from chl-a spike)
- **pH, dissolved N/P, metals, pathogens are never stored as `measured`**

---

## WeatherSeries — D3 Driver/Series Record

| Field | Type | Notes |
|---|---|---|
| `id` | str (PK) | |
| `target_id` | str (FK→MonitorTarget) | |
| `variable` | enum | `precip`/`river_discharge`/`no2`/`so2`/`temp`/`wind` |
| `source` | str | `open_meteo:forecast`/`open_meteo:era5`/`open_meteo:glofas`/`s5p` |
| `series_ref` | str | path to time series (parquet/netCDF) |
| `t0`/`t1` | ts | covered window |
| `evidence_class` | enum | `measured` (obs/reanalysis) / `modeled` (forecast) |

---

## ChokePoint — D4 Drainage Bottleneck Node

| Field | Type | Notes |
|---|---|---|
| `id` | str (PK) | |
| `aoi_id` | str (FK→AOI) | |
| `location` | geojson | point |
| `upstream_area_km2` | float | contributing drainage area |
| `constriction_score` | float | width/topographic constriction metric |
| `dem_source` | str | `cop_glo30`/`hydrosheds` |
| `drainage_ref` | str? | path to derived network raster/vector |

---

## Prediction — Base Record for Tier-A Outputs (Supertype)

| Field | Type | Notes |
|---|---|---|
| `id` | str (PK) | |
| `predictor_id` | str | `OilTrajectory`/`WaterQualityForecast`/`AnomalyDetector`/`FloodRisk`/`AcidDepositionRisk` |
| `target_id` | str (FK→MonitorTarget) | |
| `source_obs_ids` | json[str] | provenance → observations/series used |
| `kind` | enum | `forecast`/`risk`/`anomaly`/`trajectory` |
| `evidence_class` | enum | almost always `modeled` |
| `uncertainty` | json | interval/probability/ensemble spread (required, FR-12) |
| `rng_seed` | int? | reproducibility (NFR-3) |
| `skill_ref` | str? | link to the validation SkillReport gating UI trust |
| `created_at` | ts | |

### Specializations

- **Forecast** — `Prediction(kind="forecast")` + `valid_at`, `value`, `unit`, `ci_low`, `ci_high`
- **RiskAssessment** — `Prediction(kind="risk")` + `risk_level`, `valid_at`, `geometry?`
- **AnomalyResult** — `Prediction(kind="anomaly")` + `baseline_ref`, `deviation`, `direction`
- **ForecastFrame** — `Prediction(kind="trajectory")` per timestep: `valid_at`, `footprint`, `grid_ref`, `particle_count`, `stats`

---

## SkillReport — Validation Gate Output

| Field | Type | Notes |
|---|---|---|
| `id` | str (PK) | |
| `predictor_id` | str | |
| `eval_set` | str | dataset/version scored against |
| `metrics` | json | forecast error vs. persistence; hit/false-alarm |
| `passed_gate` | bool | whether the predictor is trusted in the UI (FR-12, F-029) |
| `created_at` | ts | |

---

## ExposureLayer / ImpactAssessment

**ExposureLayer**

| Field | Type | Notes |
|---|---|---|
| `id` | str (PK) | |
| `type` | enum | `coastline`/`marine_protected_area`/`population`/`cropland`/`drinking_intake`/`recreation_site` |
| `source` | str | dataset + version |
| `geometry_ref` | str | vector/raster path |

**ImpactAssessment**

| Field | Type | Notes |
|---|---|---|
| `id` | str (PK) | |
| `prediction_id` | str (FK→Prediction) | |
| `exposure_layer_id` | str (FK→ExposureLayer) | |
| `valid_at` | ts | first frame intersecting exposure (ETA) |
| `intersected_geometry` | geojson | threatened portion |
| `metrics` | json | coast length at risk / exposed population / intakes threatened / ETA hours |

---

## Alert

| Field | Type | Notes |
|---|---|---|
| `id` | str (PK) | |
| `subject_id` | str | FK→Observation or Prediction |
| `channel` | enum | `webhook`/`email` |
| `payload` | json | summary + product links + record provenance |
| `status` | enum | `pending`/`sent`/`failed` |
| `sent_at` | ts? | |

---

## AIReport / AIQueryLog — Tier-B Grounded Artifacts

**AIReport**

| Field | Type | Notes |
|---|---|---|
| `id` | str (PK) | |
| `scope` | json | target(s)/time window the report covers |
| `text_ref` | str | path to generated report text |
| `citations` | json[str] | record ids backing every factual claim (INV-4/NFR-9) |
| `model` | str | LLM id/version (pinned) |
| `created_at` | ts | |

**AIQueryLog**

| Field | Type | Notes |
|---|---|---|
| `id` | str (PK) | |
| `question` | str | user NL query |
| `resolved_query` | json | structured store query it was translated to |
| `answer_ref` | str | path to grounded answer |
| `citations` | json[str] | record ids in the answer |
| `model` | str | pinned |
| `created_at` | ts | |

---

## EvalCase — Ground Truth for Scoring

| Field | Type | Notes |
|---|---|---|
| `id` | str (PK) | |
| `event_name` | str | `tobago_2024`, `lake_x_bloom_2023`, `storm_y_2022` |
| `domain` | str | |
| `oil_type` | str? | required when `domain="marine_oil"` (ADR-0006; no default) |
| `refs` | json | product ids / API params / paths (no raw imagery) |
| `event_time` | ts | |
| `truth_geometry` | geojson? | or null for negatives |
| `truth_value` | float? | for index validation (in-situ where available) |
| `provenance` | str | source/citation |

---

## Migration Note

SQLite (GeoJSON-as-text, MVP) → PostGIS converts geometry fields to native types + spatial
indexes. Because all stages use `argus.core` store accessors, this is a swap behind the
accessor boundary. Time series (`WeatherSeries`, forecasts) move from parquet/netCDF refs to a
time-series store if/when volume requires.
