# Domain D3 — Weather & Hydro-Hazard (`weather_hydro`)

- **Status:** Specced; Phase 9 implements this domain
- **Last updated:** 2026-06-27
- **Code:** `argus/domains/weather_hydro/`
- **Related:** [phase-9.md](../features/phase-9.md) · [FloodRisk.md](../prediction/FloodRisk.md) · [AcidDepositionRisk.md](../prediction/AcidDepositionRisk.md)

---

## Purpose

Ingest precipitation forecasts, ERA5 reanalysis, GloFAS river discharge, and atmospheric
precursor data (SO₂, NO₂) as structured time series to drive flood risk and acid
deposition risk predictors.

---

## Responsibilities

- Fetch precipitation forecast + ERA5 history for an AOI from Open-Meteo (quota-aware)
- Fetch GloFAS river discharge at relevant gauge points
- Fetch SO₂/NO₂ time series from Open-Meteo Air Quality or Sentinel-5P
- Confirm observed inundation from Sentinel-1 post-event SAR
- Persist all data as `WeatherSeries` records with correct `evidence_class`
- Provide structured inputs for `FloodRisk` and `AcidDepositionRisk` predictors

---

## Data Models

**Outputs (WeatherSeries):**
- `WeatherSeries(variable="precip", source="open_meteo:forecast", evidence_class="modeled")`
- `WeatherSeries(variable="precip", source="open_meteo:era5", evidence_class="measured")`
- `WeatherSeries(variable="river_discharge", source="open_meteo:glofas", evidence_class="modeled")`
- `WeatherSeries(variable="so2", source="open_meteo:air_quality"|"s5p", evidence_class="measured")`
- `WeatherSeries(variable="no2", source=..., evidence_class="measured")`
- `Observation(obs_type="inundation", evidence_class="measured", source="S1")` — post-event confirmation

**This domain produces no predictions.** Predictions are produced by Tier A predictors that
consume these WeatherSeries records.

---

## Honesty Rules

- ERA5 reanalysis: `evidence_class="measured"` (re-analysis is the closest to measurement available)
- Open-Meteo forecast: `evidence_class="modeled"` (it's a model run)
- GloFAS discharge: `evidence_class="modeled"` (ensemble model output)
- Sentinel-1 inundation: `evidence_class="measured"` (SAR observation)
- **Acid deposition is never produced here** — it is a Tier A prediction from SO₂/NO₂ + precip

---

## Sources and Quota

| Source | Variable | Quota |
|---|---|---|
| Open-Meteo Forecast | precip, temp, wind | ≤ 10k calls/day total |
| Open-Meteo ERA5 | historical precip, temp | shared quota |
| Open-Meteo GloFAS | river discharge | shared quota; **requires CC BY 4.0 attribution** |
| Open-Meteo Air Quality | SO₂, NO₂ | shared quota |
| CDSE Sentinel-5P | SO₂, NO₂ (optional) | ≤1 GB/day |
| CDSE Sentinel-1 | inundation confirmation | ≤1 GB/day |

---

## Co-dependency with D4

D3 weather series (precip + discharge) are consumed by `FloodRisk` at D4 choke-point nodes.
D3 and D4 must be co-implemented in Phase 9 (F-040 then F-041 in sequence).

---

## OQ-B Note

Choke-point definition (OQ-B) affects how D3's discharge data is evaluated: if choke points
are stormwater-network bottlenecks, then different discharge routing is needed than for
DEM-derived drainage constrictions. D3 ingestion is somewhat flexible (it fetches discharge
at coordinates); D4 analysis determines what coordinates to query.
