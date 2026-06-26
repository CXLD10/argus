# Predictor: AnomalyDetector

- **Status:** Specced; Phase 5 implements
- **Last updated:** 2026-06-27
- **Code:** `argus/predict/anomaly_detector/`
- **Related:** [phase-5.md](../features/phase-5.md) · [D2-inland-wq.md](../domains/D2-inland-wq.md)

---

## Purpose

Detect statistically significant departures from a water body's per-season baseline as early
pollution or discharge warnings.

---

## Method

1. Build rolling multi-year climatology: weekly percentile bands from all available Observation history
2. Apply STL decomposition (if ≥2 years of data) or rolling z-score (if < 2 years)
3. Flag when residual > `alert_sigma` (default 2.5σ; configurable per water body)
4. `direction`: positive (chl-a spike = likely bloom) or negative (turbidity drop = unusual clarity)

---

## Inputs / Outputs

**Inputs:** `Observation[]` history (chlorophyll_a, turbidity, cdom) for a water body

**Outputs:**
- `Prediction(kind="anomaly", predictor_id="AnomalyDetector", evidence_class="modeled")`
  - `baseline_ref = <path to baseline parquet>`
  - `deviation = <z-score or sigma value>`
  - `direction = "positive"|"negative"`
  - `uncertainty = {"sigma": <deviation_value>, "baseline_n_obs": <count>}`

---

## Skill Gate

`passed_gate = True` when:
- False alarm rate < configured threshold on a held-out validation period
- The baseline covers ≥ 52 weekly observations (approximately 1 year of data per week)

Before sufficient history: detector runs but `passed_gate = False` (anomalies shown as
"low confidence — insufficient history" in UI)

---

## Honesty

Anomaly detection is a statistical comparison to a baseline. It is `evidence_class="modeled"`.
It cannot diagnose the cause of an anomaly — that is the AI layer's advisory role (F-033).
