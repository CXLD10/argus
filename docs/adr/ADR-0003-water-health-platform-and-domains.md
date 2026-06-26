# ADR-0003 — Reframe to a Water Health Platform with pluggable observation domains

- **Status:** Accepted (supersedes the framing in ADR-0001 §Decision-1; keeps its pipeline decisions)
- **Date:** 2026-06-26
- **Deciders:** Josh
- **Related:** [ADR-0001](ADR-0001-vertical-and-pipeline.md) · [ADR-0002](ADR-0002-data-and-simulation-stack.md) · [ADR-0004](ADR-0004-prediction-and-ai-layer.md) · [PRD.md](../product/PRD.md)

## Context

Argus began as a marine/coastal hazard detector (oil → flood). The product target has
broadened to a **water health intelligence platform** for municipal and watershed
professionals: monitor lakes/ponds/reservoirs for deteriorating water quality, predict
rain-driven flooding, model acid-deposition risk, and find hydrological choke points where
floodwater and pollutant load concentrate — with a prediction engine and AI features on top.

This is a genuine scope increase. Two failure modes to avoid:
1. **Over-claiming.** Pretending satellites measure things they cannot (dissolved nutrients,
   heavy metals, pathogens, pH). That would make Argus an impressive demo that collapses
   under expert scrutiny.
2. **Sprawl.** Building four domains + full ML + full GenAI at once, blowing the
   zero-budget/laptop constraint and the "real outcomes, not demos" principle.

The existing architecture (ADR-0001/0002) already uses a staged, stage-as-records pipeline
with a plug-in `Detector` interface. That interface was named for oil; the right move is to
**generalize it to observation domains**, so new water-health capabilities slot in behind
stable interfaces rather than forcing a rewrite.

## Decisions

### D1 — Argus is a Water Health Intelligence Platform
The product is reframed accordingly (see [PRD.md](../product/PRD.md)). The marine oil capability
becomes **one domain among several**, retained because it best exercises the prediction
engine (trajectory simulation) end-to-end.

### D2 — Observation-domain abstraction
Generalize the `Detector` plug-in into a **domain** abstraction. Each domain is a
self-contained `(source + analyzer)` plug-in that writes `Observation`/`Detection` records
into the shared store. The spine (tasking, ingestion, store, impact, delivery, API, viewer,
alerting) and the prediction + AI layers are **domain-agnostic**.

MVP-era domains:

| Domain | Code | Sources | Produces |
| --- | --- | --- | --- |
| **D1 Marine surface (oil)** | `marine_oil` | Sentinel-1 SAR | oil-slick detections (+ trajectory) |
| **D2 Inland water quality** | `inland_wq` | Sentinel-2 (10m), Sentinel-3 OLCI (300m) | chlorophyll-a, turbidity/TSS, CDOM, surface-temp indices per water body; anomalies |
| **D3 Weather & hydro-hazard** | `weather_hydro` | Open-Meteo (precip forecast, ERA5 history, GloFAS Flood API, Air-Quality SO₂/NO₂), Sentinel-5P, Sentinel-1 (observed inundation) | rain-flood risk; acid-deposition **risk index** |
| **D4 Hydrology / choke points** | `hydro_chokepoints` | Copernicus GLO-30 DEM / HydroSHEDS | drainage network + choke-point nodes (flow-accumulation bottlenecks) |

### D3 — Honest observability boundary (binding)
The platform distinguishes **measured proxies**, **modeled risk**, and **what it cannot
see**, and never blurs them in data, API, or UI:

- **Optical proxies (measured, calibration-dependent):** chlorophyll-a, turbidity/TSS, CDOM,
  surface temperature. Robust for *relative change / trend / anomaly*; absolute
  concentrations require in-situ calibration (tracked as a calibration state per water body).
- **Not observable from orbit:** dissolved N/P directly, heavy metals, pathogens, pH. These
  are never reported as measurements; eutrophication/pollution is inferred via optical
  proxies + anomaly detection, flagged as inference.
- **Acid rain:** reported only as a **modeled acid-deposition risk index** (precursors ×
  precipitation), labeled as model output, validated against ground sensors where available.
- **Resolution floor:** a minimum monitorable water-body size policy (default derived from
  Sentinel-2 10m; very small ponds are marked `below_resolution` rather than silently
  estimated).

### D4 — Choke point definition (working; see Open Questions)
A **choke point** is a node on the DEM-derived drainage network with high upstream
contributing area passing through a topographic/width constriction — i.e., where a large
amount of water (and the pollutant load it carries) funnels through a narrow point. These are
simultaneously flood-risk hotspots and pollutant-accumulation nodes. Computed from a free DEM
via flow-direction → flow-accumulation → constriction scoring. *This interpretation is
flagged for confirmation in Open Questions.*

### D5 — Two-tier MVP
- **Vertical-Slice MVP** (already specced, Phases 0–3): the domain-agnostic spine proven
  end-to-end on **one domain (D1 oil)** — detection → prediction (trajectory) → impact →
  alert → viewer. This de-risks the pipeline fastest and keeps the specced work.
- **Platform MVP** (the milestone that demonstrates the vision): spine + **two domains
  (D1 oil + D2 inland water quality)** + the **prediction engine** (trajectory + ML
  forecasting + anomaly detection) + the **AI layer** (NL report + NL query) + viewer +
  alerting. D3 and D4 follow as additive domains.

## Consequences

**Positive**
- The platform vision is captured without a rewrite: the spine and prediction/AI layers are
  domain-agnostic; domains are additive plug-ins (proves the architecture generalizes — a
  strong portfolio story).
- The honest-observability boundary is a *design invariant*, not a disclaimer bolted on
  late, which is what makes the platform credible to domain experts.

**Negative / costs**
- More moving parts than a single vertical. Mitigated by the two-tier MVP: ship the
  vertical slice first, expand by domain.
- The optical-proxy/calibration model adds per-water-body state. Accepted: it is the price of
  not over-claiming.

## Alternatives considered
- **Bolt new hazard types onto the oil `Detector` directly.** Rejected: leaks domain
  specifics into the spine and the data model; the domain abstraction is cleaner and is the
  generalization story.
- **Lead the platform with inland water quality and drop/defer oil.** Reasonable; oil is
  retained only because it best exercises the prediction engine (trajectory) and is already
  specced. The lead *domain of the platform demo* is open (see Open Questions).

## Open questions
- **OQ-A (sequencing):** Should the platform demo lead with **D2 inland water quality** (most
  central to the city/water-health ask, broadest municipal user base) while D1 oil remains
  the spine-proving slice? *Recommendation: yes.* Needs Josh's confirmation.
- **OQ-B (choke point):** Confirm the D4 definition above (drainage-constriction nodes) vs. an
  alternative meaning (e.g., stormwater-network bottlenecks, or pollutant-accumulation basins).
- **OQ-C (calibration):** Will any in-situ reference data be available for at least one water
  body to calibrate optical proxies, or is the MVP relative-only? *Default: relative-only with
  calibration hooks.*

## Cost Validation

All observation domains use free data sources (CDSE free-user quota; Open-Meteo free non-commercial ≤10k calls/day with CC BY 4.0 attribution; Copernicus DEM free; HydroSHEDS free). The domain plug-in architecture is a software design pattern with zero cost impact. Zero recurring cost.
