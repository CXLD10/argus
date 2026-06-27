"""Detection scorer: match Observations to a truth geometry, compute P/R/F1."""

from __future__ import annotations

from dataclasses import dataclass

from shapely.geometry import shape

from argus.core.models import Observation


@dataclass
class EvalResult:
    """Detection quality metrics for one EvalCase run."""

    eval_case_id: str
    n_observations: int
    n_confirmed: int
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1: float


def score(
    eval_case_id: str,
    observations: list[Observation],
    truth_geometry: dict,
    *,
    min_confidence: float = 0.5,
) -> EvalResult:
    """Score detections against a single GeoJSON truth polygon.

    An Observation counts as active if confidence >= min_confidence.
    TP: active Observation whose geometry intersects the truth polygon.
    FP: active Observation that does not intersect the truth polygon.
    FN: 1 if the truth polygon is not covered by any TP, else 0.
    """
    truth_geom = shape(truth_geometry)
    active = [o for o in observations if o.confidence >= min_confidence]

    tp = sum(1 for o in active if shape(o.geometry).intersects(truth_geom))
    fp = len(active) - tp
    fn = 0 if tp > 0 else 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return EvalResult(
        eval_case_id=eval_case_id,
        n_observations=len(observations),
        n_confirmed=len(active),
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1=round(f1, 4),
    )
