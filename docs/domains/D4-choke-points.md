# Domain D4 — Hydro Choke Points (`hydro_chokepoints`)

- **Status:** Specced; Phase 9 implements (BLOCKED on OQ-B)
- **Last updated:** 2026-06-27
- **Code:** `argus/domains/hydro_chokepoints/`
- **Related:** [phase-9.md](../features/phase-9.md) · [D3-weather-hydro.md](D3-weather-hydro.md) · [FloodRisk.md](../prediction/FloodRisk.md) · [ADR-0003 D4](../adr/ADR-0003-water-health-platform-and-domains.md) · [OPEN_QUESTIONS.md](../product/OPEN_QUESTIONS.md)

---

## GATE: OQ-B Must Be Resolved

F-040 (first feature of this domain) is blocked until OQ-B is resolved. Do not implement
a provisional definition. The interpretation of "choke point" determines the entire D4
analysis approach.

**Current provisional definition (ADR-0003 D4):** A node on the DEM-derived drainage
network with high upstream contributing area passing through a topographic/width constriction.

---

## Purpose

Derive a drainage network from a free DEM and identify choke-point nodes — topographic
bottlenecks where large upstream areas funnel through narrow constrictions — as the spatial
substrate for flood risk and pollutant-concentration assessment.

---

## Responsibilities

- Download/clip DEM tile for an AOI (Copernicus GLO-30; one-time per AOI)
- Run flow-direction → flow-accumulation → drainage-network extraction
- Score constriction: upstream area × topographic width inverse
- Persist top-N choke-point nodes as `ChokePoint` records
- These nodes become the spatial index for `FloodRisk` evaluation

---

## Data Models

**Inputs:** `AOI`, DEM raster (local)
**Outputs:**
- `ChokePoint(location=Point, upstream_area_km2=float, constriction_score=float, dem_source="cop_glo30")`

`ChokePoint` belongs to `AOI` directly (not to a `MonitorTarget`).

---

## Sources and Quota

| Source | Purpose | Quota |
|---|---|---|
| Copernicus GLO-30 DEM | 30m global DEM | Free; bulk download; one-time per AOI |
| HydroSHEDS | Pre-computed drainage (alternative) | Free; bulk download |

DEM downloads are large (hundreds of MB per AOI) but one-time. Cache locally.

---

## License Check Required

Before implementing F-040, confirm the license of the chosen DEM processing tool:

| Tool | License | Action required |
|---|---|---|
| `pysheds` | MIT | Can import directly |
| `richdem` | Apache 2.0 | Can import directly |
| `WhiteboxTools` | MIT (open-core) | Check which features used; MIT subset is safe |
| `grass_gis` | GPL | **Isolate behind subprocess if used** |

Document the chosen tool and its license in ADR before implementing.

---

## Domain Protocol Note

Unlike D1–D3 (which operate on time windows), D4 is a one-time analysis per AOI:
- `search()` returns a `SourceRef` for the DEM tile(s) covering the AOI
- `acquire()` downloads and clips the DEM
- `analyze()` derives the drainage network and choke points

The `Domain` protocol still applies; the "time window" parameter is effectively ignored
(DEM is static; choke points are re-computed if DEM updates).
