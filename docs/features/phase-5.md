# Phase 5 — Prediction Engine: Water Quality

- **Status:** Specced; waiting for Phase 4
- **Priority:** P0
- **Last updated:** 2026-06-27
- **Features:** F-027–F-029
- **Depends on:** Phase 4 complete; history of WQ Observations available for training
- **Related:** [WaterQualityForecast.md](../prediction/WaterQualityForecast.md) · [AnomalyDetector.md](../prediction/AnomalyDetector.md) · [ADR-0004](../adr/ADR-0004-prediction-and-ai-layer.md)

**Goal:** Build the water quality prediction engine: seasonal baseline, anomaly detection,
and bloom-risk forecasting with validated skill. Establish the `Predictor` interface and
the skill gate that blocks unvalidated predictors from the UI.

---

## F-027 — Per-Water-Body Seasonal Baseline + AnomalyDetector

**Why:** Early warning requires detecting departures from a water body's normal seasonal
pattern — not just absolute thresholds.

**Depends on:** F-026 (Observations with chlorophyll-a, turbidity, CDOM exist)

**Owns / creates:**
- `argus/predict/anomaly_detector/__init__.py`
- `argus/predict/anomaly_detector/baseline.py` (STL decomposition or rolling climatology)
- `argus/predict/anomaly_detector/detector.py` (z-score vs. seasonal baseline)
- `argus/core/store.py` (add Prediction(kind="anomaly") CRUD)
- `tests/test_anomaly_detector.py`

**Algorithm:**
- Build rolling 3-year climatology (weekly bins) from Observation history
- Decompose into trend + seasonal + residual (STL if sufficient history; z-score otherwise)
- Flag observations where residual > threshold_sigma (default 2.5σ; configurable)
- `Prediction(kind="anomaly", evidence_class="modeled", uncertainty={"sigma": value})`

**Acceptance criteria:**
- Synthetic Observations with planted spike → AnomalyResult flagged
- Stable time series (no spikes) → no anomaly flagged
- Anomaly `Prediction.uncertainty` non-null (sigma value present)

---

## F-028 — WaterQualityForecast (n-day bloom-risk + CI)

**Why:** Short-term forecast lets operators act before a bloom develops, not after.

**Depends on:** F-027 (baseline established)

**Owns / creates:**
- `argus/predict/wq_forecast/__init__.py`
- `argus/predict/wq_forecast/model.py` (GBM model; train + predict)
- `argus/predict/wq_forecast/trainer.py` (feature engineering; train on history)
- `argus/predict/wq_forecast/drivers.py` (Open-Meteo ERA5 history as training features)
- `models/wq_forecast_v1.pkl` (trained model artifact)
- `tests/test_wq_forecast.py`

**Features:**
- Inputs: lagged chl-a/turbidity (t-1, t-7, t-14), seasonal index, precip_7d, temp_7d
- Target: chl-a at t+7 days (bloom-risk forecast window)
- CI: bootstrapped 90% CI bands
- `Prediction(kind="forecast", evidence_class="modeled", value=pred, ci_low=..., ci_high=...)`

**Model must beat persistence baseline** (predicting t+7 = t-0 value) before UI trust (F-029).

**Acceptance criteria:**
- On held-out synthetic history: RMSE computed and logged
- `Prediction.ci_low < Prediction.value < Prediction.ci_high`
- `Prediction.uncertainty = {"ci_90_low": ..., "ci_90_high": ..., "rmse": ...}`

---

## F-029 — Predictor Interface + Validation/Skill Gate

**Why:** Predictors must be independently validatable, and the UI must not trust an
unvalidated predictor.

**Depends on:** F-028

**Owns / creates:**
- `argus/predict/base.py` (finalize `Predictor` protocol: predict + validate)
- `argus/eval/skill_gate.py` (check SkillReport.passed_gate before surfacing in API)
- `argus/core/store.py` (finalize `SkillReport` CRUD)
- `tests/test_skill_gate.py`

**Predictor protocol (final):**
```python
class Predictor(Protocol):
    predictor_id: str
    def predict(self, ctx: PredictContext, rng_seed: int) -> Prediction: ...
    def validate(self, history: EvalSet) -> SkillReport: ...
```

**Skill gate:**
- `SkillReport.passed_gate = True` only if:
  - WQForecast: beats persistence baseline on held-out data
  - AnomalyDetector: false alarm rate < configured threshold
- API: `GET /waterbody/{id}/forecasts` returns only predictions from predictors with `passed_gate=True`
- Before gate passes: predictions visible in internal `GET /waterbody/{id}/raw_predictions`

**Acceptance criteria:**
- Mock predictor with `passed_gate=False` → not returned by forecasts endpoint
- Mock predictor with `passed_gate=True` → returned
- VAL-021: F-029 must be DONE before any Phase 5 feature is marked DONE in BOARD.md

## Phase 5 Definition of Done

- [ ] F-027–F-029 acceptance criteria met
- [ ] WQForecast SkillReport generated; `passed_gate` set correctly
- [ ] AnomalyDetector SkillReport generated; false alarm rate acceptable
- [ ] API skill gate enforced and tested
- [ ] All Prediction records have non-null `uncertainty`
