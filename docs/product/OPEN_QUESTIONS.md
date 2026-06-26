# Argus — Open Questions

- **Owner:** Josh (decision maker)
- **Last updated:** 2026-06-27
- **Purpose:** Single source of truth for all open questions. Resolved questions become ADRs.
- **Rule:** Never resolve an OQ by assumption. All resolutions require explicit confirmation.

---

## Resolved

### OQ-A — Demo Lead Domain

**Question:** Should the platform demonstration lead with D2 inland water quality, or is D1
oil the primary demo vehicle?

**Status:** RESOLVED — 2026-06-27

**Resolution:** The MVP demonstration is the **complete Argus Environmental Intelligence
Platform** — all 4 domains, full prediction engine, full AI layer, production dashboard.
There is no "demo lead" domain because the MVP is the full platform.

**ADR:** [ADR-0005](../adr/ADR-0005-mvp-redefinition.md)

---

### OQ-F — Oil Type Default for Trajectory Seeding

**Question:** What is the default oil type for seeding the OpenOil trajectory simulation?

**Status:** RESOLVED — 2026-06-27

**Resolution:** There is NO default oil type. The trajectory simulation requires an explicit
`oil_type` parameter in every run. Oil types are registered in `config/oil_types.yaml`.
A simulation job that does not specify a registered oil type fails validation. This keeps the
model honest (different oils behave differently) and the architecture extensible.

**ADR:** [ADR-0006](../adr/ADR-0006-oil-type-configurability.md)

---

## Open

### OQ-B — Choke Point Definition

**Question:** Is a "choke point" (a) a DEM flow-accumulation bottleneck with a topographic
width constriction (current ADR-0003 D4 working definition), (b) a stormwater-network
bottleneck, or (c) a pollutant-accumulation basin?

**Impact if unresolved:** Blocks F-040 (D4 choke-point derivation). Phase 9 cannot start.

**Current default (provisional):** ADR-0003 D4 — DEM-derived drainage-constriction node
(high upstream contributing area + narrow topographic passage). This is provisional and
labeled as such in all Phase 9 specs.

**Decision needed from:** Josh

**Options:**
1. Confirm drainage-constriction node definition (ADR-0003 D4 default)
2. Redefine as stormwater-network bottleneck (requires vector network data)
3. Redefine as pollutant-accumulation basin (requires concentration modeling)

---

### OQ-C — In-Situ Calibration Data Availability

**Question:** Will any in-situ water quality reference data be available for at least one
water body, to enable calibrated absolute concentrations for D2 (inland WQ)?

**Impact if unresolved:** F-026 will proceed with relative-only calibration state
(`calibration_state="relative_only"`) until resolved. This is safe and honest but limits
the absolute quantitative outputs.

**Current default:** Relative-only. Calibration hooks are built in (F-026), so switching
to calibrated mode later does not require a rewrite.

**Decision needed from:** Josh

**Options:**
1. Proceed relative-only (safe default; activate calibration later when data is available)
2. Identify a public in-situ reference dataset for the chosen reference lake

---

### OQ-D — LLM Model Tier and Monthly Call Budget

**Question:** Which Claude model tier should the AI layer use? What is the acceptable monthly
API call count?

**Impact if unresolved:** F-030 scaffolding will mock the API. No live LLM calls needed
until Phase 6 testing. However, the system prompt design and cost estimation require knowing
the model.

**Current default:** Use a cost-efficient Claude model (haiku or similar); templated
fallback when over budget; no live API in default CI suite.

**Decision needed from:** Josh

**Constraint:** Must remain within the zero-cost constraint (free tier or educational
credits). If no free tier exists for the chosen model, OQ-D resolution must identify an
alternative (e.g., local open-source LLM — but grounding quality may differ).

---

### OQ-E — NL-Query Read-Only for MVP?

**Question:** Should the NL query feature (F-032) be strictly read-only (query the store,
return grounded answers) or should it also support write actions (e.g., create AOIs,
configure alerts via natural language)?

**Impact if unresolved:** F-032 proceeds with read-only assumption.

**Current default:** Yes, read-only. Write actions via NL are deferred post-MVP.

**Decision needed from:** Josh (low urgency; default is safe)
