# Phase 2 — Simulation Vertical (Oil)

- **Status:** Specced; waiting for Phase 1
- **Priority:** P0
- **Last updated:** 2026-06-27
- **Depends on:** Phase 1 complete; OQ-F resolved ✓ (ADR-0006: configurable oil types)
- **Related:** [phase-1.md](phase-1.md) · [OilTrajectory.md](../prediction/OilTrajectory.md) · [ADR-0002](../adr/ADR-0002-data-and-simulation-stack.md) · [ADR-0006](../adr/ADR-0006-oil-type-configurability.md)
- **Checkpoint:** Part of CP-1

**Goal:** Add a validated oil drift trajectory predictor, isolated from the GPL-licensed
OpenOil library, with metocean forcing from free APIs. Every simulation uses an explicit,
registered oil type (no defaults).

---

## F-011 — OpenOil Simulation Service (Isolated) + Oil Type Registry

**Why:** Oil drift trajectory is the first Tier-A predictor. OpenOil is GPLv2 and must not
contaminate the main process (ADR-0002 D2). Oil type must come from a validated registry
(ADR-0006).

**Depends on:** F-010 (Observation schema frozen)

**Owns / creates:**
- `argus/predict/__init__.py`
- `argus/predict/base.py` (`Predictor` protocol — scaffold only; frozen in F-029)
- `argus/predict/oil_trajectory/__init__.py`
- `argus/predict/oil_trajectory/runner.py` (main process interface; subprocess wrapper)
- `argus/predict/oil_trajectory/sim_worker.py` (the isolated subprocess; imports opendrift here only)
- `argus/predict/oil_trajectory/oil_types.py` (loads and validates config/oil_types.yaml)
- `config/oil_types.yaml` (oil type registry: crude_medium, diesel, bunker_c, condensate)
- `argus/core/models.py` (add `Prediction`, `ForecastFrame` scaffold)
- `argus/core/store.py` (add `Prediction` CRUD scaffold)
- `tests/test_oil_trajectory_service.py`

**GPL isolation pattern:**
```
main process (argus/predict/oil_trajectory/runner.py)
  └─ subprocess.run(["python", "sim_worker.py", "--input", ...])
       └─ sim_worker.py imports opendrift ← only here
```

**oil_types.yaml structure:**
```yaml
oil_types:
  - id: crude_medium
    name: "Medium crude oil"
    openoil_name: "GENERIC CRUDE"
    validated: false  # no spill benchmark yet
  - id: diesel
    name: "Marine diesel"
    openoil_name: "GENERIC DIESEL"
    validated: false
  - id: bunker_c
    name: "Bunker C heavy fuel oil"
    openoil_name: "BUNKER C"
    validated: false
```

**Acceptance criteria:**
- Given a mocked forcing input and `oil_type="crude_medium"`, subprocess returns valid trajectory JSON
- Missing `oil_type` → `OilTypeRequiredError` (not a default applied silently)
- Unregistered `oil_type` → `OilTypeNotFoundError` listing available types
- GPL isolation verified: `grep -r "import opendrift" argus/` returns only `sim_worker.py`

---

## F-012 — Metocean Forcing Providers + Caching + Fallback

**Why:** The trajectory simulation needs winds and currents. Both must come from free sources
with caching to avoid repeated API calls.

**Depends on:** F-011

**Owns / creates:**
- `argus/predict/oil_trajectory/forcing.py`
- `argus/predict/oil_trajectory/cache.py` (parquet-based forcing cache)
- `tests/test_forcing_providers.py`
- `tests/fixtures/cmems_currents_tobago.parquet`
- `tests/fixtures/open_meteo_winds_tobago.json`

**Forcing sources:**
- Primary currents: CMEMS (Copernicus Marine) — free with registration
- Primary winds: Open-Meteo forecast or ERA5 history — free, ≤10k calls/day
- Fallback: if CMEMS unavailable → Open-Meteo marine API for wind+wave

**Quota accounting:** Every Open-Meteo call increments the daily counter. CMEMS bytes tracked.

**Acceptance criteria:**
- Mocked CMEMS + Open-Meteo → combined forcing object returned with correct grid and time
- Cache hit: second call with same params reads from parquet, makes zero HTTP calls
- Fallback: CMEMS mocked as unavailable → Open-Meteo marine used; result still valid

---

## F-013 — ForecastFrames + Trajectory Evaluation

**Why:** Persist the trajectory output and measure simulation skill against historical data.

**Depends on:** F-012

**Owns / creates:**
- `argus/predict/oil_trajectory/evaluator.py`
- `argus/core/models.py` (finalize `Prediction`, `ForecastFrame`)
- `argus/core/store.py` (finalize `Prediction`, `ForecastFrame` CRUD)
- `data/eval/tobago_2024_trajectory.json` (trajectory eval case with truth)
- `tests/test_forecast_frames.py`

**`ForecastFrame` fields (per DATA_MODELS.md):**
kind="trajectory", valid_at, footprint (probability footprint polygon), grid_ref,
particle_count, stats (min/mean/max drift distance)

**Skill metric:** km separation between predicted centroid and actual SAR observation at T+24h.
Stored in `SkillReport` (informational at this stage; gating is F-029).

**Acceptance criteria:**
- Simulation run produces ≥1 `ForecastFrame` per output timestep
- `Prediction.uncertainty` is populated (particle spread as uncertainty measure)
- `Prediction.rng_seed` matches the seed used in the simulation
- Skill metric computed and stored in `SkillReport` (even if metric is poor at this stage)

## Phase 2 Definition of Done

- [ ] F-011–F-013 acceptance criteria met
- [ ] GPL isolation verified by grep: only `sim_worker.py` imports opendrift
- [ ] `config/oil_types.yaml` has ≥3 registered types
- [ ] Trajectory skill report exists for tobago_2024 (baseline established)
- [ ] `Prediction.uncertainty` non-null for all outputs
