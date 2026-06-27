"""F-013 tests: ForecastFrame persistence, trajectory evaluator, SkillReport store."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from argus.core.models import ForecastFrame, Prediction
from argus.core.store import Store
from argus.predict.oil_trajectory.evaluator import (
    TrajectoryEvalCase,
    TrajectorySkillResult,
    _frame_centroid,
    _haversine_km,
    evaluate_trajectory,
    skill_result_to_store_report,
)

_REPO_ROOT = Path(__file__).parent.parent
_TOBAGO_TRAJ_CASE = _REPO_ROOT / "data" / "eval" / "tobago_2024_trajectory.json"

_BBOX_GEOM = {
    "type": "Polygon",
    "coordinates": [[[-61.4, 11.0], [-61.1, 11.0], [-61.1, 11.3], [-61.4, 11.3], [-61.4, 11.0]]],
}


def _make_prediction(pred_id: str = "pred-001") -> Prediction:
    return Prediction(
        id=pred_id,
        predictor_id="oil_trajectory_v1",
        source_obs_ids=["obs-001"],
        kind="trajectory",
        evidence_class="modeled",
        uncertainty={"particle_spread_km": 18.0, "n_particles": 1000},
        rng_seed=42,
    )


def _make_frame(
    pred_id: str = "pred-001",
    frame_id: str | None = None,
    valid_at: datetime | None = None,
    mean_lon: float = -61.2,
    mean_lat: float = 11.1,
) -> ForecastFrame:
    return ForecastFrame(
        id=frame_id or str(uuid.uuid4()),
        prediction_id=pred_id,
        valid_at=valid_at or datetime(2024, 2, 8, 0, 0, tzinfo=UTC),
        footprint=_BBOX_GEOM,
        particle_count=1000,
        stats={"mean_lon": mean_lon, "mean_lat": mean_lat},
    )


# ── TrajectoryEvalCase.from_json ──────────────────────────────────────────────


def test_trajectory_eval_case_loads_id() -> None:
    case = TrajectoryEvalCase.from_json(_TOBAGO_TRAJ_CASE)
    assert case.id == "tobago_2024_trajectory"


def test_trajectory_eval_case_loads_oil_type() -> None:
    case = TrajectoryEvalCase.from_json(_TOBAGO_TRAJ_CASE)
    assert case.oil_type == "crude_medium"


def test_trajectory_eval_case_loads_rng_seed() -> None:
    case = TrajectoryEvalCase.from_json(_TOBAGO_TRAJ_CASE)
    assert case.rng_seed == 42


def test_trajectory_eval_case_loads_truth_centroid() -> None:
    case = TrajectoryEvalCase.from_json(_TOBAGO_TRAJ_CASE)
    assert len(case.truth_centroid) == 2
    assert -62.0 < case.truth_centroid[0] < -60.0  # lon in range
    assert 10.0 < case.truth_centroid[1] < 12.0  # lat in range


def test_trajectory_eval_case_horizon_hours() -> None:
    case = TrajectoryEvalCase.from_json(_TOBAGO_TRAJ_CASE)
    assert case.horizon_hours == 24


# ── Prediction: uncertainty and rng_seed required ─────────────────────────────


def test_prediction_uncertainty_non_empty() -> None:
    pred = _make_prediction()
    assert len(pred.uncertainty) > 0


def test_prediction_rng_seed_matches_case() -> None:
    case = TrajectoryEvalCase.from_json(_TOBAGO_TRAJ_CASE)
    pred = _make_prediction()
    assert pred.rng_seed == case.rng_seed


def test_prediction_evidence_class_modeled() -> None:
    pred = _make_prediction()
    assert pred.evidence_class == "modeled"


# ── ForecastFrame persistence ─────────────────────────────────────────────────


def test_forecast_frames_persisted_and_retrieved(tmp_path: Path) -> None:
    store = Store(tmp_path / "argus.db")
    pred = _make_prediction()
    store.save_prediction(pred)
    frames = [_make_frame(pred_id=pred.id, frame_id=str(i)) for i in range(3)]
    for f in frames:
        store.save_forecast_frame(f)
    retrieved = store.get_forecast_frames_for_prediction(pred.id)
    assert len(retrieved) == 3


def test_forecast_frame_footprint_round_trip(tmp_path: Path) -> None:
    store = Store(tmp_path / "argus.db")
    pred = _make_prediction()
    store.save_prediction(pred)
    frame = _make_frame(pred_id=pred.id)
    store.save_forecast_frame(frame)
    retrieved = store.get_forecast_frames_for_prediction(pred.id)
    assert retrieved[0].footprint["type"] == "Polygon"


def test_forecast_frame_stats_round_trip(tmp_path: Path) -> None:
    store = Store(tmp_path / "argus.db")
    pred = _make_prediction()
    store.save_prediction(pred)
    frame = _make_frame(pred_id=pred.id, mean_lon=-61.3, mean_lat=11.2)
    store.save_forecast_frame(frame)
    retrieved = store.get_forecast_frames_for_prediction(pred.id)
    assert retrieved[0].stats["mean_lon"] == pytest.approx(-61.3)


def test_forecast_frame_valid_at_round_trip(tmp_path: Path) -> None:
    ts = datetime(2024, 2, 8, 0, 0, tzinfo=UTC)
    store = Store(tmp_path / "argus.db")
    pred = _make_prediction()
    store.save_prediction(pred)
    frame = _make_frame(pred_id=pred.id, valid_at=ts)
    store.save_forecast_frame(frame)
    retrieved = store.get_forecast_frames_for_prediction(pred.id)
    assert retrieved[0].valid_at.replace(tzinfo=UTC) == ts


# ── haversine distance ────────────────────────────────────────────────────────


def test_haversine_same_point() -> None:
    assert _haversine_km(-61.0, 11.0, -61.0, 11.0) == pytest.approx(0.0)


def test_haversine_known_distance() -> None:
    d = _haversine_km(0.0, 0.0, 1.0, 0.0)
    assert d == pytest.approx(111.19, abs=0.5)


# ── _frame_centroid ───────────────────────────────────────────────────────────


def test_frame_centroid_uses_stats() -> None:
    frame = _make_frame(mean_lon=-61.2, mean_lat=11.1)
    lon, lat = _frame_centroid(frame)
    assert lon == pytest.approx(-61.2)
    assert lat == pytest.approx(11.1)


def test_frame_centroid_falls_back_to_polygon() -> None:
    frame = ForecastFrame(
        id="fc-1",
        prediction_id="p-1",
        valid_at=datetime(2024, 2, 7, tzinfo=UTC),
        footprint={
            "type": "Polygon",
            "coordinates": [[[-61.0, 11.0], [-60.0, 11.0], [-60.0, 12.0], [-61.0, 12.0]]],
        },
        stats={},  # no mean_lon/mean_lat
    )
    lon, lat = _frame_centroid(frame)
    assert -61.5 < lon < -59.5
    assert 10.5 < lat < 12.5


# ── evaluate_trajectory ───────────────────────────────────────────────────────


def test_evaluate_trajectory_returns_result() -> None:
    case = TrajectoryEvalCase.from_json(_TOBAGO_TRAJ_CASE)
    frames = [_make_frame()]
    result = evaluate_trajectory(case, frames)
    assert isinstance(result, TrajectorySkillResult)


def test_evaluate_trajectory_separation_km_non_negative() -> None:
    case = TrajectoryEvalCase.from_json(_TOBAGO_TRAJ_CASE)
    frames = [_make_frame()]
    result = evaluate_trajectory(case, frames)
    assert result.separation_km >= 0.0


def test_evaluate_trajectory_n_frames_correct() -> None:
    case = TrajectoryEvalCase.from_json(_TOBAGO_TRAJ_CASE)
    frames = [_make_frame() for _ in range(5)]
    result = evaluate_trajectory(case, frames)
    assert result.n_frames == 5


def test_evaluate_trajectory_zero_separation_for_exact_match() -> None:
    case = TrajectoryEvalCase.from_json(_TOBAGO_TRAJ_CASE)
    lon, lat = case.truth_centroid[0], case.truth_centroid[1]
    frames = [_make_frame(mean_lon=lon, mean_lat=lat)]
    result = evaluate_trajectory(case, frames)
    assert result.separation_km == pytest.approx(0.0, abs=0.1)


def test_evaluate_trajectory_empty_frames_graceful() -> None:
    case = TrajectoryEvalCase.from_json(_TOBAGO_TRAJ_CASE)
    result = evaluate_trajectory(case, [])
    assert result.n_frames == 0
    assert result.separation_km >= 0.0


# ── skill_result_to_store_report ──────────────────────────────────────────────


def test_skill_result_to_store_report_keys() -> None:
    case = TrajectoryEvalCase.from_json(_TOBAGO_TRAJ_CASE)
    frames = [_make_frame()]
    result = evaluate_trajectory(case, frames)
    report = skill_result_to_store_report(result)
    for key in (
        "report_id",
        "predictor_id",
        "eval_case_id",
        "precision",
        "recall",
        "f1",
        "n_observations",
        "created_at",
    ):
        assert key in report


def test_skill_result_stored_in_store(tmp_path: Path) -> None:
    store = Store(tmp_path / "argus.db")
    case = TrajectoryEvalCase.from_json(_TOBAGO_TRAJ_CASE)
    frames = [_make_frame()]
    result = evaluate_trajectory(case, frames)
    report = skill_result_to_store_report(result)
    store.save_skill_report(**report)
    reports = store.get_skill_reports_for_case(case.id)
    assert len(reports) == 1
    assert reports[0]["predictor_id"] == "oil_trajectory_v1"
