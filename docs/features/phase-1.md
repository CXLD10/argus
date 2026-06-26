# Phase 1 — Detection Vertical (Oil)

- **Status:** Specced; waiting for Phase 0 complete
- **Priority:** P0
- **Last updated:** 2026-06-27
- **Depends on:** Phase 0 complete; `Domain` protocol stable (F-005 DoD)
- **Related:** [phase-0.md](phase-0.md) · [D1-marine-oil.md](../domains/D1-marine-oil.md) · [BOARD.md](../../BOARD.md)
- **Checkpoint:** Part of CP-1 (oil pipeline)

**Goal:** Replace the naive detector internals with production-quality segmentation and
look-alike rejection; establish the evaluation harness; finalize the Observation schema.

---

## F-007 — Robust Dark-Spot Segmentation + Feature Extraction

**Why:** The v0 detector (F-005) uses a naive threshold; this replaces the internals with
real segmentation while keeping the `Domain` interface unchanged.

**Depends on:** F-005 (stable Domain protocol)

**Owns / creates:**
- `argus/domains/marine_oil/segmentor.py`
- `argus/domains/marine_oil/features.py`
- `argus/domains/marine_oil/detector.py` (refactor — replaces v0 internals)
- `tests/test_segmentor.py`, `tests/test_features.py`
- `tests/fixtures/sar_with_blob_and_noise.npy`

**Implementation:**
- Segmentation: Otsu/adaptive thresholding + morphological opening/closing
- Shape features: area_km2, perimeter_km, compactness, elongation, convexity, orientation
- Backscatter features: mean_sigma0_db, contrast_vs_background_db, texture_glcm
- Output: same `Observation[]` schema; adds populated `features` JSON

**Acceptance criteria:**
- On synthetic raster with planted blob + noise patches: primary blob detected; small noise patches rejected by min-area gate
- All required feature fields present in `Observation.features`
- Does not change `Domain` interface or store schema

---

## F-008 — Look-Alike Rejection + Confidence Score

**Why:** Dark patches in SAR include wind shadows, algae, ships, rain cells. Rejection
requires a trained classifier.

**Depends on:** F-007 (features extracted)

**Owns / creates:**
- `argus/domains/marine_oil/classifier.py`
- `models/oil_classifier_v1.pkl` (trained on synthetic + labeled data)
- `config/oil_classifier.yaml` (classifier hyperparams; threshold)
- `tests/test_classifier.py`
- `tests/fixtures/labeled_detections.json` (small labeled set for unit testing)

**Implementation:**
- Binary classifier: gradient boosted trees (scikit-learn GradientBoostingClassifier)
  on the feature vector from F-007
- Output: `confidence: float [0,1]`; update `Observation.confidence`
- Threshold in config; below-threshold → `status="dismissed"`
- `evidence_class` stays `"measured"` — the classifier scores confidence, not evidence class

**Acceptance criteria:**
- Clean-water fixture: no Observations with `status="confirmed"` above threshold
- Planted blob with all features: returns `confidence > 0.5`
- `Observation.status` transitions: candidate → confirmed or dismissed based on threshold

---

## F-009 — Eval Harness + Labeled Dataset + P/R Report

**Why:** Establish the framework for scoring detection quality; create the labeled baseline.

**Depends on:** F-008 (Observations include confidence)

**Owns / creates:**
- `argus/eval/__init__.py`
- `argus/eval/harness.py` (run an EvalCase; call domain pipeline; collect Observations)
- `argus/eval/scorer.py` (match detections to truth; compute P, R, F1 at threshold)
- `argus/core/store.py` (add `EvalCase`, `SkillReport` CRUD — scaffold only)
- `data/eval/tobago_2024.json` (verify/extend; add truth polygon if not present)
- `tests/test_eval_harness.py`

**Acceptance criteria:**
- `harness.run(eval_case)` returns `EvalResult` with P/R metrics
- On tobago_2024 (fixture mode): at least one True Positive if truth polygon overlaps fixture blob
- `SkillReport` scaffold created (not yet gating UI; that is F-029)

---

## F-010 — Detection Characterization & Schema Finalization

**Why:** Freeze the `Observation` schema before Phase 2 consumers (predictors) depend on it.

**Depends on:** F-008

**Owns / creates:**
- `argus/core/models.py` (finalize `Observation`; freeze v2.0 schema)
- `argus/core/store.py` (finalize Observation CRUD; add status transition methods)
- `tests/test_observation_schema.py`

**Changes:**
- Confirm all `Observation` fields match DATA_MODELS.md exactly
- Add `status` transition: `candidate` → `confirmed` / `dismissed` with timestamp
- Add `obs_type` validation (only registered types allowed)
- Write a migration check: existing test DB can be re-created from the final schema

**Acceptance criteria:**
- A multi-detection `AnalysisRun` with mixed statuses (confirmed/dismissed) round-trips correctly
- `evidence_class` field present and validated (not nullable, must be in allowed enum)
- Schema matches DATA_MODELS.md `Observation` table exactly (field for field)

## Phase 1 Definition of Done

- [ ] F-007–F-010 acceptance criteria met
- [ ] P/R report exists for tobago_2024 (even if metrics are low — baseline established)
- [ ] `Observation` schema frozen; any future change requires store migration
- [ ] No v1.0 entity names anywhere in argus/ code
