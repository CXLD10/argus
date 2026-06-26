# Domain D1 — Marine Oil (`marine_oil`)

- **Status:** Specced; Phase 0–3 implements this domain
- **Last updated:** 2026-06-27
- **Code:** `argus/domains/marine_oil/`
- **Related:** [phase-0.md](../features/phase-0.md) · [phase-1.md](../features/phase-1.md) · [phase-2.md](../features/phase-2.md) · [OilTrajectory.md](../prediction/OilTrajectory.md) · [ADR-0002](../adr/ADR-0002-data-and-simulation-stack.md) · [ADR-0006](../adr/ADR-0006-oil-type-configurability.md)

---

## Purpose

Detect hydrocarbon surface slicks in Sentinel-1 SAR imagery and feed detections into the
OilTrajectory predictor for drift forecasting and impact assessment.

---

## Responsibilities

- Search CDSE for S1 GRD products (IW mode, VV polarization) intersecting an AOI
- Acquire AOI-subset σ⁰ dB rasters via CDSE Process API
- Preprocess: dB conversion, speckle filter, land masking
- Detect dark spots: Otsu/adaptive segmentation + morphological cleanup
- Compute shape and backscatter features
- Classify: look-alike rejection; assign confidence score
- Produce `Observation` records with `obs_type="oil_slick"`, `evidence_class="measured"`

---

## Domain Interface Implementation

```python
class MarineOilDomain(Domain):
    domain_id = "marine_oil"

    def search(self, target: MonitorTarget, t0, t1) -> list[SourceRef]:
        # Search CDSE S1 GRD catalogue
        ...

    def acquire(self, ref: SourceRef) -> Acquisition:
        # CDSE Process API subset or fallback full download
        ...

    def analyze(self, acq: Acquisition) -> list[Observation]:
        # preprocess → segment → classify → Observation[]
        ...
```

---

## Data Models

**Inputs:** `MonitorTarget(kind="region")`, time window
**Outputs:**
- `Scene(domain="marine_oil", source="S1")`
- `AnalysisRun(domain="marine_oil", analyzer="oil_darkspot.v1")`
- `Observation(obs_type="oil_slick", evidence_class="measured", confidence=0–1, features={shape, backscatter})`

**evidence_class:** Always `"measured"` — SAR dark-spot detection is a physical measurement.
The classifier assigns `confidence` (0–1); low-confidence detections remain `status="candidate"`.

---

## Sources and Quota

| Source | Purpose | Quota |
|---|---|---|
| CDSE S1 GRD | SAR scenes | ≤1 GB/day |
| CDSE Process API | AOI subset eval script | Counted in bytes |

Prefer Process API subsets. Full-scene download is a flagged fallback.

---

## Interfaces with Other Components

- **Spine ingest:** uses `argus.ingest.catalogue.search_s1_grd()` and `argus.ingest.acquire.acquire()`
- **Predictor:** detections consumed by `OilTrajectory` predictor
- **Store:** `AnalysisRun` + `Observation` written via `argus.core.store`
- **Spine does not change:** Domain is purely additive (NFR-4)

---

## Honesty

- SAR dark spots are **measured** (physical signal) — `evidence_class="measured"` always
- Confidence score (classifier output) does not change evidence_class
- Oil type is NOT inferred from SAR; it must be provided externally (ADR-0006)
- Very thin films (< SAR detection limit) may be missed — not flagged, not estimated

---

## Known Limitations

- Wind shadows, ship wakes, biogenic films, and rain cells can produce SAR dark spots
  (look-alike rejection via classifier reduces but cannot eliminate false positives)
- Night/cloud coverage: SAR is all-weather/all-time, but some incidence angle geometries
  reduce sensitivity
- Oil slick thickness is not recoverable from SAR intensity alone

---

## Future Extensions

- Multi-polarization (VV+VH) for better look-alike discrimination
- Multi-date coherence change detection for chronic polluters
- Deep-learning segmentation (post-MVP, GPU optional)
