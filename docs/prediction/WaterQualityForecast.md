# Predictor: WaterQualityForecast

- **Status:** Specced; Phase 5 implements
- **Last updated:** 2026-06-27
- **Code:** `argus/predict/wq_forecast/`
- **Related:** [phase-5.md](../features/phase-5.md) · [D2-inland-wq.md](../domains/D2-inland-wq.md) · [ADR-0004](../adr/ADR-0004-prediction-and-ai-layer.md)

---

## Purpose

Forecast water quality indices (primarily chlorophyll-a as a bloom-risk proxy) 7 days ahead
per water body, with a 90% confidence interval. Must beat the persistence baseline before
being trusted in the UI (skill gate).

---

## Method

Gradient-boosted tree model (scikit-learn GradientBoostingRegressor):
- Features: lagged chl-a (t-1, t-7, t-14 days), seasonal index (DOY), precip_7d, temp_7d (Open-Meteo)
- Target: chl-a proxy at t+7 days
- Training: per-water-body (or cross-water-body with site as feature if sparse)
- CI: bootstrapped 90% interval (B=100 bootstrap samples)

**CPU-only, no GPU, no deep learning.** Training time target: < 5 min per water body on laptop.

---

## Skill Gate

The predictor is not trusted in the API viewer until:
- `SkillReport.passed_gate = True`
- Passes gate when: RMSE on held-out data < RMSE of persistence baseline (predict t+7 = t-0)
- If insufficient history: model is built but `passed_gate = False` until validated

---

## Inputs / Outputs

**Inputs:**
- `Observation[]` history (chlorophyll_a, turbidity) for the target water body
- `WeatherSeries` from Open-Meteo (precip, temp for the forecast window and lagged period)
- `rng_seed: int`

**Outputs:**
- `Prediction(kind="forecast", predictor_id="WaterQualityForecast", evidence_class="modeled")`
  - `value = <7-day chl-a proxy forecast>`
  - `ci_low, ci_high = <90% CI bounds>`
  - `valid_at = <forecast date>`
  - `uncertainty = {"ci_90_low": ..., "ci_90_high": ..., "rmse_vs_persistence": ...}`

---

## Honesty

`evidence_class="modeled"` always. This is a model forecast, not a measurement.
CI bands must be shown alongside the forecast value in the UI.
The API response includes: `"label": "7-day bloom-risk forecast (model output)"`.

---

## Cost Validation

scikit-learn: open-source. Open-Meteo training data: free (CC BY 4.0). Zero recurring cost.
