# Eval Results

- **Status:** Active
- **Last updated:** 2026-06-29
- **Owner:** CXLD10

Offline validation results for all 4 observation domains.
Eval cases: `data/eval/`.

---

## D1: marine_oil — tobago_2024

| Metric | Value |
|---|---|
| Eval case | tobago_2024 |
| Method | OilDomainV0 on synthetic SAR (512×512) with planted dark blob |
| Detection | ≥1 oil_slick Observation produced |
| evidence_class | measured (VAL-004 ✓) |
| Precision (offline) | N/A — offline case only; no pixel-level ground truth |
| Status | PASS — detector correctly identifies planted anomaly |

**Note:** Full precision/recall requires live Sentinel-1 CDSE data (tobago_2024 product ID).
Offline case validates the analysis pipeline structure and evidence_class compliance.

---

## D2: inland_wq — gulf_paria_wq_2024

| Metric | Value |
|---|---|
| Eval case | gulf_paria_wq_2024 |
| Method | InlandWqDomain on synthetic Sentinel-2 optical bands (512×512) |
| Observations | 4 produced: chlorophyll_a, turbidity, cdom, bloom_presence |
| evidence_class | measured (VAL-004 ✓) |
| Truth value | 0.14 ndci_index (reference) |
| Status | PASS — analysis pipeline produces correctly typed Observations |

---

## D3: weather_hydro — tobago_flood_risk_2024

| Metric | Value |
|---|---|
| Eval case | tobago_flood_risk_2024 |
| Method | FloodRiskPredictor with synthetic precip (92mm peak) + choke points |
| Prediction | risk_level='high' (matches truth) |
| evidence_class | modeled (VAL-020 ✓) |
| uncertainty | risk_score in uncertainty dict (VAL-006 ✓) |
| Status | PASS — high precip + choke points correctly triggers high risk |

---

## D4: hydro_chokepoints — tobago_choke_points_2024

| Metric | Value |
|---|---|
| Eval case | tobago_choke_points_2024 |
| Method | HydroChokepointsDomain on synthetic funnel DEM |
| Choke points found | ≥1 with constriction_score ≥ 0.5 |
| evidence_class | inferred (VAL-020 ✓) |
| Status | PASS — funnel DEM produces expected drainage constriction |

---

## Summary

| Domain | Eval Case | Status |
|---|---|---|
| D1 marine_oil | tobago_2024 | ✓ PASS (offline) |
| D2 inland_wq | gulf_paria_wq_2024 | ✓ PASS (offline) |
| D3 weather_hydro | tobago_flood_risk_2024 | ✓ PASS (offline) |
| D4 hydro_chokepoints | tobago_choke_points_2024 | ✓ PASS (offline) |

All domains produce correctly typed, evidence-class-compliant outputs.
Live validation (actual Sentinel products) requires CDSE credentials and `--live` flag.
