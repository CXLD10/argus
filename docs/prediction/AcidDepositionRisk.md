# Predictor: AcidDepositionRisk

- **Status:** Specced; Phase 9 implements
- **Last updated:** 2026-06-27
- **Code:** `argus/predict/acid_deposition/`
- **Related:** [phase-9.md](../features/phase-9.md) · [D3-weather-hydro.md](../domains/D3-weather-hydro.md)

---

## Purpose

Compute a physically-motivated acid-deposition **risk index** from atmospheric precursors
and precipitation. This is NOT a pH measurement or an acid rain detection — it is a modeled
risk signal for operator attention.

---

## Method

Physically-motivated index:
```
acid_risk_index = normalize(SO2_conc × NO2_conc × precip_rate × catchment_sensitivity)
```

- SO₂ and NO₂ from Open-Meteo Air Quality or Sentinel-5P
- Precipitation from Open-Meteo forecast
- Catchment sensitivity from `MonitorTarget.attrs.acid_sensitivity` (configurable)
- Output: index on 0–10 scale (0 = negligible risk; 10 = high risk)

**No machine learning required.** Pure formula-based. No training data needed.

---

## Honesty (Critical)

This index is **NEVER** presented as a pH measurement. Ever.

The API response always includes:
```json
{
  "evidence_class": "modeled",
  "label": "modeled acid-deposition risk index (0–10 scale) — NOT a pH measurement",
  "methodology": "SO2 × NO2 × precip × catchment sensitivity index"
}
```

`obs_type` is never set to anything implying pH or acid measurement.

---

## Inputs / Outputs

**Inputs:**
- `WeatherSeries(variable="so2")` + `WeatherSeries(variable="no2")`
- `WeatherSeries(variable="precip")`
- `MonitorTarget.attrs.acid_sensitivity` (optional; defaults to medium if not set)

**Outputs:**
- `Prediction(kind="risk", predictor_id="AcidDepositionRisk", evidence_class="modeled")`
  - `value = <index 0–10>`
  - `uncertainty = {"index_range": [low, high], "so2_source": ..., "precip_source": ...}`

---

## Validation

Compare index against historical acid rain sensor data (where available) or expert labels.
This is an informational comparison — the index is a screening tool, not a certified sensor.

## Cost Validation

Pure formula computation. No external API calls beyond D3 inputs already fetched. Zero cost.
