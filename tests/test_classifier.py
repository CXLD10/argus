"""F-008 tests: look-alike rejection classifier."""

from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np
import pytest
from sklearn.ensemble import GradientBoostingClassifier

from argus.core.models import Observation
from argus.domains.marine_oil.classifier import (
    _FEATURE_ORDER,
    OilClassifier,
    _build_feature_matrix,
    train_classifier,
)

_FIXTURE = Path(__file__).parent / "fixtures" / "labeled_detections.json"
_THRESHOLD = 0.5


def _make_observation(features: dict, *, status: str = "candidate") -> Observation:
    return Observation(
        id="test-obs",
        analysis_run_id="test-run",
        scene_id="test-scene",
        obs_type="oil_slick",
        evidence_class="measured",
        geometry={"type": "Point", "coordinates": [-61.0, 11.0]},
        area_km2=features.get("area_km2", 1.0),
        confidence=0.5,
        status=status,  # type: ignore[arg-type]
        attrs={"features": features},
    )


_OIL_FEATURES = {
    "area_km2": 100.0,
    "perimeter_km": 60.0,
    "compactness": 0.35,
    "elongation": 3.0,
    "convexity": 0.65,
    "orientation": 45.0,
    "mean_sigma0_db": -28.0,
    "contrast_vs_background_db": 14.0,
    "texture_glcm": 0.03,
}

_LOOKALIKE_FEATURES = {
    "area_km2": 5.0,
    "perimeter_km": 10.0,
    "compactness": 0.70,
    "elongation": 1.2,
    "convexity": 0.92,
    "orientation": 10.0,
    "mean_sigma0_db": -17.0,
    "contrast_vs_background_db": 3.0,
    "texture_glcm": 0.20,
}


@pytest.fixture(scope="module")
def trained_model() -> GradientBoostingClassifier:
    samples = json.loads(_FIXTURE.read_text())
    return train_classifier(samples, n_estimators=50, random_state=42)


@pytest.fixture(scope="module")
def classifier(trained_model: GradientBoostingClassifier) -> OilClassifier:
    return OilClassifier(model=trained_model, threshold=_THRESHOLD)


# ── train_classifier ──────────────────────────────────────────────────────────


def test_train_classifier_returns_gbt(trained_model: GradientBoostingClassifier) -> None:
    assert isinstance(trained_model, GradientBoostingClassifier)


def test_train_classifier_fitted(trained_model: GradientBoostingClassifier) -> None:
    assert hasattr(trained_model, "classes_")
    assert 0 in trained_model.classes_ and 1 in trained_model.classes_


def test_train_classifier_reproducible() -> None:
    """INV-8: same seed → identical model predictions."""
    samples = json.loads(_FIXTURE.read_text())
    m1 = train_classifier(samples, random_state=42)
    m2 = train_classifier(samples, random_state=42)
    x = np.array([[s["features"][k] for k in _FEATURE_ORDER] for s in samples[:5]])
    np.testing.assert_array_equal(m1.predict_proba(x), m2.predict_proba(x))


# ── OilClassifier.classify ────────────────────────────────────────────────────


def test_classify_empty_returns_empty(classifier: OilClassifier) -> None:
    assert classifier.classify([]) == []


def test_classify_oil_returns_confirmed(classifier: OilClassifier) -> None:
    obs = _make_observation(_OIL_FEATURES)
    result = classifier.classify([obs])
    assert result[0].status == "confirmed"


def test_classify_lookalike_returns_dismissed(classifier: OilClassifier) -> None:
    obs = _make_observation(_LOOKALIKE_FEATURES)
    result = classifier.classify([obs])
    assert result[0].status == "dismissed"


def test_classify_oil_confidence_above_half(classifier: OilClassifier) -> None:
    obs = _make_observation(_OIL_FEATURES)
    result = classifier.classify([obs])
    assert result[0].confidence > 0.5


def test_classify_evidence_class_unchanged(classifier: OilClassifier) -> None:
    """INV-3: classifier must not change evidence_class."""
    obs = _make_observation(_OIL_FEATURES)
    result = classifier.classify([obs])
    assert result[0].evidence_class == "measured"


def test_classify_returns_new_instances(classifier: OilClassifier) -> None:
    obs = _make_observation(_OIL_FEATURES)
    result = classifier.classify([obs])
    assert result[0] is not obs


def test_classify_result_count_matches_input(classifier: OilClassifier) -> None:
    obs_list = [_make_observation(_OIL_FEATURES), _make_observation(_LOOKALIKE_FEATURES)]
    result = classifier.classify(obs_list)
    assert len(result) == 2


def test_classify_clean_water_no_confirmed() -> None:
    """Acceptance criterion: clean-water observations must not be confirmed."""
    samples = json.loads(_FIXTURE.read_text())
    clf = OilClassifier(model=train_classifier(samples, random_state=42), threshold=_THRESHOLD)
    clean_water = _make_observation(_LOOKALIKE_FEATURES)
    result = clf.classify([clean_water])
    assert result[0].status != "confirmed"


# ── _build_feature_matrix ─────────────────────────────────────────────────────


def test_feature_matrix_shape() -> None:
    obs = _make_observation(_OIL_FEATURES)
    x = _build_feature_matrix([obs])
    assert x.shape == (1, len(_FEATURE_ORDER))


def test_feature_matrix_missing_key_defaults_zero() -> None:
    obs = _make_observation({})  # no features
    x = _build_feature_matrix([obs])
    assert np.all(x == 0.0)


# ── load_classifier integration ───────────────────────────────────────────────


def test_load_classifier_from_pickle(
    tmp_path: Path, trained_model: GradientBoostingClassifier
) -> None:
    pkl_path = tmp_path / "model.pkl"
    with pkl_path.open("wb") as fh:
        pickle.dump(trained_model, fh)

    config_path = tmp_path / "clf.yaml"
    config_path.write_text(f"model_path: {pkl_path}\nthreshold: 0.5\n")

    from argus.domains.marine_oil.classifier import load_classifier

    loaded = load_classifier(config_path)
    assert isinstance(loaded, OilClassifier)
    assert loaded.threshold == 0.5
