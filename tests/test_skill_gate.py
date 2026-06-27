"""F-029 tests: skill gate, Predictor interface finalization, gated API endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from argus.api.app import create_app
from argus.core.models import Prediction
from argus.core.store import Store
from argus.eval.skill_gate import check_gate, gate_predictions

# ── Helpers ────────────────────────────────────────────────────────────────────

_GEOMETRY = {"type": "Point", "coordinates": [0.0, 0.0]}


def _make_forecast_prediction(predictor_id: str) -> Prediction:
    return Prediction(
        id=str(uuid.uuid4()),
        predictor_id=predictor_id,
        source_obs_ids=[],
        kind="forecast",
        evidence_class="modeled",
        uncertainty={"ci_90_low": 0.04, "ci_90_high": 0.07, "rmse": 0.005},
        rng_seed=42,
        attrs={"value": 0.055, "ci_low": 0.04, "ci_high": 0.07, "obs_type": "chlorophyll_a"},
    )


def _save_skill_report(
    store: Store,
    predictor_id: str,
    passed_gate: bool,
) -> None:
    store.save_skill_report(
        report_id=str(uuid.uuid4()),
        predictor_id=predictor_id,
        eval_case_id="eval_test",
        precision=0.8,
        recall=0.75,
        f1=0.77,
        n_observations=20,
        created_at=datetime.now(UTC),
        passed_gate=passed_gate,
    )


# ── check_gate ────────────────────────────────────────────────────────────────


def test_check_gate_no_reports_returns_false(tmp_store: Store) -> None:
    assert check_gate("wq_forecast_v1", tmp_store) is False


def test_check_gate_with_passed_report_returns_true(tmp_store: Store) -> None:
    _save_skill_report(tmp_store, "wq_forecast_v1", passed_gate=True)
    assert check_gate("wq_forecast_v1", tmp_store) is True


def test_check_gate_with_failed_report_returns_false(tmp_store: Store) -> None:
    _save_skill_report(tmp_store, "wq_forecast_v1", passed_gate=False)
    assert check_gate("wq_forecast_v1", tmp_store) is False


def test_check_gate_uses_most_recent_report(tmp_store: Store) -> None:
    """Latest SkillReport wins; first fail then pass → gate should pass."""
    _save_skill_report(tmp_store, "wq_forecast_v1", passed_gate=False)
    _save_skill_report(tmp_store, "wq_forecast_v1", passed_gate=True)
    assert check_gate("wq_forecast_v1", tmp_store) is True


def test_check_gate_predictor_isolation(tmp_store: Store) -> None:
    """Gate for predictor A doesn't affect predictor B."""
    _save_skill_report(tmp_store, "predictor_a", passed_gate=True)
    assert check_gate("predictor_b", tmp_store) is False


# ── gate_predictions ──────────────────────────────────────────────────────────


def test_gate_predictions_excludes_ungated(tmp_store: Store) -> None:
    """AC: Mock predictor with passed_gate=False → not returned."""
    _save_skill_report(tmp_store, "ungated_predictor", passed_gate=False)
    pred = _make_forecast_prediction("ungated_predictor")
    result = gate_predictions([pred], tmp_store)
    assert result == []


def test_gate_predictions_includes_gated(tmp_store: Store) -> None:
    """AC: Mock predictor with passed_gate=True → returned."""
    _save_skill_report(tmp_store, "gated_predictor", passed_gate=True)
    pred = _make_forecast_prediction("gated_predictor")
    result = gate_predictions([pred], tmp_store)
    assert len(result) == 1
    assert result[0].predictor_id == "gated_predictor"


def test_gate_predictions_mixed(tmp_store: Store) -> None:
    """Mixed predictors: only gated ones survive."""
    _save_skill_report(tmp_store, "predictor_ok", passed_gate=True)
    _save_skill_report(tmp_store, "predictor_ng", passed_gate=False)
    preds = [
        _make_forecast_prediction("predictor_ok"),
        _make_forecast_prediction("predictor_ng"),
    ]
    result = gate_predictions(preds, tmp_store)
    assert len(result) == 1
    assert result[0].predictor_id == "predictor_ok"


def test_gate_predictions_empty_list(tmp_store: Store) -> None:
    assert gate_predictions([], tmp_store) == []


def test_gate_predictions_no_skill_reports(tmp_store: Store) -> None:
    """Predictor with no skill report → excluded."""
    pred = _make_forecast_prediction("new_predictor")
    result = gate_predictions([pred], tmp_store)
    assert result == []


# ── Store: get_skill_reports_by_predictor ─────────────────────────────────────


def test_get_skill_reports_by_predictor_empty(tmp_store: Store) -> None:
    assert tmp_store.get_skill_reports_by_predictor("unknown") == []


def test_get_skill_reports_by_predictor_returns_records(tmp_store: Store) -> None:
    _save_skill_report(tmp_store, "predictor_x", passed_gate=True)
    reports = tmp_store.get_skill_reports_by_predictor("predictor_x")
    assert len(reports) == 1
    assert reports[0]["predictor_id"] == "predictor_x"
    assert bool(reports[0]["passed_gate"]) is True


def test_get_skill_reports_by_predictor_sorted_ascending(tmp_store: Store) -> None:
    for pg in [False, True, False]:
        _save_skill_report(tmp_store, "predictor_y", passed_gate=pg)
    reports = tmp_store.get_skill_reports_by_predictor("predictor_y")
    assert len(reports) == 3
    # Last report has passed_gate=False
    assert bool(reports[-1]["passed_gate"]) is False


# ── API: /waterbody/{id}/forecasts (skill gate enforced) ─────────────────────


@pytest.fixture()
def wq_client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "argus_test.db"
    app = create_app(db_path=db_path, config_dir=Path("config"))
    return TestClient(app)


def _get_store_from_client(client: TestClient) -> Store:
    return Store(client.app.state.db_path)


def test_forecasts_endpoint_returns_200(wq_client: TestClient) -> None:
    resp = wq_client.get("/waterbody/test_lake/forecasts")
    assert resp.status_code == 200


def test_forecasts_endpoint_excludes_ungated_predictor(wq_client: TestClient) -> None:
    """AC: Mock predictor with passed_gate=False → not returned by forecasts endpoint."""
    store = _get_store_from_client(wq_client)
    _save_skill_report(store, "ungated_predictor", passed_gate=False)
    store.save_prediction(_make_forecast_prediction("ungated_predictor"))

    resp = wq_client.get("/waterbody/test_lake/forecasts")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 0
    assert data["items"] == []


def test_forecasts_endpoint_includes_gated_predictor(wq_client: TestClient) -> None:
    """AC: Mock predictor with passed_gate=True → returned by forecasts endpoint."""
    store = _get_store_from_client(wq_client)
    _save_skill_report(store, "gated_predictor", passed_gate=True)
    pred = _make_forecast_prediction("gated_predictor")
    store.save_prediction(pred)

    resp = wq_client.get("/waterbody/test_lake/forecasts")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["items"][0]["predictor_id"] == "gated_predictor"


def test_raw_predictions_endpoint_returns_all(wq_client: TestClient) -> None:
    """raw_predictions returns both gated and ungated predictions."""
    store = _get_store_from_client(wq_client)
    _save_skill_report(store, "gated_predictor", passed_gate=True)
    _save_skill_report(store, "ungated_predictor", passed_gate=False)
    store.save_prediction(_make_forecast_prediction("gated_predictor"))
    store.save_prediction(_make_forecast_prediction("ungated_predictor"))

    resp = wq_client.get("/waterbody/test_lake/raw_predictions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2


def test_forecasts_attribution_present(wq_client: TestClient) -> None:
    resp = wq_client.get("/waterbody/test_lake/forecasts")
    data = resp.json()
    assert "_attribution" in data
