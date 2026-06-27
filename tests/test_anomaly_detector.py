"""F-027 tests: SeasonalBaseline + AnomalyDetector."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from argus.core.models import Observation, Prediction
from argus.predict.anomaly_detector import AnomalyDetector, SeasonalBaseline, build_baseline
from argus.predict.base import PredictContext

# ── Helpers ────────────────────────────────────────────────────────────────────

_GEOMETRY = {"type": "Point", "coordinates": [0.0, 0.0]}


def _make_obs(
    value: float,
    obs_type: str = "chlorophyll_a",
    days_offset: int = 0,
    iso_week: int | None = None,
) -> Observation:
    """Create a synthetic Observation with controlled created_at."""
    if iso_week is not None:
        # Pin to a Monday in the given ISO week of 2023
        jan4 = datetime(2023, 1, 4, tzinfo=UTC)  # always in week 1
        week1_monday = jan4 - timedelta(days=jan4.isocalendar().weekday - 1)
        created_at = week1_monday + timedelta(weeks=iso_week - 1, days=days_offset)
    else:
        created_at = datetime(2024, 6, 1, tzinfo=UTC) + timedelta(days=days_offset)
    return Observation(
        id=str(uuid.uuid4()),
        analysis_run_id="run_test",
        scene_id="scene_test",
        obs_type=obs_type,
        evidence_class="measured",
        geometry=_GEOMETRY,
        area_km2=0.0,
        confidence=0.8,
        value=value,
        unit="ndci_index",
        domain="inland_wq",
        target_id="target_test",
        created_at=created_at,
    )


def _make_stable_history(
    weeks: int = 52,
    n_per_week: int = 6,
    mean: float = 0.05,
    std: float = 0.01,
) -> list[Observation]:
    """Generate synthetic weekly Observations around a stable mean.

    n_per_week ≥ 6 gives a stable sample std so that baseline z-scores are reliable.
    Fixed RNG seed for reproducibility (INV-8).
    """
    import random

    rng = random.Random(42)
    history = []
    for w in range(1, min(weeks, 52) + 1):
        for i in range(n_per_week):
            v = mean + rng.gauss(0, std)
            history.append(_make_obs(value=v, iso_week=w, days_offset=i * 14))
    return history


def _make_ctx(obs: list[Observation], aoi_id: str = "test_aoi") -> PredictContext:
    return PredictContext(
        obs=obs,
        aoi_id=aoi_id,
        t0=datetime(2024, 6, 1, tzinfo=UTC),
        t1=datetime(2024, 6, 7, tzinfo=UTC),
        attrs={},
    )


# ── SeasonalBaseline ──────────────────────────────────────────────────────────


def test_build_baseline_returns_seasonal_baseline() -> None:
    history = _make_stable_history(weeks=10)
    baseline = build_baseline(history)
    assert isinstance(baseline, SeasonalBaseline)


def test_build_baseline_obs_type_set() -> None:
    history = _make_stable_history(weeks=10)
    baseline = build_baseline(history, obs_type="turbidity")
    assert baseline.obs_type == "turbidity"


def test_build_baseline_weekly_stats_populated() -> None:
    history = _make_stable_history(weeks=10)
    baseline = build_baseline(history)
    assert len(baseline.weekly_stats) > 0


def test_build_baseline_ignores_wrong_obs_type() -> None:
    obs = [_make_obs(value=0.1, obs_type="turbidity", iso_week=1)]
    baseline = build_baseline(obs, obs_type="chlorophyll_a")
    assert baseline.weekly_stats == {}


def test_build_baseline_mean_std_unknown_week_returns_none() -> None:
    history = _make_stable_history(weeks=5)  # only weeks 1–5
    baseline = build_baseline(history)
    mean, std = baseline.mean_std(40)  # week 40 has no data
    assert mean is None and std is None


def test_build_baseline_single_obs_std_is_zero() -> None:
    obs = [_make_obs(value=0.1, iso_week=10)]
    baseline = build_baseline(obs)
    _, std = baseline.mean_std(10)
    assert std == 0.0


# ── AnomalyDetector ───────────────────────────────────────────────────────────


def test_anomaly_detector_predict_before_fit_raises() -> None:
    detector = AnomalyDetector()
    obs = [_make_obs(value=0.5)]
    with pytest.raises(RuntimeError, match="fit"):
        detector.predict(_make_ctx(obs), rng_seed=42)


def test_anomaly_detector_predictor_id() -> None:
    assert AnomalyDetector.predictor_id == "anomaly_detector_wq"


def test_anomaly_detector_stable_series_no_anomaly() -> None:
    """AC2: Stable time series (no spikes) must not produce an anomaly."""
    history = _make_stable_history(weeks=52, mean=0.05, std=0.01)
    detector = AnomalyDetector(threshold_sigma=2.5)
    detector.fit(history)

    # A normal observation in week 10
    week_10_obs = _make_obs(value=0.051, iso_week=10)
    ctx = _make_ctx([week_10_obs])
    pred = detector.predict(ctx, rng_seed=42)

    assert pred.attrs["anomaly_detected"] is False


def test_anomaly_detector_spike_triggers_anomaly() -> None:
    """AC1: Planted spike in stable baseline must be flagged as anomaly."""
    history = _make_stable_history(weeks=52, mean=0.05, std=0.005)
    detector = AnomalyDetector(threshold_sigma=2.5)
    detector.fit(history)

    # 10× spike far above normal range (z-score >> 2.5)
    spike_obs = _make_obs(value=0.5, iso_week=10)
    ctx = _make_ctx([spike_obs])
    pred = detector.predict(ctx, rng_seed=42)

    assert pred.attrs["anomaly_detected"] is True


def test_anomaly_detector_prediction_kind_is_anomaly() -> None:
    history = _make_stable_history()
    detector = AnomalyDetector()
    detector.fit(history)
    pred = detector.predict(_make_ctx([_make_obs(value=0.05, iso_week=5)]), rng_seed=0)
    assert pred.kind == "anomaly"


def test_anomaly_detector_evidence_class_is_modeled() -> None:
    history = _make_stable_history()
    detector = AnomalyDetector()
    detector.fit(history)
    pred = detector.predict(_make_ctx([_make_obs(value=0.05, iso_week=5)]), rng_seed=0)
    assert pred.evidence_class == "modeled"


def test_anomaly_detector_uncertainty_non_null() -> None:
    """AC3: Prediction.uncertainty must be non-null and contain sigma value."""
    history = _make_stable_history()
    detector = AnomalyDetector()
    detector.fit(history)
    pred = detector.predict(_make_ctx([_make_obs(value=0.05, iso_week=5)]), rng_seed=0)
    assert pred.uncertainty is not None
    assert "sigma" in pred.uncertainty


def test_anomaly_detector_uncertainty_sigma_matches_z_score() -> None:
    history = _make_stable_history()
    detector = AnomalyDetector()
    detector.fit(history)
    pred = detector.predict(_make_ctx([_make_obs(value=0.05, iso_week=5)]), rng_seed=0)
    assert pred.uncertainty["sigma"] == pytest.approx(pred.attrs["z_score"])


def test_anomaly_detector_empty_obs_returns_prediction() -> None:
    """Empty PredictContext.obs returns a no-data Prediction (not a crash)."""
    history = _make_stable_history()
    detector = AnomalyDetector()
    detector.fit(history)
    pred = detector.predict(_make_ctx([]), rng_seed=0)
    assert isinstance(pred, Prediction)
    assert pred.attrs["anomaly_detected"] is False


def test_anomaly_detector_rng_seed_stored() -> None:
    history = _make_stable_history()
    detector = AnomalyDetector()
    detector.fit(history)
    pred = detector.predict(_make_ctx([_make_obs(value=0.05, iso_week=5)]), rng_seed=77)
    assert pred.rng_seed == 77


# ── validate() ────────────────────────────────────────────────────────────────


def test_anomaly_detector_validate_empty_history() -> None:
    history = _make_stable_history()
    detector = AnomalyDetector()
    detector.fit(history)
    result = detector.validate([])
    assert result["false_alarm_rate"] == 0.0
    assert result["passed_gate"] is False


def test_anomaly_detector_validate_low_false_alarm_rate_passes_gate() -> None:
    """False alarm rate < 10% should set passed_gate = True."""
    history = _make_stable_history(weeks=52, mean=0.05, std=0.005)
    detector = AnomalyDetector(threshold_sigma=2.5)
    detector.fit(history)

    # Eval set: all normal observations (truth_anomaly=False) with near-baseline values
    eval_set = [
        {"obs": _make_obs(value=0.051, iso_week=w), "truth_anomaly": False}
        for w in range(1, 20)
    ]
    result = detector.validate(eval_set)
    assert result["false_alarm_rate"] < 0.10
    assert result["passed_gate"] is True


def test_anomaly_detector_validate_high_false_alarm_rate_fails_gate() -> None:
    """If every normal observation is flagged, false_alarm_rate = 1.0, gate fails."""
    # Baseline built on very low values; "normal" eval obs are extreme → all flagged
    tiny_history = [_make_obs(value=0.001, iso_week=w) for w in range(1, 10)]
    # Add a second obs per week to have std > 0
    tiny_history += [_make_obs(value=0.002, iso_week=w, days_offset=7) for w in range(1, 10)]
    detector = AnomalyDetector(threshold_sigma=0.1)  # ultra-sensitive
    detector.fit(tiny_history)

    eval_set = [
        {"obs": _make_obs(value=1.0, iso_week=w), "truth_anomaly": False}
        for w in range(1, 5)
    ]
    result = detector.validate(eval_set)
    assert result["passed_gate"] is False


# ── Store integration ─────────────────────────────────────────────────────────


def test_store_get_predictions_by_kind_anomaly(tmp_store) -> None:
    """save_prediction + get_predictions_by_kind round-trip for kind='anomaly'."""
    history = _make_stable_history()
    detector = AnomalyDetector()
    detector.fit(history)
    pred = detector.predict(_make_ctx([_make_obs(value=0.5, iso_week=5)]), rng_seed=42)

    tmp_store.save_prediction(pred)
    results = tmp_store.get_predictions_by_kind("anomaly")
    assert len(results) == 1
    assert results[0].id == pred.id
    assert results[0].kind == "anomaly"


def test_store_get_predictions_by_kind_excludes_other_kinds(tmp_store) -> None:
    """get_predictions_by_kind('anomaly') should not return trajectory predictions."""
    trajectory_pred = Prediction(
        id=str(uuid.uuid4()),
        predictor_id="oil_trajectory",
        kind="trajectory",
        evidence_class="modeled",
        uncertainty={"ensemble_spread_km": 5.0},
        rng_seed=42,
    )
    tmp_store.save_prediction(trajectory_pred)
    results = tmp_store.get_predictions_by_kind("anomaly")
    assert len(results) == 0
