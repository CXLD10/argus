"""Eval harness: run EvalCase through the detection pipeline, return EvalResult."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from argus.domains.base import Acquisition
from argus.domains.marine_oil.classifier import OilClassifier, train_classifier
from argus.domains.marine_oil.detector import MarineOilDomain, make_analysis_run
from argus.eval.scorer import EvalResult, score
from argus.preprocess.landmask import GeoTransform
from argus.preprocess.sar import preprocess

_FIXTURE_ROWS = 100
_FIXTURE_COLS = 100
_BLOB_ROW_SLICE = slice(40, 60)  # planted dark blob: overlaps tobago truth polygon
_BLOB_COL_SLICE = slice(20, 40)


@dataclass
class EvalCase:
    """A single evaluation case loaded from a JSON file."""

    id: str
    domain: str
    oil_type: str
    event_name: str
    refs: dict[str, Any]
    event_time: str
    truth_geometry: dict[str, Any]
    provenance: str

    @classmethod
    def from_json(cls, path: Path) -> EvalCase:
        data = json.loads(path.read_text())
        return cls(**data)


@dataclass
class SkillReport:
    """Scaffold for predictor skill metrics (not yet gating UI; see F-029)."""

    predictor_id: str
    eval_case_id: str
    precision: float
    recall: float
    f1: float
    n_observations: int
    created_at: datetime = field(default_factory=datetime.now)


def run(
    eval_case: EvalCase,
    *,
    labeled_samples: list[dict[str, Any]] | None = None,
    fixture_mode: bool = True,
) -> EvalResult:
    """Run the detection pipeline on *eval_case* and return P/R/F1 metrics.

    In fixture mode (default): generates a synthetic SAR with a planted dark blob
    positioned to overlap the eval_case truth polygon; no network calls.
    In live mode: raises NotImplementedError (requires CDSE — Phase 2+).

    *labeled_samples* is used to train the classifier inline. If None, a default
    synthetic sample set is used so the harness can run without external files.
    """
    if not fixture_mode:
        raise NotImplementedError("Live eval mode requires CDSE access; use fixture_mode=True")

    bbox = eval_case.refs["bbox"]  # [min_lon, min_lat, max_lon, max_lat]
    transform = GeoTransform(
        min_lon=bbox[0],
        min_lat=bbox[1],
        max_lon=bbox[2],
        max_lat=bbox[3],
        cols=_FIXTURE_COLS,
        rows=_FIXTURE_ROWS,
    )

    vv_linear, vh_linear = _synthetic_sar(transform)
    land_mask = np.zeros((_FIXTURE_ROWS, _FIXTURE_COLS), dtype=bool)
    scene_id = f"eval-fixture-{eval_case.id}"
    prep = preprocess(vv_linear, vh_linear, land_mask, transform, scene_id)

    run_obj = make_analysis_run(eval_case.id, scene_id)
    acq = Acquisition(
        scene_id=scene_id,
        source_ref=None,  # type: ignore[arg-type]
        preprocessed=prep,
        attrs={"analysis_run_id": run_obj.id},
    )
    observations = MarineOilDomain().analyze(acq)

    classifier = _build_classifier(labeled_samples)
    classified = classifier.classify(observations)

    return score(eval_case.id, classified, eval_case.truth_geometry)


def _synthetic_sar(transform: GeoTransform) -> tuple[np.ndarray, np.ndarray]:
    """Generate a synthetic SAR with a dark blob positioned inside the truth region."""
    rng = np.random.default_rng(42)
    vv = rng.uniform(5e-4, 2e-3, (_FIXTURE_ROWS, _FIXTURE_COLS)).astype(np.float32)
    vh = rng.uniform(5e-5, 2e-4, (_FIXTURE_ROWS, _FIXTURE_COLS)).astype(np.float32)
    vv[_BLOB_ROW_SLICE, _BLOB_COL_SLICE] = 5e-6
    vh[_BLOB_ROW_SLICE, _BLOB_COL_SLICE] = 5e-7
    return vv, vh


def _build_classifier(labeled_samples: list[dict[str, Any]] | None) -> OilClassifier:
    """Return a classifier trained on *labeled_samples* or a minimal inline set."""
    if labeled_samples is not None:
        model = train_classifier(labeled_samples)
        return OilClassifier(model=model, threshold=0.5)

    # Inline fallback: high-contrast feature → oil; low-contrast → lookalike
    minimal: list[dict[str, Any]] = [
        *[
            {
                "label": 1,
                "features": {
                    "area_km2": 80.0 + i * 10,
                    "perimeter_km": 45.0,
                    "compactness": 0.45,
                    "elongation": 2.5,
                    "convexity": 0.72,
                    "orientation": 45.0,
                    "mean_sigma0_db": -28.0,
                    "contrast_vs_background_db": 14.0 + i,
                    "texture_glcm": 0.03,
                },
            }
            for i in range(10)
        ],
        *[
            {
                "label": 0,
                "features": {
                    "area_km2": 5.0 + i,
                    "perimeter_km": 10.0,
                    "compactness": 0.72,
                    "elongation": 1.2,
                    "convexity": 0.92,
                    "orientation": 10.0,
                    "mean_sigma0_db": -17.0,
                    "contrast_vs_background_db": 3.0 + i * 0.2,
                    "texture_glcm": 0.20,
                },
            }
            for i in range(10)
        ],
    ]
    model = train_classifier(minimal)
    return OilClassifier(model=model, threshold=0.5)
