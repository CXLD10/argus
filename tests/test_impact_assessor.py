"""F-014 tests: ExposureLayer, ImpactAssessment, impact assessor, store round-trips."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from argus.core.models import ExposureLayer, ForecastFrame, ImpactAssessment, Prediction
from argus.core.store import Store
from argus.impact.assessor import assess_impact, load_exposure_layer

_REPO_ROOT = Path(__file__).parent.parent
_COAST_GJ = _REPO_ROOT / "data" / "static" / "exposure" / "coastline_tobago.geojson"
_MPA_GJ = _REPO_ROOT / "data" / "static" / "exposure" / "mpas_tobago.geojson"

# Footprint that overlaps both fixtures (centre of Tobago test bbox)
_OVERLAPPING_FOOTPRINT = {
    "type": "Polygon",
    "coordinates": [[[-61.4, 11.0], [-61.1, 11.0], [-61.1, 11.3], [-61.4, 11.3], [-61.4, 11.0]]],
}

# Footprint far away from all exposure fixtures
_MISS_FOOTPRINT = {
    "type": "Polygon",
    "coordinates": [[[-60.0, 10.0], [-59.0, 10.0], [-59.0, 10.5], [-60.0, 10.5], [-60.0, 10.0]]],
}

_T0 = datetime(2024, 2, 7, 0, 0, tzinfo=UTC)
_T1 = datetime(2024, 2, 8, 0, 0, tzinfo=UTC)  # 24 h later


def _make_prediction(pred_id: str = "pred-001") -> Prediction:
    return Prediction(
        id=pred_id,
        predictor_id="oil_trajectory_v1",
        kind="trajectory",
        uncertainty={"particle_spread_km": 18.0},
        rng_seed=42,
    )


def _make_frame(
    pred_id: str = "pred-001",
    valid_at: datetime = _T1,
    footprint: dict | None = None,
) -> ForecastFrame:
    return ForecastFrame(
        id=str(uuid.uuid4()),
        prediction_id=pred_id,
        valid_at=valid_at,
        footprint=footprint or _OVERLAPPING_FOOTPRINT,
        particle_count=1000,
    )


def _coastline_layer() -> ExposureLayer:
    return load_exposure_layer(_COAST_GJ)


def _mpa_layer() -> ExposureLayer:
    return load_exposure_layer(_MPA_GJ)


# ── Fixture file loading ──────────────────────────────────────────────────────


def test_load_coastline_fixture_has_geometry() -> None:
    layer = _coastline_layer()
    assert layer.geometry["type"] == "LineString"


def test_load_coastline_fixture_layer_type() -> None:
    layer = _coastline_layer()
    assert layer.layer_type == "coastline"


def test_load_mpa_fixture_has_geometry() -> None:
    layer = _mpa_layer()
    assert layer.geometry["type"] == "Polygon"


def test_load_mpa_fixture_layer_type() -> None:
    layer = _mpa_layer()
    assert layer.layer_type == "marine_protected_area"


# ── assess_impact: hit cases ──────────────────────────────────────────────────


def test_impact_hit_coastline_returns_assessment() -> None:
    pred = _make_prediction()
    frames = [_make_frame()]
    layers = [_coastline_layer()]
    results = assess_impact(pred, frames, layers, _T0)
    assert len(results) == 1


def test_impact_hit_mpa_returns_assessment() -> None:
    pred = _make_prediction()
    frames = [_make_frame()]
    layers = [_mpa_layer()]
    results = assess_impact(pred, frames, layers, _T0)
    assert len(results) == 1


def test_impact_hit_both_layers_returns_two_assessments() -> None:
    pred = _make_prediction()
    frames = [_make_frame()]
    layers = [_coastline_layer(), _mpa_layer()]
    results = assess_impact(pred, frames, layers, _T0)
    assert len(results) == 2


def test_impact_hit_valid_at_is_frame_valid_at() -> None:
    pred = _make_prediction()
    frame = _make_frame(valid_at=_T1)
    results = assess_impact(pred, [frame], [_coastline_layer()], _T0)
    assert results[0].valid_at == _T1


def test_impact_hit_eta_hours_correct() -> None:
    pred = _make_prediction()
    frame = _make_frame(valid_at=_T1)  # _T1 - _T0 = 24 h
    results = assess_impact(pred, [frame], [_coastline_layer()], _T0)
    assert results[0].eta_hours == pytest.approx(24.0, abs=0.01)


def test_impact_hit_coast_length_km_nonzero() -> None:
    pred = _make_prediction()
    results = assess_impact(pred, [_make_frame()], [_coastline_layer()], _T0)
    assert results[0].metrics["coast_length_km"] > 0.0


def test_impact_hit_mpa_area_km2_nonzero() -> None:
    pred = _make_prediction()
    results = assess_impact(pred, [_make_frame()], [_mpa_layer()], _T0)
    assert results[0].metrics["mpa_area_km2"] > 0.0


def test_impact_hit_prediction_id_set() -> None:
    pred = _make_prediction("pred-xyz")
    results = assess_impact(pred, [_make_frame("pred-xyz")], [_coastline_layer()], _T0)
    assert results[0].prediction_id == "pred-xyz"


# ── assess_impact: miss case ──────────────────────────────────────────────────


def test_impact_miss_returns_empty_list() -> None:
    pred = _make_prediction()
    frame = _make_frame(footprint=_MISS_FOOTPRINT)
    layers = [_coastline_layer(), _mpa_layer()]
    results = assess_impact(pred, [frame], layers, _T0)
    assert results == []


def test_impact_miss_no_zero_value_record() -> None:
    pred = _make_prediction()
    frame = _make_frame(footprint=_MISS_FOOTPRINT)
    results = assess_impact(pred, [frame], [_coastline_layer()], _T0)
    assert not any(ia.eta_hours == 0.0 for ia in results)


# ── assess_impact: ETA = first frame ─────────────────────────────────────────


def test_impact_first_frame_wins() -> None:
    pred = _make_prediction()
    t_early = datetime(2024, 2, 7, 6, 0, tzinfo=UTC)
    t_late = datetime(2024, 2, 7, 18, 0, tzinfo=UTC)
    frames = [
        _make_frame(valid_at=t_early, footprint=_OVERLAPPING_FOOTPRINT),
        _make_frame(valid_at=t_late, footprint=_OVERLAPPING_FOOTPRINT),
    ]
    results = assess_impact(pred, frames, [_coastline_layer()], _T0)
    assert len(results) == 1
    assert results[0].valid_at == t_early


def test_impact_second_frame_hits_when_first_misses() -> None:
    pred = _make_prediction()
    t_early = datetime(2024, 2, 7, 6, 0, tzinfo=UTC)
    t_late = datetime(2024, 2, 7, 18, 0, tzinfo=UTC)
    frames = [
        _make_frame(valid_at=t_early, footprint=_MISS_FOOTPRINT),
        _make_frame(valid_at=t_late, footprint=_OVERLAPPING_FOOTPRINT),
    ]
    results = assess_impact(pred, frames, [_coastline_layer()], _T0)
    assert len(results) == 1
    assert results[0].valid_at == t_late


# ── Store round-trips ─────────────────────────────────────────────────────────


def test_exposure_layer_store_round_trip(tmp_path: Path) -> None:
    store = Store(tmp_path / "argus.db")
    layer = _coastline_layer()
    store.save_exposure_layer(layer)
    layers = store.get_exposure_layers()
    assert len(layers) == 1
    assert layers[0].id == layer.id


def test_exposure_layer_geometry_round_trip(tmp_path: Path) -> None:
    store = Store(tmp_path / "argus.db")
    layer = _mpa_layer()
    store.save_exposure_layer(layer)
    retrieved = store.get_exposure_layers()[0]
    assert retrieved.geometry["type"] == "Polygon"


def test_exposure_layer_type_round_trip(tmp_path: Path) -> None:
    store = Store(tmp_path / "argus.db")
    layer = _mpa_layer()
    store.save_exposure_layer(layer)
    retrieved = store.get_exposure_layers()[0]
    assert retrieved.layer_type == "marine_protected_area"


def test_impact_assessment_store_round_trip(tmp_path: Path) -> None:
    store = Store(tmp_path / "argus.db")
    pred = _make_prediction()
    store.save_prediction(pred)
    layer = _coastline_layer()
    store.save_exposure_layer(layer)
    ia = ImpactAssessment(
        id=str(uuid.uuid4()),
        prediction_id=pred.id,
        exposure_layer_id=layer.id,
        valid_at=_T1,
        eta_hours=24.0,
        metrics={"coast_length_km": 12.5},
    )
    store.save_impact_assessment(ia)
    retrieved = store.get_impact_assessments_for_prediction(pred.id)
    assert len(retrieved) == 1


def test_impact_assessment_metrics_round_trip(tmp_path: Path) -> None:
    store = Store(tmp_path / "argus.db")
    pred = _make_prediction()
    store.save_prediction(pred)
    layer = _coastline_layer()
    store.save_exposure_layer(layer)
    ia = ImpactAssessment(
        id=str(uuid.uuid4()),
        prediction_id=pred.id,
        exposure_layer_id=layer.id,
        valid_at=_T1,
        eta_hours=24.0,
        metrics={"coast_length_km": 12.5},
    )
    store.save_impact_assessment(ia)
    retrieved = store.get_impact_assessments_for_prediction(pred.id)[0]
    assert retrieved.metrics["coast_length_km"] == pytest.approx(12.5)


def test_get_impact_assessments_empty(tmp_path: Path) -> None:
    store = Store(tmp_path / "argus.db")
    results = store.get_impact_assessments_for_prediction("nonexistent")
    assert results == []
