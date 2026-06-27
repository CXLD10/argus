"""Trajectory evaluator — measures skill of OilTrajectory predictor.

Skill metric: great-circle distance (km) between predicted centroid at T+24h
and truth centroid from the eval case. Stored as a SkillReport in the store.
"""

from __future__ import annotations

import json
import math
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from argus.core.models import ForecastFrame


@dataclass
class TrajectoryEvalCase:
    """Trajectory-specific eval case with T+horizon truth centroid."""

    id: str
    domain: str
    oil_type: str
    event_name: str
    refs: dict[str, Any]
    event_time: str
    truth_geometry: dict[str, Any]
    truth_centroid: list[float]  # [lon, lat]
    provenance: str
    rng_seed: int
    horizon_hours: int = 24

    @classmethod
    def from_json(cls, path: Path) -> TrajectoryEvalCase:
        data = json.loads(path.read_text())
        return cls(**data)


@dataclass
class TrajectorySkillResult:
    """Outcome of one trajectory evaluation run."""

    eval_case_id: str
    predictor_id: str
    rng_seed: int
    horizon_hours: int
    predicted_centroid: tuple[float, float]  # (lon, lat) of last frame
    truth_centroid: tuple[float, float]
    separation_km: float
    n_frames: int
    created_at: datetime


def _haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Great-circle distance between two points (degrees) in km."""
    r = 6371.0
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    return r * 2 * math.asin(math.sqrt(a))


def _frame_centroid(frame: ForecastFrame) -> tuple[float, float]:
    """Extract (lon, lat) centroid from a ForecastFrame footprint."""
    stats = frame.stats
    if "mean_lon" in stats and "mean_lat" in stats:
        return float(stats["mean_lon"]), float(stats["mean_lat"])
    coords = frame.footprint.get("coordinates", [[]])[0]
    if not coords:
        return 0.0, 0.0
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return sum(lons) / len(lons), sum(lats) / len(lats)


def evaluate_trajectory(
    eval_case: TrajectoryEvalCase,
    frames: list[ForecastFrame],
    *,
    predictor_id: str = "oil_trajectory_v1",
) -> TrajectorySkillResult:
    """Compute the separation between the last predicted frame centroid and the truth.

    Uses the final ForecastFrame as the T+horizon prediction.
    Returns a TrajectorySkillResult; caller is responsible for persisting to store.
    """
    if not frames:
        pred_centroid = (0.0, 0.0)
        sep_km = _haversine_km(*pred_centroid, *eval_case.truth_centroid)
    else:
        pred_centroid = _frame_centroid(frames[-1])
        sep_km = _haversine_km(*pred_centroid, *eval_case.truth_centroid)

    truth = (float(eval_case.truth_centroid[0]), float(eval_case.truth_centroid[1]))

    return TrajectorySkillResult(
        eval_case_id=eval_case.id,
        predictor_id=predictor_id,
        rng_seed=eval_case.rng_seed,
        horizon_hours=eval_case.horizon_hours,
        predicted_centroid=pred_centroid,
        truth_centroid=truth,
        separation_km=round(sep_km, 2),
        n_frames=len(frames),
        created_at=datetime.now(UTC),
    )


def skill_result_to_store_report(result: TrajectorySkillResult) -> dict[str, Any]:
    """Convert a TrajectorySkillResult to keyword arguments for Store.save_skill_report()."""
    f1_proxy = max(0.0, 1.0 - result.separation_km / 100.0)  # 0 km → 1.0; 100+ km → 0.0
    return {
        "report_id": str(uuid.uuid4()),
        "predictor_id": result.predictor_id,
        "eval_case_id": result.eval_case_id,
        "precision": round(f1_proxy, 4),
        "recall": round(f1_proxy, 4),
        "f1": round(f1_proxy, 4),
        "n_observations": result.n_frames,
        "created_at": result.created_at,
    }
