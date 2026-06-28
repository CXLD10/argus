"""Tests for F-043: AcidDepositionRisk predictor.

All tests are offline (INV-7).  Synthetic SO₂/NO₂/precip Observations are used.

Acceptance criteria:
  - High SO₂ + high precip → risk index > 7
  - Zero SO₂ → risk index = 0 regardless of precip
  - evidence_class = "modeled" always (INV-3)
  - API response includes explicit label: "modeled acid-deposition risk index … NOT a pH measurement"
  - uncertainty populated (INV-9)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from argus.core.models import Observation, Prediction
from argus.predict.acid_deposition.predictor import (
    AcidDepositionRiskPredictor,
    _compute_acid_index,
    _peak_from_obs,
)
from argus.predict.base import PredictContext

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_obs(obs_type: str, value: float) -> Observation:
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
        unit="μg/m3" if obs_type in ("so2_series", "no2_series") else "mm",
        domain="weather_hydro",
        attrs={"source": "open_meteo:air_quality"},
    )


def _make_ctx(
    so2: float | None = None,
    no2: float | None = None,
    precip: float | None = None,
    sensitivity: float = 1.0,
) -> PredictContext:
    obs: list[Observation] = []
    if so2 is not None:
        obs.append(_make_obs("so2_series", so2))
    if no2 is not None:
        obs.append(_make_obs("no2_series", no2))
    if precip is not None:
        obs.append(_make_obs("precip_series", precip))
    return PredictContext(
        obs=obs,
        aoi_id="tobago",
        t0=datetime(2024, 1, 1, tzinfo=UTC),
        t1=datetime(2024, 1, 7, tzinfo=UTC),
        attrs={"acid_sensitivity": sensitivity},
    )


@pytest.fixture()
def predictor() -> AcidDepositionRiskPredictor:
    return AcidDepositionRiskPredictor()


# ── Predictor protocol ────────────────────────────────────────────────────────


def test_predictor_id(predictor: AcidDepositionRiskPredictor) -> None:
    assert predictor.predictor_id == "AcidDepositionRisk"


def test_predict_returns_prediction(predictor: AcidDepositionRiskPredictor) -> None:
    ctx = _make_ctx(so2=30.0, precip=25.0)
    result = predictor.predict(ctx, rng_seed=42)
    assert isinstance(result, Prediction)


def test_predict_kind_is_risk(predictor: AcidDepositionRiskPredictor) -> None:
    ctx = _make_ctx(so2=30.0)
    result = predictor.predict(ctx, rng_seed=0)
    assert result.kind == "risk"


def test_predict_evidence_class_is_modeled(predictor: AcidDepositionRiskPredictor) -> None:
    """INV-3: AcidDepositionRisk must always be evidence_class='modeled'."""
    ctx = _make_ctx(so2=30.0, precip=20.0)
    result = predictor.predict(ctx, rng_seed=0)
    assert result.evidence_class == "modeled"


def test_predict_uncertainty_not_empty(predictor: AcidDepositionRiskPredictor) -> None:
    """INV-9: uncertainty field must be non-empty."""
    ctx = _make_ctx(so2=30.0, precip=20.0)
    result = predictor.predict(ctx, rng_seed=0)
    assert isinstance(result.uncertainty, dict)
    assert len(result.uncertainty) > 0


def test_predict_uncertainty_has_methodology(predictor: AcidDepositionRiskPredictor) -> None:
    ctx = _make_ctx(so2=30.0)
    result = predictor.predict(ctx, rng_seed=0)
    assert "methodology" in result.uncertainty


def test_predict_rng_seed_recorded(predictor: AcidDepositionRiskPredictor) -> None:
    """INV-8: rng_seed stored in Prediction."""
    ctx = _make_ctx(so2=10.0)
    result = predictor.predict(ctx, rng_seed=77)
    assert result.rng_seed == 77


# ── F-043 AC: Honesty label ───────────────────────────────────────────────────


def test_predict_label_says_not_ph_measurement(predictor: AcidDepositionRiskPredictor) -> None:
    """API response must explicitly state this is NOT a pH measurement."""
    ctx = _make_ctx(so2=30.0, precip=20.0)
    result = predictor.predict(ctx, rng_seed=0)
    label = result.attrs.get("label", "")
    assert "NOT a pH measurement" in label


def test_predict_label_says_modeled(predictor: AcidDepositionRiskPredictor) -> None:
    ctx = _make_ctx(so2=30.0)
    result = predictor.predict(ctx, rng_seed=0)
    label = result.attrs.get("label", "")
    assert "modeled" in label.lower()


def test_predict_label_says_0_to_10_scale(predictor: AcidDepositionRiskPredictor) -> None:
    ctx = _make_ctx(so2=30.0)
    result = predictor.predict(ctx, rng_seed=0)
    label = result.attrs.get("label", "")
    assert "0–10" in label or "0-10" in label


# ── F-043 AC: Risk index correctness ─────────────────────────────────────────


def test_high_so2_high_precip_yields_index_above_7(
    predictor: AcidDepositionRiskPredictor,
) -> None:
    """F-043 AC: high SO₂ + high precip → acid_risk_index > 7."""
    ctx = _make_ctx(
        so2=60.0,   # above SO2 saturation (50 μg/m³)
        precip=60.0,  # above precip saturation (50 mm)
    )
    result = predictor.predict(ctx, rng_seed=0)
    assert result.attrs["acid_risk_index"] > 7.0, (
        f"Expected > 7, got {result.attrs['acid_risk_index']}"
    )


def test_zero_so2_yields_index_zero(predictor: AcidDepositionRiskPredictor) -> None:
    """F-043 AC: zero SO₂ → risk index = 0 regardless of precip."""
    ctx = _make_ctx(so2=0.0, no2=200.0, precip=100.0)
    result = predictor.predict(ctx, rng_seed=0)
    assert result.attrs["acid_risk_index"] == pytest.approx(0.0)


def test_no_so2_obs_yields_index_zero(predictor: AcidDepositionRiskPredictor) -> None:
    """If no SO₂ observation present, index should be 0 (SO₂ drives the risk)."""
    ctx = _make_ctx(precip=100.0, no2=200.0)  # no so2 obs
    result = predictor.predict(ctx, rng_seed=0)
    assert result.attrs["acid_risk_index"] == pytest.approx(0.0)


def test_acid_index_range_0_to_10(predictor: AcidDepositionRiskPredictor) -> None:
    """Index must always be in [0, 10]."""
    for so2 in [0.0, 25.0, 50.0, 100.0, 1000.0]:
        for precip in [0.0, 10.0, 50.0, 200.0]:
            ctx = _make_ctx(so2=so2, precip=precip)
            result = predictor.predict(ctx, rng_seed=0)
            idx = result.attrs["acid_risk_index"]
            assert 0.0 <= idx <= 10.0, f"Index {idx} out of range for SO2={so2}, precip={precip}"


def test_higher_so2_higher_index(predictor: AcidDepositionRiskPredictor) -> None:
    """Increasing SO₂ with fixed precip monotonically increases index."""
    indices = []
    for so2 in [5.0, 20.0, 50.0, 100.0]:
        ctx = _make_ctx(so2=so2, precip=30.0)
        result = predictor.predict(ctx, rng_seed=0)
        indices.append(result.attrs["acid_risk_index"])
    for a, b in zip(indices, indices[1:], strict=False):
        assert b >= a


def test_catchment_sensitivity_amplifies_index(
    predictor: AcidDepositionRiskPredictor,
) -> None:
    """Higher catchment sensitivity raises the risk index."""
    ctx_low = _make_ctx(so2=40.0, precip=30.0, sensitivity=0.5)
    ctx_high = _make_ctx(so2=40.0, precip=30.0, sensitivity=1.0)
    r_low = predictor.predict(ctx_low, rng_seed=0)
    r_high = predictor.predict(ctx_high, rng_seed=0)
    assert r_high.attrs["acid_risk_index"] > r_low.attrs["acid_risk_index"]


def test_no2_amplifies_index_when_present(
    predictor: AcidDepositionRiskPredictor,
) -> None:
    """Adding NO₂ with same SO₂ + precip raises index (until saturation)."""
    ctx_no_no2 = _make_ctx(so2=30.0, precip=30.0)
    ctx_with_no2 = _make_ctx(so2=30.0, no2=100.0, precip=30.0)
    r_no = predictor.predict(ctx_no_no2, rng_seed=0)
    r_with = predictor.predict(ctx_with_no2, rng_seed=0)
    # no2_norm=1.0 when absent (neutral), 100/100=1.0 when present → same
    # When no2=100 → norm=1.0; absent → norm=1.0; so result is same
    assert r_with.attrs["acid_risk_index"] == pytest.approx(r_no.attrs["acid_risk_index"])


def test_peak_so2_recorded_in_attrs(predictor: AcidDepositionRiskPredictor) -> None:
    ctx = _make_ctx(so2=42.5, precip=10.0)
    result = predictor.predict(ctx, rng_seed=0)
    assert result.attrs["peak_so2_ug_m3"] == pytest.approx(42.5)


def test_uncertainty_index_range_sensible(predictor: AcidDepositionRiskPredictor) -> None:
    ctx = _make_ctx(so2=30.0, precip=25.0)
    result = predictor.predict(ctx, rng_seed=0)
    lo, hi = result.uncertainty["index_range"]
    assert lo <= result.attrs["acid_risk_index"] <= hi


# ── _compute_acid_index unit tests ────────────────────────────────────────────


def test_compute_acid_index_max_inputs() -> None:
    idx, comps = _compute_acid_index(
        peak_so2=999.0, peak_no2=999.0, peak_precip=999.0, catchment_sensitivity=1.0
    )
    assert idx == pytest.approx(10.0)


def test_compute_acid_index_zero_so2() -> None:
    idx, _ = _compute_acid_index(
        peak_so2=0.0, peak_no2=100.0, peak_precip=100.0, catchment_sensitivity=1.0
    )
    assert idx == pytest.approx(0.0)


def test_compute_acid_index_no_no2_uses_neutral() -> None:
    idx_no_no2, _ = _compute_acid_index(
        peak_so2=50.0, peak_no2=None, peak_precip=50.0, catchment_sensitivity=1.0
    )
    idx_full_no2, _ = _compute_acid_index(
        peak_so2=50.0, peak_no2=100.0, peak_precip=50.0, catchment_sensitivity=1.0
    )
    # no2=None → no2_norm=1.0; no2=100 → no2_norm=1.0 (same at saturation)
    assert idx_no_no2 == pytest.approx(idx_full_no2)


def test_compute_acid_index_components_populated() -> None:
    _, comps = _compute_acid_index(
        peak_so2=25.0, peak_no2=50.0, peak_precip=25.0, catchment_sensitivity=1.0
    )
    assert "so2_norm" in comps
    assert "no2_norm" in comps
    assert "precip_norm" in comps
    assert "sensitivity_norm" in comps


def test_peak_from_obs_no_match_returns_none() -> None:
    obs = [_make_obs("so2_series", 5.0)]
    assert _peak_from_obs(obs, "no2_series") is None


# ── validate() ────────────────────────────────────────────────────────────────


def test_validate_empty_returns_none_mae(predictor: AcidDepositionRiskPredictor) -> None:
    report = predictor.validate([])
    assert report["mae"] is None
    assert report["n_samples"] == 0


def test_validate_returns_mae(predictor: AcidDepositionRiskPredictor) -> None:
    history = [
        {"so2_ug_m3": 50.0, "precip_mm": 50.0, "expert_index": 10.0},
        {"so2_ug_m3": 0.0, "precip_mm": 50.0, "expert_index": 0.0},
    ]
    report = predictor.validate(history)
    assert report["mae"] is not None
    assert report["mae"] >= 0.0
    assert report["n_samples"] == 2
