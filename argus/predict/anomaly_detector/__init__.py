"""Inland water quality anomaly detector (Phase 5 / F-027)."""

from argus.predict.anomaly_detector.baseline import SeasonalBaseline, build_baseline
from argus.predict.anomaly_detector.detector import AnomalyDetector

__all__ = ["AnomalyDetector", "SeasonalBaseline", "build_baseline"]
