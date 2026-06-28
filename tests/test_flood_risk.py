"""Tests for F-042: FloodRisk predictor.

All tests are offline (INV-7).  Synthetic WeatherSeries Observations and
ChokePoint fixtures are used — no live data fetches.

Acceptance criteria:
  - High precip + high discharge → risk_level ∈ {"high", "extreme"}
  - evidence_class = "modeled" always (INV-3)
  - uncertainty is non-empty (INV-9)
  - SkillReport (validate()) generated from historical data
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from argus.core.models import ChokePoint, Observation, Prediction
from argus.predict.base import PredictContext
from argus.predict.flood_risk.evaluator import build_eval_set
from argus.predict.flood_risk.predictor import (
    FloodRiskPredictor,
    _compute_risk_score,
    _merge_thresholds,
    _peak_from_obs,
    _score_to_level,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_obs(obs_type: str, value: float | None) -> Observation:
    return Observation(
        id=str(uuid.uuid4()),
        analysis_run_id="ar1",
        scene_id="s1",
        obs_type=obs_type,
        evidence_class="modeled",
        geometry={"type": "Point", "coordinates": [-61.25, 11.25]},
        area_km2=0.0,
        confidence=1.0,
        value=value,
        unit="mm" if obs_type == "precip_series" else "m3/s",
        domain="weather_hydro",
    )


def _make_choke_point(constriction_score: float = 0.8) -> ChokePoint:
    return ChokePoint(
        id=str(uuid.uuid4()),
        aoi_id="tobago",
        location={"type": "Point", "coordinates": [-61.25, 11.25]},
        upstream_area_km2=5.0,
        constriction_score=constriction_score,
        dem_source="cop_glo30",
        evidence_class="inferred",
    )


def _make_ctx(
    precip_mm: float | None = None,
    discharge_m3s: float | None = None,
    choke_points: list[ChokePoint] | None = None,
    thresholds: dict | None = None,
) -> PredictContext:
    obs: list[Observation] = []
    if precip_mm is not None:
        obs.append(_make_obs("precip_series", precip_mm))
    if discharge_m3s is not None:
        obs.append(_make_obs("discharge_series", discharge_m3s))
    attrs: dict = {}
    if choke_points is not None:
        attrs["choke_points"] = choke_points
    if thresholds is not None:
        attrs["flood_risk_thresholds"] = thresholds
    return PredictContext(
        obs=obs,
        aoi_id="tobago",
        t0=datetime(2024, 1, 1, tzinfo=UTC),
        t1=datetime(2024, 1, 7, tzinfo=UTC),
        attrs=attrs,
    )


@pytest.fixture()
def predictor() -> FloodRiskPredictor:
    return FloodRiskPredictor()


# ── Predictor protocol ────────────────────────────────────────────────────────


def test_predictor_id(predictor: FloodRiskPredictor) -> None:
    assert predictor.predictor_id == "FloodRisk"


def test_predict_returns_prediction(predictor: FloodRiskPredictor) -> None:
    ctx = _make_ctx(precip_mm=50.0, discharge_m3s=200.0)
    result = predictor.predict(ctx, rng_seed=42)
    assert isinstance(result, Prediction)


def test_predict_kind_is_risk(predictor: FloodRiskPredictor) -> None:
    ctx = _make_ctx(precip_mm=50.0, discharge_m3s=200.0)
    result = predictor.predict(ctx, rng_seed=42)
    assert result.kind == "risk"


def test_predict_evidence_class_is_modeled(predictor: FloodRiskPredictor) -> None:
    """INV-3: FloodRisk must always produce modeled predictions."""
    ctx = _make_ctx(precip_mm=50.0, discharge_m3s=200.0)
    result = predictor.predict(ctx, rng_seed=42)
    assert result.evidence_class == "modeled"


def test_predict_uncertainty_not_empty(predictor: FloodRiskPredictor) -> None:
    """INV-9: uncertainty field must be non-empty."""
    ctx = _make_ctx(precip_mm=50.0, discharge_m3s=200.0)
    result = predictor.predict(ctx, rng_seed=42)
    assert isinstance(result.uncertainty, dict)
    assert len(result.uncertainty) > 0


def test_predict_uncertainty_model_type_is_rule_based(predictor: FloodRiskPredictor) -> None:
    ctx = _make_ctx(precip_mm=50.0, discharge_m3s=200.0)
    result = predictor.predict(ctx, rng_seed=42)
    assert result.uncertainty.get("model_type") == "rule_based"


def test_predict_rng_seed_recorded(predictor: FloodRiskPredictor) -> None:
    """INV-8: rng_seed must be stored in the Prediction."""
    ctx = _make_ctx(precip_mm=50.0)
    result = predictor.predict(ctx, rng_seed=99)
    assert result.rng_seed == 99


def test_predict_label_honesty_string(predictor: FloodRiskPredictor) -> None:
    """Honesty label must be present and explicitly state risk is modeled."""
    ctx = _make_ctx(precip_mm=50.0)
    result = predictor.predict(ctx, rng_seed=0)
    label = result.attrs.get("label", "")
    assert "modeled" in label.lower()
    assert "not a measured" in label.lower()


def test_predict_source_obs_ids_populated(predictor: FloodRiskPredictor) -> None:
    ctx = _make_ctx(precip_mm=120.0, discharge_m3s=600.0)
    result = predictor.predict(ctx, rng_seed=0)
    assert len(result.source_obs_ids) == 2


def test_predict_no_obs_returns_low_risk(predictor: FloodRiskPredictor) -> None:
    ctx = _make_ctx()  # no obs at all
    result = predictor.predict(ctx, rng_seed=0)
    assert result.attrs["risk_level"] == "low"


# ── F-042 AC: High precip + high discharge → high/extreme risk ────────────────


def test_high_precip_high_discharge_yields_high_or_extreme(
    predictor: FloodRiskPredictor,
) -> None:
    """F-042 AC: synthetic high-precip + high-discharge → risk ≥ 'high'."""
    ctx = _make_ctx(
        precip_mm=180.0,   # above precip_high threshold (100mm)
        discharge_m3s=1500.0,  # above discharge_high threshold (500 m3/s)
        choke_points=[_make_choke_point(constriction_score=0.9)],
    )
    result = predictor.predict(ctx, rng_seed=0)
    assert result.attrs["risk_level"] in ("high", "extreme")


def test_extreme_precip_extreme_discharge_yields_extreme(
    predictor: FloodRiskPredictor,
) -> None:
    """Maximum inputs → extreme risk level."""
    ctx = _make_ctx(
        precip_mm=250.0,   # well above extreme threshold (200mm)
        discharge_m3s=3000.0,  # well above extreme threshold (2000 m3/s)
        choke_points=[_make_choke_point(constriction_score=1.0)],
    )
    result = predictor.predict(ctx, rng_seed=0)
    assert result.attrs["risk_level"] == "extreme"


def test_zero_precip_zero_discharge_yields_low(predictor: FloodRiskPredictor) -> None:
    ctx = _make_ctx(precip_mm=0.0, discharge_m3s=0.0)
    result = predictor.predict(ctx, rng_seed=0)
    assert result.attrs["risk_level"] == "low"


def test_medium_precip_no_discharge_yields_medium_or_low(
    predictor: FloodRiskPredictor,
) -> None:
    ctx = _make_ctx(precip_mm=60.0)  # 60mm → precip_score ≈ 0.3
    result = predictor.predict(ctx, rng_seed=0)
    assert result.attrs["risk_level"] in ("low", "medium")


def test_choke_points_elevate_risk(predictor: FloodRiskPredictor) -> None:
    """Identical weather, adding high-constriction choke point raises risk."""
    ctx_no_cp = _make_ctx(precip_mm=80.0, discharge_m3s=300.0, choke_points=[])
    ctx_with_cp = _make_ctx(
        precip_mm=80.0,
        discharge_m3s=300.0,
        choke_points=[_make_choke_point(constriction_score=1.0)],
    )
    result_no_cp = predictor.predict(ctx_no_cp, rng_seed=0)
    result_with_cp = predictor.predict(ctx_with_cp, rng_seed=0)
    no_cp_score = result_no_cp.uncertainty["risk_score"]
    with_cp_score = result_with_cp.uncertainty["risk_score"]
    assert with_cp_score > no_cp_score


def test_custom_thresholds_change_risk_level(predictor: FloodRiskPredictor) -> None:
    """Threshold overrides in ctx.attrs must be respected."""
    ctx = _make_ctx(
        precip_mm=50.0,
        thresholds={"score_medium": 0.5, "score_high": 0.8, "score_extreme": 0.95},
    )
    result = predictor.predict(ctx, rng_seed=0)
    # With raised thresholds, 50mm precip should produce low risk
    assert result.attrs["risk_level"] == "low"


def test_peak_precip_recorded_in_attrs(predictor: FloodRiskPredictor) -> None:
    ctx = _make_ctx(precip_mm=123.4)
    result = predictor.predict(ctx, rng_seed=0)
    assert result.attrs["peak_precip_mm"] == pytest.approx(123.4)


def test_peak_discharge_recorded_in_attrs(predictor: FloodRiskPredictor) -> None:
    ctx = _make_ctx(discharge_m3s=456.7)
    result = predictor.predict(ctx, rng_seed=0)
    assert result.attrs["peak_discharge_m3s"] == pytest.approx(456.7)


def test_choke_point_count_in_attrs(predictor: FloodRiskPredictor) -> None:
    ctx = _make_ctx(choke_points=[_make_choke_point(), _make_choke_point()])
    result = predictor.predict(ctx, rng_seed=0)
    assert result.attrs["choke_point_count"] == 2


# ── Helper unit tests ─────────────────────────────────────────────────────────


def test_peak_from_obs_returns_max() -> None:
    obs = [_make_obs("precip_series", 5.0), _make_obs("precip_series", 12.8)]
    assert _peak_from_obs(obs, "precip_series") == pytest.approx(12.8)


def test_peak_from_obs_returns_none_when_no_match() -> None:
    obs = [_make_obs("discharge_series", 100.0)]
    assert _peak_from_obs(obs, "precip_series") is None


def test_peak_from_obs_skips_none_values() -> None:
    obs = [_make_obs("precip_series", None), _make_obs("precip_series", 5.0)]
    assert _peak_from_obs(obs, "precip_series") == pytest.approx(5.0)


def test_merge_thresholds_applies_override() -> None:
    t = _merge_thresholds({"score_medium": 0.1})
    assert t["score_medium"] == pytest.approx(0.1)
    assert t["score_high"] == pytest.approx(0.50)  # default preserved


def test_compute_risk_score_max_inputs() -> None:
    t = _merge_thresholds({})
    score = _compute_risk_score(
        peak_precip=999.0,
        peak_discharge=99999.0,
        max_constriction=1.0,
        thresholds=t,
    )
    assert score == pytest.approx(1.0)


def test_compute_risk_score_zero_inputs() -> None:
    t = _merge_thresholds({})
    score = _compute_risk_score(
        peak_precip=0.0,
        peak_discharge=0.0,
        max_constriction=0.0,
        thresholds=t,
    )
    assert score == pytest.approx(0.0)


def test_score_to_level_boundaries() -> None:
    t = _merge_thresholds({})
    assert _score_to_level(0.0, t) == "low"
    assert _score_to_level(0.25, t) == "medium"
    assert _score_to_level(0.50, t) == "high"
    assert _score_to_level(0.75, t) == "extreme"
    assert _score_to_level(1.0, t) == "extreme"


def test_score_to_level_just_below_thresholds() -> None:
    t = _merge_thresholds({})
    assert _score_to_level(0.2499, t) == "low"
    assert _score_to_level(0.4999, t) == "medium"
    assert _score_to_level(0.7499, t) == "high"


# ── validate() / SkillReport ──────────────────────────────────────────────────


def test_validate_empty_history(predictor: FloodRiskPredictor) -> None:
    report = predictor.validate([])
    assert report["hit_rate"] is None
    assert report["false_alarm_rate"] is None
    assert report["n_samples"] == 0


def test_validate_perfect_predictor(predictor: FloodRiskPredictor) -> None:
    """All true events predicted high → hit_rate = 1.0."""
    history = build_eval_set([
        {"precip_mm": 200.0, "discharge_m3s": 1500.0, "inundation_observed": True},
        {"precip_mm": 180.0, "discharge_m3s": 900.0, "inundation_observed": True},
    ])
    report = predictor.validate(history)
    assert report["hit_rate"] == pytest.approx(1.0)


def test_validate_zero_precip_all_false_alarms_zero(
    predictor: FloodRiskPredictor,
) -> None:
    """No inundation, zero inputs → no false alarms."""
    history = build_eval_set([
        {"precip_mm": 0.0, "discharge_m3s": 0.0, "inundation_observed": False},
        {"precip_mm": 0.0, "discharge_m3s": 0.0, "inundation_observed": False},
    ])
    report = predictor.validate(history)
    assert report["false_alarm_rate"] == pytest.approx(0.0)


def test_validate_n_samples(predictor: FloodRiskPredictor) -> None:
    history = build_eval_set([
        {"precip_mm": 100.0, "discharge_m3s": 500.0, "inundation_observed": False},
    ] * 5)
    report = predictor.validate(history)
    assert report["n_samples"] == 5


def test_build_eval_set_preserves_data() -> None:
    records = [{"precip_mm": 50.0, "discharge_m3s": 100.0, "inundation_observed": True}]
    es = build_eval_set(records)
    assert len(es) == 1
    assert es[0]["precip_mm"] == pytest.approx(50.0)
    assert es[0]["inundation_observed"] is True
