"""F-034 tests: WQ exposure + impact assessment for drinking intakes and recreation sites."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from argus.core.models import ExposureLayer, Prediction
from argus.core.store import Store
from argus.impact.assessor import assess_wq_impact, load_exposure_layer

_REPO_ROOT = Path(__file__).parent.parent
_INTAKE_GJ = _REPO_ROOT / "data" / "static" / "exposure" / "drinking_intakes_reference.geojson"
_RECREATION_GJ = _REPO_ROOT / "data" / "static" / "exposure" / "recreation_sites_reference.geojson"

# Reference lake polygon (matches config/water_bodies/reference_lake.geojson)
_LAKE_GEOM = {
    "type": "Polygon",
    "coordinates": [[
        [-60.502, 10.499],
        [-60.499, 10.499],
        [-60.499, 10.502],
        [-60.502, 10.502],
        [-60.502, 10.499],
    ]],
}

# Geometry far from the reference lake
_FAR_POINT_GEOM = {
    "type": "Point",
    "coordinates": [-61.5, 11.5],  # Tobago area, far from reference lake
}

_T0 = datetime(2026, 6, 28, 0, 0, tzinfo=UTC)


def _make_anomaly_pred(z_score: float = 3.5, pred_id: str | None = None) -> Prediction:
    return Prediction(
        id=pred_id or str(uuid.uuid4()),
        predictor_id="anomaly_detector_wq",
        kind="anomaly",
        uncertainty={"sigma": z_score},
        rng_seed=42,
        attrs={
            "anomaly_detected": abs(z_score) >= 2.5,
            "z_score": z_score,
            "threshold_sigma": 2.5,
            "obs_type": "chlorophyll_a",
        },
    )


def _make_forecast_pred(value: float = 30.0, pred_id: str | None = None) -> Prediction:
    return Prediction(
        id=pred_id or str(uuid.uuid4()),
        predictor_id="wq_forecast_v1",
        kind="forecast",
        uncertainty={"ci_90_low": value - 5.0, "ci_90_high": value + 5.0, "rmse": 2.0},
        rng_seed=42,
        attrs={
            "value": value,
            "ci_low": value - 5.0,
            "ci_high": value + 5.0,
            "obs_type": "chlorophyll_a",
            "horizon_days": 7,
        },
    )


def _intake_layer() -> ExposureLayer:
    return load_exposure_layer(_INTAKE_GJ)


def _recreation_layer() -> ExposureLayer:
    return load_exposure_layer(_RECREATION_GJ)


def _far_intake_layer() -> ExposureLayer:
    return ExposureLayer(
        id="far_intake",
        name="Far Intake",
        layer_type="drinking_intake",
        geometry=_FAR_POINT_GEOM,
    )


# ── Fixture file loading ──────────────────────────────────────────────────────


def test_load_intake_fixture_layer_type() -> None:
    layer = _intake_layer()
    assert layer.layer_type == "drinking_intake"


def test_load_intake_fixture_has_point_geometry() -> None:
    layer = _intake_layer()
    assert layer.geometry["type"] == "Point"


def test_load_recreation_fixture_layer_type() -> None:
    layer = _recreation_layer()
    assert layer.layer_type == "recreation_site"


def test_load_recreation_fixture_has_point_geometry() -> None:
    layer = _recreation_layer()
    assert layer.geometry["type"] == "Point"


def test_intake_point_is_inside_reference_lake() -> None:
    from shapely.geometry import shape
    lake = shape(_LAKE_GEOM)
    intake = shape(_intake_layer().geometry)
    assert lake.intersects(intake)


def test_recreation_point_is_inside_reference_lake() -> None:
    from shapely.geometry import shape
    lake = shape(_LAKE_GEOM)
    rec = shape(_recreation_layer().geometry)
    assert lake.intersects(rec)


# ── assess_wq_impact: anomaly prediction ─────────────────────────────────────


def test_wq_impact_anomaly_above_threshold_creates_assessments() -> None:
    pred = _make_anomaly_pred(z_score=3.5)
    layers = [_intake_layer(), _recreation_layer()]
    results = assess_wq_impact(pred, _LAKE_GEOM, layers, t0=_T0)
    assert len(results) == 2


def test_wq_impact_anomaly_below_threshold_returns_empty() -> None:
    pred = _make_anomaly_pred(z_score=1.0)
    layers = [_intake_layer(), _recreation_layer()]
    results = assess_wq_impact(pred, _LAKE_GEOM, layers, t0=_T0)
    assert results == []


def test_wq_impact_anomaly_at_threshold_creates_assessments() -> None:
    pred = _make_anomaly_pred(z_score=2.5)
    layers = [_intake_layer()]
    results = assess_wq_impact(pred, _LAKE_GEOM, layers, t0=_T0)
    assert len(results) == 1


def test_wq_impact_anomaly_negative_z_score_triggers() -> None:
    # Negative anomaly (e.g. unusual drop) also triggers if abs(z) >= threshold
    pred = _make_anomaly_pred(z_score=-3.0)
    layers = [_intake_layer()]
    results = assess_wq_impact(pred, _LAKE_GEOM, layers, t0=_T0)
    assert len(results) == 1


def test_wq_impact_anomaly_eta_hours_is_zero() -> None:
    # Anomaly = immediate threat, ETA = 0 hours
    pred = _make_anomaly_pred(z_score=3.5)
    layers = [_intake_layer()]
    results = assess_wq_impact(pred, _LAKE_GEOM, layers, t0=_T0)
    assert results[0].eta_hours == pytest.approx(0.0)


def test_wq_impact_anomaly_valid_at_equals_t0() -> None:
    pred = _make_anomaly_pred(z_score=3.5)
    layers = [_intake_layer()]
    results = assess_wq_impact(pred, _LAKE_GEOM, layers, t0=_T0)
    assert results[0].valid_at == _T0


# ── assess_wq_impact: forecast prediction ────────────────────────────────────


def test_wq_impact_forecast_above_threshold_creates_assessments() -> None:
    pred = _make_forecast_pred(value=30.0)  # > 25.0 threshold
    layers = [_intake_layer(), _recreation_layer()]
    results = assess_wq_impact(pred, _LAKE_GEOM, layers, t0=_T0)
    assert len(results) == 2


def test_wq_impact_forecast_below_threshold_returns_empty() -> None:
    pred = _make_forecast_pred(value=10.0)  # < 25.0 threshold
    layers = [_intake_layer(), _recreation_layer()]
    results = assess_wq_impact(pred, _LAKE_GEOM, layers, t0=_T0)
    assert results == []


def test_wq_impact_forecast_eta_hours_is_horizon() -> None:
    # 7-day forecast → eta = 7 * 24 = 168 hours
    pred = _make_forecast_pred(value=30.0)
    layers = [_intake_layer()]
    results = assess_wq_impact(pred, _LAKE_GEOM, layers, t0=_T0)
    assert results[0].eta_hours == pytest.approx(168.0)


def test_wq_impact_forecast_valid_at_is_t0_plus_horizon() -> None:
    from datetime import timedelta
    pred = _make_forecast_pred(value=30.0)
    layers = [_intake_layer()]
    results = assess_wq_impact(pred, _LAKE_GEOM, layers, t0=_T0)
    assert results[0].valid_at == _T0 + timedelta(hours=168.0)


# ── assess_wq_impact: layer intersection ─────────────────────────────────────


def test_wq_impact_far_intake_not_threatened() -> None:
    pred = _make_anomaly_pred(z_score=3.5)
    layers = [_far_intake_layer()]
    results = assess_wq_impact(pred, _LAKE_GEOM, layers, t0=_T0)
    assert results == []


def test_wq_impact_mixed_layers_only_inside_ones_hit() -> None:
    pred = _make_anomaly_pred(z_score=3.5)
    layers = [_intake_layer(), _far_intake_layer()]
    results = assess_wq_impact(pred, _LAKE_GEOM, layers, t0=_T0)
    assert len(results) == 1


def test_wq_impact_non_wq_layer_types_ignored() -> None:
    # coastline and marine_protected_area layers must not appear in results
    from argus.impact.assessor import load_exposure_layer
    _REPO_ROOT = Path(__file__).parent.parent
    coast_layer = load_exposure_layer(
        _REPO_ROOT / "data" / "static" / "exposure" / "coastline_tobago.geojson"
    )
    pred = _make_anomaly_pred(z_score=3.5)
    results = assess_wq_impact(pred, _LAKE_GEOM, [coast_layer], t0=_T0)
    assert results == []


def test_wq_impact_prediction_id_set_correctly() -> None:
    pred = _make_anomaly_pred(z_score=3.5, pred_id="test-pred-001")
    layers = [_intake_layer()]
    results = assess_wq_impact(pred, _LAKE_GEOM, layers, t0=_T0)
    assert results[0].prediction_id == "test-pred-001"


def test_wq_impact_exposure_layer_id_set_correctly() -> None:
    layer = _intake_layer()
    pred = _make_anomaly_pred(z_score=3.5)
    results = assess_wq_impact(pred, _LAKE_GEOM, [layer], t0=_T0)
    assert results[0].exposure_layer_id == layer.id


# ── assess_wq_impact: metrics ─────────────────────────────────────────────────


def test_wq_impact_intake_metrics_has_intakes_threatened() -> None:
    pred = _make_anomaly_pred(z_score=3.5)
    results = assess_wq_impact(pred, _LAKE_GEOM, [_intake_layer()], t0=_T0)
    assert results[0].metrics["intakes_threatened"] == 1


def test_wq_impact_recreation_metrics_has_sites_threatened() -> None:
    pred = _make_anomaly_pred(z_score=3.5)
    results = assess_wq_impact(pred, _LAKE_GEOM, [_recreation_layer()], t0=_T0)
    assert results[0].metrics["recreation_sites_threatened"] == 1


def test_wq_impact_no_nearby_exposure_returns_empty() -> None:
    """AC: No nearby exposure → no ImpactAssessment (correct non-event handling)."""
    pred = _make_anomaly_pred(z_score=3.5)
    results = assess_wq_impact(pred, _LAKE_GEOM, [_far_intake_layer()], t0=_T0)
    assert results == []


def test_wq_impact_intake_inside_lake_creates_assessment() -> None:
    """AC: Reference lake with nearby intake → forecast above threshold → ImpactAssessment created."""
    pred = _make_forecast_pred(value=30.0)
    layers = [_intake_layer()]
    results = assess_wq_impact(pred, _LAKE_GEOM, layers, t0=_T0)
    assert len(results) == 1


# ── Store round-trip ──────────────────────────────────────────────────────────


def test_wq_intake_layer_store_round_trip(tmp_path: Path) -> None:
    store = Store(tmp_path / "argus.db")
    layer = _intake_layer()
    store.save_exposure_layer(layer)
    retrieved = store.get_exposure_layers()
    assert len(retrieved) == 1
    assert retrieved[0].layer_type == "drinking_intake"


def test_wq_impact_assessment_store_round_trip(tmp_path: Path) -> None:
    store = Store(tmp_path / "argus.db")
    pred = _make_anomaly_pred(z_score=3.5, pred_id="store-pred-001")
    store.save_prediction(pred)
    layer = _intake_layer()
    store.save_exposure_layer(layer)

    results = assess_wq_impact(pred, _LAKE_GEOM, [layer], t0=_T0)
    for ia in results:
        store.save_impact_assessment(ia)

    retrieved = store.get_impact_assessments_for_prediction(pred.id)
    assert len(retrieved) == 1
    assert retrieved[0].metrics["intakes_threatened"] == 1


def test_wq_custom_threshold_controls_trigger(tmp_path: Path) -> None:
    # With a very high threshold, low z_score prediction should not trigger
    pred = _make_anomaly_pred(z_score=3.0)
    layers = [_intake_layer()]
    # anomaly_sigma_threshold=5.0 → 3.0 < 5.0 → no impact
    results = assess_wq_impact(
        pred, _LAKE_GEOM, layers, anomaly_sigma_threshold=5.0, t0=_T0
    )
    assert results == []
    # With lower threshold, should trigger
    results2 = assess_wq_impact(
        pred, _LAKE_GEOM, layers, anomaly_sigma_threshold=2.5, t0=_T0
    )
    assert len(results2) == 1
