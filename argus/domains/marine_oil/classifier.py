"""Look-alike rejection classifier for SAR dark-spot candidates.

Uses a GradientBoostingClassifier trained on shape and backscatter features
from F-007. Updates Observation.confidence and Observation.status (INV-8: seed=42).
"""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from sklearn.ensemble import GradientBoostingClassifier

from argus.core.models import Observation

_DEFAULT_CONFIG = Path("config") / "oil_classifier.yaml"
_FEATURE_ORDER: list[str] = [
    "area_km2",
    "perimeter_km",
    "compactness",
    "elongation",
    "convexity",
    "orientation",
    "mean_sigma0_db",
    "contrast_vs_background_db",
    "texture_glcm",
]


class OilClassifier:
    """Wraps a trained GBT model; classifies Observations into confirmed/dismissed."""

    def __init__(self, model: GradientBoostingClassifier, threshold: float) -> None:
        self._model = model
        self.threshold = threshold

    def classify(self, observations: list[Observation]) -> list[Observation]:
        """Return new Observation instances with updated confidence and status.

        evidence_class is never changed — confidence is not evidence (INV-3).
        """
        if not observations:
            return []

        x = _build_feature_matrix(observations)
        probs: np.ndarray = self._model.predict_proba(x)[:, 1]

        result: list[Observation] = []
        for obs, prob in zip(observations, probs.tolist(), strict=True):
            status: str = "confirmed" if prob >= self.threshold else "dismissed"
            result.append(obs.model_copy(update={"confidence": round(prob, 4), "status": status}))
        return result


def load_classifier(config_path: Path = _DEFAULT_CONFIG) -> OilClassifier:
    """Load the trained classifier specified in *config_path*."""
    with config_path.open() as fh:
        cfg: dict[str, Any] = yaml.safe_load(fh)
    model_path = Path(cfg["model_path"])
    threshold = float(cfg["threshold"])
    with model_path.open("rb") as fh:
        model: GradientBoostingClassifier = pickle.load(fh)
    return OilClassifier(model=model, threshold=threshold)


def train_classifier(
    labeled_samples: list[dict[str, Any]],
    *,
    n_estimators: int = 50,
    random_state: int = 42,
) -> GradientBoostingClassifier:
    """Train a GBT classifier on labeled feature dicts.

    Each sample must have 'label' (int) and 'features' (dict matching _FEATURE_ORDER).
    random_state=42 ensures INV-8 (reproducibility).
    """
    x = np.array(
        [[float(s["features"].get(k, 0.0)) for k in _FEATURE_ORDER] for s in labeled_samples]
    )
    y = np.array([int(s["label"]) for s in labeled_samples])
    clf = GradientBoostingClassifier(n_estimators=n_estimators, random_state=random_state)
    clf.fit(x, y)
    return clf


def _build_feature_matrix(observations: list[Observation]) -> np.ndarray:
    return np.array(
        [
            [float(obs.attrs.get("features", {}).get(k, 0.0)) for k in _FEATURE_ORDER]
            for obs in observations
        ]
    )
