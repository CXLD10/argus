# ADR-0006 — Oil Type Configurability (No Default)

- **Status:** Accepted
- **Date:** 2026-06-27
- **Deciders:** Josh
- **Resolves:** OQ-F (oil type default for trajectory seeding)
- **Related:** [ADR-0002](ADR-0002-data-and-simulation-stack.md) · [docs/prediction/OilTrajectory.md](../prediction/OilTrajectory.md) · F-011

---

## Context

When seeding an oil trajectory simulation in OpenOil, the oil type is a critical physical
parameter. Different oils (crude, diesel, bunker C, condensate, biodiesel, etc.) have
different viscosities, densities, evaporation rates, and emulsification properties — producing
substantially different drift patterns and environmental impacts.

OQ-F asked: what is the default oil type? Prior recommendation (Session 1) was to default
to `generic_oil`. This is rejected for two reasons:

1. **Honesty by design (ADR-0003 D3):** Silently applying a "generic" oil type to a specific
   spill event misrepresents the model's assumptions. The choice of oil type is scientifically
   significant.

2. **Architecture extensibility:** The system should support any oil type that OpenOil supports,
   plus any custom type the operator provides. A hardcoded default discourages explicit
   configuration.

---

## Decisions

### D1 — No Default Oil Type

The `OilTrajectory` predictor has **no default oil type**. Every simulation run must specify
an `oil_type` parameter. A run that omits or provides an unregistered oil type fails
validation with a clear, actionable error message.

### D2 — Oil Type Registry

All supported oil types are registered in `config/oil_types.yaml`. The registry includes:
- A unique ID for each type (e.g., `crude_medium`, `diesel`, `bunker_c`, `condensate`)
- Human-readable name + description
- Key physical properties for documentation (not computed here; OpenOil computes them)
- Whether the type is validated (benchmarked against a historical spill) or provisional

### D3 — CLI and API Accept Oil Type as Parameter

`argus run --domain marine_oil --oil-type crude_medium ...` (required, no default)
`POST /trajectories` body must include `oil_type` (required field)

### D4 — Eval Cases Specify Oil Type

Every `EvalCase` for D1 spill events includes an `oil_type` field. This ensures historical
case re-runs use the correct physical parameters, supporting NFR-3 reproducibility.

### D5 — Extensibility

Adding a new oil type = add an entry to `config/oil_types.yaml`. No code changes required.
Custom types not natively supported by OpenOil may require a custom properties dict
compatible with OpenOil's API.

---

## Consequences

**Positive:**
- Every simulation is honest about its physical assumptions
- The system is extensible to any oil class OpenOil supports
- Historical case re-runs are reproducible (oil type is part of the case record)
- Operators are forced to make an explicit, documented choice

**Negative/costs:**
- Operators must always specify oil type; no "quick run" with a default
- Initial `config/oil_types.yaml` must be seeded with at least a few common types
  before F-011 can be tested

## Cost Validation

`config/oil_types.yaml` is a local configuration file. No cost. OpenOil is open-source
(GPLv2, isolated per ADR-0002 D2). Zero recurring cost.

## Implementation Checklist

- [ ] F-011: Create `config/oil_types.yaml` with at least: crude_medium, diesel, bunker_c
- [ ] F-011: `OilTrajectory.predict()` validates `ctx.oil_type` is in registry before running
- [ ] F-011: Validation error message names available types and registry path
- [ ] F-006 / F-010: EvalCase model includes `oil_type: str` field
- [ ] VAL-017: grep check for hardcoded oil type strings in code
