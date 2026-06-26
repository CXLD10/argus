# Predictor: FloodRisk

- **Status:** Specced; Phase 9 implements (BLOCKED on OQ-B)
- **Last updated:** 2026-06-27
- **Code:** `argus/predict/flood_risk/`
- **Related:** [phase-9.md](../features/phase-9.md) · [D3-weather-hydro.md](../domains/D3-weather-hydro.md) · [D4-choke-points.md](../domains/D4-choke-points.md) · [ADR-0004](../adr/ADR-0004-prediction-and-ai-layer.md)

---

## Purpose

Quantify near-term overflow/inundation **risk** at DEM-derived choke-point nodes, combining
precipitation forecast and river discharge with topographic constriction scoring.

---

## Method

Rule-based + optional learned:
1. For each `ChokePoint` in the AOI: fetch GloFAS discharge forecast at nearest gauge
2. Compute discharge excess: `excess = max(0, Q_forecast - Q_threshold_at_constriction)`
3. Combine with precip forecast (7-day cumulative) and upstream area
4. Risk score: `risk_level ∈ {low, medium, high, extreme}` (thresholds configurable)
5. Optional: train a classifier on historical storm events vs. observed inundation (SAR)

**Always labeled as modeled risk, never measured flood occurrence.**

---

## Inputs / Outputs

**Inputs:**
- `ChokePoint[]` for the AOI
- `WeatherSeries(variable="precip")` — Open-Meteo forecast
- `WeatherSeries(variable="river_discharge")` — GloFAS

**Outputs:**
- `Prediction(kind="risk", predictor_id="FloodRisk", evidence_class="modeled")`
  - `risk_level: str`
  - `valid_at: datetime` (forecast horizon)
  - `geometry: ChokePoint.location` (spatial reference)
  - `uncertainty = {"discharge_percentile": ..., "model_type": "rule_based"|"learned"}`

---

## Validation

Score against historical storm events where Sentinel-1 inundation (`Observation(obs_type="inundation")`) was observed.
Metric: hit rate (risk_level ≥ "high" before observed inundation) + false alarm rate.

---

## Honesty

`evidence_class="modeled"` always. The API response includes:
`"label": "modeled flood risk at choke point (not a measured flood)"`.
Observed inundation (post-event SAR) is a separate `Observation`.
