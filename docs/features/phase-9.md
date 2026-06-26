# Phase 9 — Domains D3 (Weather/Hydro) & D4 (Choke Points)

- **Status:** Specced (OQ-B must be resolved before F-040)
- **Priority:** P1
- **Last updated:** 2026-06-27
- **Features:** F-040–F-044
- **Depends on:** Phase 8 complete; OQ-B resolved (choke-point definition)
- **Related:** [D3-weather-hydro.md](../domains/D3-weather-hydro.md) · [D4-choke-points.md](../domains/D4-choke-points.md) · [FloodRisk.md](../prediction/FloodRisk.md) · [AcidDepositionRisk.md](../prediction/AcidDepositionRisk.md)
- **Checkpoint:** Completes CP-3 (all 4 domains + full automation)

**GATE:** OQ-B (choke-point definition) must be resolved before F-040 begins. Do not
implement a provisional choke-point definition — the interpretation determines the entire
D4 analysis approach.

---

## F-040 — D4 Choke Points: DEM Flow-Accumulation → Drainage Network + Choke Nodes

**Why:** Choke points are the spatial substrate for flood risk and pollutant concentration assessment.

**Pre-requisite:** OQ-B resolved; DEM tool license confirmed (pysheds/WhiteboxTools — isolate if copyleft).

**Depends on:** F-039, OQ-B

**Owns / creates:**
- `argus/domains/hydro_chokepoints/__init__.py`
- `argus/domains/hydro_chokepoints/analyzer.py` (implements Domain protocol)
- `argus/domains/hydro_chokepoints/dem_processor.py` (flow-direction, accumulation)
- `argus/domains/hydro_chokepoints/constriction.py` (choke-point scoring)
- `config/oil_types.yaml` → `config/dem_sources.yaml` (DEM source registry)
- `argus/core/models.py` (finalize `ChokePoint`)
- `argus/core/store.py` (add ChokePoint CRUD)
- `tests/test_choke_points.py`
- `tests/fixtures/dem_small_aoi.tif` (small synthetic DEM)

**If DEM tool is copyleft:** isolate behind subprocess boundary same as OpenDrift.

**Acceptance criteria:**
- Synthetic DEM → flow accumulation → ≥1 choke-point node identified
- `ChokePoint.upstream_area_km2` and `constriction_score` populated
- VAL-008 passes: no copyleft DEM tool imported in main process if tool is GPL

---

## F-041 — D3 Ingestion: Open-Meteo + SO₂/NO₂ + Sentinel-1 Inundation

**Why:** Flood risk and acid deposition models need weather drivers and atmospheric precursors.

**Depends on:** F-040

**Owns / creates:**
- `argus/domains/weather_hydro/__init__.py`
- `argus/domains/weather_hydro/analyzer.py` (implements Domain protocol; produces WeatherSeries)
- `argus/domains/weather_hydro/open_meteo.py` (precip forecast + ERA5 + GloFAS + air quality)
- `argus/domains/weather_hydro/s5p.py` (Sentinel-5P SO₂/NO₂ search + acquisition)
- `argus/domains/weather_hydro/inundation.py` (Sentinel-1 inundation confirmation)
- `tests/test_weather_hydro_domain.py`

**Quota:** Open-Meteo calls are counted strictly; ERA5 + GloFAS + air quality are separate endpoints each.

**Acceptance criteria:**
- Mocked Open-Meteo precip forecast → `WeatherSeries(variable="precip", evidence_class="modeled")`
- ERA5 history → `WeatherSeries(variable="precip", evidence_class="measured")`
- Quota counter incremented per API call

---

## F-042 — FloodRisk Predictor @ Choke Points + Hydro Impact

**Why:** Quantify near-term overflow/inundation risk at each choke point.

**Depends on:** F-041

**Owns / creates:**
- `argus/predict/flood_risk/__init__.py`
- `argus/predict/flood_risk/predictor.py`
- `argus/predict/flood_risk/evaluator.py` (score vs. historical inundation)
- `tests/test_flood_risk.py`

**Method:** Rule-based (discharge > threshold × channel capacity → risk level) + optional
learned model on historical storm events. Always labeled as `evidence_class="modeled"`.

**Impact:** Extend `ImpactAssessment` for choke-point flood events: population at risk,
infrastructure at risk (from exposure layers).

**Acceptance criteria:**
- Synthetic high-precip + high-discharge WeatherSeries → FloodRisk `RiskAssessment` at nearest choke point
- `evidence_class="modeled"` always (never measured)
- SkillReport generated (even if against limited historical data)

---

## F-043 — AcidDepositionRisk Index (Modeled, Labeled)

**Why:** Acid deposition is a water quality threat in sensitive catchments. Must be modeled
risk, never presented as a measurement.

**Depends on:** F-041

**Owns / creates:**
- `argus/predict/acid_deposition/__init__.py`
- `argus/predict/acid_deposition/predictor.py`
- `tests/test_acid_deposition.py`

**Method:** Physically-motivated index: SO₂_concentration × precip_rate × catchment_sensitivity
→ acid-deposition risk index (0–10 scale). All outputs labeled `evidence_class="modeled"`.

**Honesty:** This index is NEVER presented as a pH measurement. No obs_type suggests acidity
is measured. The index is a risk signal for operator attention.

**Acceptance criteria:**
- High SO₂ + high precip → risk index > 7 (high risk)
- Zero SO₂ → risk index = 0 regardless of precip
- API response includes `evidence_class="modeled"` and an explicit label: "modeled acid-deposition risk"

---

## F-044 — Hydro Viewer + Alerting + Domain Generalization Pass

**Why:** D3/D4 outputs must be visible in the viewer; alerts must fire; the platform must
prove NFR-4 (adding 2 more domains = plug-in, not rewrite).

**Depends on:** F-043

**Owns / creates:**
- `argus/api/routers/` (extend: choke-point endpoints, flood risk, acid risk)
- `argus/api/static/app.js` (extend: choke-point layer, flood risk heat map, acid risk layer)
- `argus/alert/delivery.py` (extend: flood risk and acid risk alerts)
- `tests/test_hydro_viewer.py`, `tests/test_hydro_alerts.py`

**Generalization pass:**
- Verify spine code has no D1/D2/D3/D4 specific references (INV-2)
- Any domain can be enabled/disabled via AOI.domains without code changes

**Acceptance criteria:**
- `argus serve` with all 4 domains enabled: all 4 domain layers visible on map
- FloodRisk alert fires for a synthetic high-risk ChokPoint scenario
- Adding a 5th domain (mock) requires only: new Domain class + registration; no spine edits

## Phase 9 Definition of Done

- [ ] OQ-B resolved before any feature starts
- [ ] F-040–F-044 acceptance criteria met
- [ ] CP-3 complete: all 4 domains operational; automation running; all predictors validated
- [ ] Generalization pass: spine has no domain-specific code
- [ ] NFR-4 demonstration: mock Domain plug-in works without spine changes
