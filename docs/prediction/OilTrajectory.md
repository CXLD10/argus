# Predictor: OilTrajectory

- **Status:** Specced; Phase 2 implements
- **Last updated:** 2026-06-27
- **Code:** `argus/predict/oil_trajectory/`
- **Related:** [phase-2.md](../features/phase-2.md) · [D1-marine-oil.md](../domains/D1-marine-oil.md) · [ADR-0002](../adr/ADR-0002-data-and-simulation-stack.md) · [ADR-0006](../adr/ADR-0006-oil-type-configurability.md)

---

## Purpose

Forecast oil drift from a detection, producing probability footprints per timestep for the
next 6–72 hours, with uncertainty quantified from particle spread.

---

## Method

OpenOil (part of the `opendrift` library, GPLv2) particle simulation:
- N particles seeded at the detection polygon centroid (and/or distributed over polygon)
- Forced by CMEMS currents + Open-Meteo winds (or fallback)
- Each timestep: advect particles + apply weathering (evaporation, emulsification)
- Output: particle cloud per timestep → probability footprint polygon

**GPL isolation (ADR-0002 D2):** OpenOil runs in an isolated subprocess. The main process
calls `runner.py`; only `sim_worker.py` imports opendrift.

---

## Oil Type Requirement (ADR-0006)

- `oil_type` parameter is REQUIRED. No default. Validation fails if absent.
- Must be a registered type from `config/oil_types.yaml`
- Registered types: `crude_medium`, `diesel`, `bunker_c`, `condensate` (MVP)
- `EvalCase.oil_type` must be set for reproducibility (NFR-3)

---

## Inputs / Outputs

**Inputs:**
- `Observation(obs_type="oil_slick")` — detection to seed the simulation
- `oil_type: str` — from config/operator (required)
- Metocean forcing: CMEMS currents + Open-Meteo winds for the forecast window
- `rng_seed: int` — for reproducibility

**Outputs:**
- `Prediction(kind="trajectory", predictor_id="OilTrajectory", evidence_class="modeled")`
  - `uncertainty = {"particle_spread_km": ..., "footprint_90pct_km2": ...}`
  - `rng_seed = <seed used>`
- `ForecastFrame[]` per timestep (T+1h, T+3h, T+6h, T+12h, T+24h, T+48h, T+72h)
  - `footprint = <polygon enclosing 90% of particles>`
  - `stats = {"centroid_lat": ..., "centroid_lon": ..., "spread_km": ...}`

---

## Validation (SkillReport)

**Metric:** km separation between predicted centroid and actual SAR observation at T+24h
**Reference:** tobago_2024 eval case (+ additional cases as data permits)
**Gate (`passed_gate=True`):** Established after first historical validation run; threshold
set based on baseline skill. The gate is informational until enough cases exist for statistics.

---

## Cost Validation

OpenOil: open-source (GPLv2, isolated). CMEMS: free registration. Open-Meteo: free
non-commercial (CC BY 4.0). Zero recurring cost.
