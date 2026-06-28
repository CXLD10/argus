"""F-036 tests: HAB early-warning alerting + D2 product exports."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from argus.alert.delivery import (
    Alert,
    AlertChannel,
    create_hab_alert,
    send_alert,
    should_alert_hab,
)
from argus.core.models import Prediction
from argus.export.products import export_wq_geojson, export_wq_products, export_wq_summary


def _make_anomaly_pred(z_score: float = 3.5) -> Prediction:
    obs_id = str(uuid.uuid4())
    return Prediction(
        id=str(uuid.uuid4()),
        predictor_id="anomaly_detector_wq",
        kind="anomaly",
        source_obs_ids=[obs_id],
        uncertainty={"sigma": z_score},
        rng_seed=42,
        attrs={
            "anomaly_detected": abs(z_score) >= 2.5,
            "z_score": z_score,
            "threshold_sigma": 2.5,
            "obs_type": "chlorophyll_a",
        },
    )


def _make_forecast_pred(value: float = 30.0) -> Prediction:
    return Prediction(
        id=str(uuid.uuid4()),
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

_WB_ENTRY = {
    "target_id": "reference_lake",
    "name": "Reference Lake (Synthetic)",
    "geometry": _LAKE_GEOM,
    "anomaly_sigma": 3.5,
    "forecast_value": 30.0,
    "intakes_threatened": 1,
    "recreation_sites_threatened": 1,
}


# ── should_alert_hab ──────────────────────────────────────────────────────────


def test_should_alert_hab_both_above_threshold_returns_true() -> None:
    anomaly = _make_anomaly_pred(z_score=3.5)
    forecast = _make_forecast_pred(value=30.0)
    assert should_alert_hab(anomaly, forecast) is True


def test_should_alert_hab_anomaly_below_threshold_returns_false() -> None:
    anomaly = _make_anomaly_pred(z_score=1.0)   # < 2.5 sigma
    forecast = _make_forecast_pred(value=30.0)
    assert should_alert_hab(anomaly, forecast) is False


def test_should_alert_hab_forecast_below_threshold_returns_false() -> None:
    anomaly = _make_anomaly_pred(z_score=3.5)
    forecast = _make_forecast_pred(value=10.0)  # < 25.0 µg/L
    assert should_alert_hab(anomaly, forecast) is False


def test_should_alert_hab_both_below_threshold_returns_false() -> None:
    anomaly = _make_anomaly_pred(z_score=1.0)
    forecast = _make_forecast_pred(value=10.0)
    assert should_alert_hab(anomaly, forecast) is False


def test_should_alert_hab_custom_thresholds() -> None:
    anomaly = _make_anomaly_pred(z_score=3.0)
    forecast = _make_forecast_pred(value=20.0)
    # With default thresholds: 3.0 > 2.5 but 20.0 < 25.0 → False
    assert should_alert_hab(anomaly, forecast) is False
    # With lower thresholds: should fire
    assert should_alert_hab(anomaly, forecast, bloom_risk_threshold=15.0) is True


# ── create_hab_alert ──────────────────────────────────────────────────────────


def test_create_hab_alert_domain_is_inland_wq() -> None:
    alert = create_hab_alert(
        "reference_lake", "Reference Lake",
        _make_anomaly_pred(), _make_forecast_pred(),
    )
    assert alert.domain == "inland_wq"


def test_create_hab_alert_target_is_name() -> None:
    alert = create_hab_alert(
        "reference_lake", "Reference Lake",
        _make_anomaly_pred(), _make_forecast_pred(),
    )
    assert alert.target == "Reference Lake"


def test_create_hab_alert_message_contains_waterbody_name() -> None:
    alert = create_hab_alert(
        "reference_lake", "Reference Lake",
        _make_anomaly_pred(), _make_forecast_pred(),
    )
    assert "Reference Lake" in alert.message


def test_create_hab_alert_message_contains_anomaly_sigma() -> None:
    alert = create_hab_alert(
        "reference_lake", "Reference Lake",
        _make_anomaly_pred(z_score=3.5), _make_forecast_pred(),
    )
    assert "3.5" in alert.message


def test_create_hab_alert_message_contains_forecast_value() -> None:
    alert = create_hab_alert(
        "reference_lake", "Reference Lake",
        _make_anomaly_pred(), _make_forecast_pred(value=30.0),
    )
    assert "30.0" in alert.message


def test_create_hab_alert_message_contains_intakes_count() -> None:
    alert = create_hab_alert(
        "reference_lake", "Reference Lake",
        _make_anomaly_pred(), _make_forecast_pred(),
        intakes_threatened=2,
    )
    assert "2" in alert.message
    assert "intake" in alert.message


def test_create_hab_alert_details_has_anomaly_sigma() -> None:
    alert = create_hab_alert(
        "reference_lake", "Reference Lake",
        _make_anomaly_pred(z_score=3.5), _make_forecast_pred(),
    )
    assert "anomaly_sigma" in alert.details
    assert abs(alert.details["anomaly_sigma"] - 3.5) < 0.01


def test_create_hab_alert_details_has_bloom_risk_forecast() -> None:
    alert = create_hab_alert(
        "reference_lake", "Reference Lake",
        _make_anomaly_pred(), _make_forecast_pred(value=30.0),
    )
    assert alert.details["bloom_risk_forecast"] == pytest.approx(30.0, abs=0.01)


def test_create_hab_alert_details_has_intakes_threatened() -> None:
    alert = create_hab_alert(
        "reference_lake", "Reference Lake",
        _make_anomaly_pred(), _make_forecast_pred(),
        intakes_threatened=1,
    )
    assert alert.details["intakes_threatened"] == 1


def test_create_hab_alert_details_has_target_id() -> None:
    alert = create_hab_alert(
        "reference_lake", "Reference Lake",
        _make_anomaly_pred(), _make_forecast_pred(),
    )
    assert alert.details["target_id"] == "reference_lake"


def test_create_hab_alert_prediction_id_is_forecast_id() -> None:
    forecast = _make_forecast_pred()
    alert = create_hab_alert("reference_lake", "Reference Lake", _make_anomaly_pred(), forecast)
    assert alert.prediction_id == forecast.id


def test_create_hab_alert_observation_id_from_anomaly_source_obs() -> None:
    anomaly = _make_anomaly_pred()
    alert = create_hab_alert("reference_lake", "Reference Lake", anomaly, _make_forecast_pred())
    assert alert.observation_id == anomaly.source_obs_ids[0]


def test_create_hab_alert_status_is_pending() -> None:
    alert = create_hab_alert(
        "reference_lake", "Reference Lake",
        _make_anomaly_pred(), _make_forecast_pred(),
    )
    assert alert.status == "pending"


# ── to_payload includes details ───────────────────────────────────────────────


def test_hab_alert_payload_includes_details() -> None:
    alert = create_hab_alert(
        "reference_lake", "Reference Lake",
        _make_anomaly_pred(), _make_forecast_pred(),
        intakes_threatened=1,
    )
    payload = alert.to_payload()
    assert "details" in payload
    assert payload["details"]["intakes_threatened"] == 1


def test_alert_without_details_payload_omits_details_key() -> None:
    alert = Alert(domain="inland_wq", target="Test Lake")
    payload = alert.to_payload()
    assert "details" not in payload


# ── send_alert with HAB alert ─────────────────────────────────────────────────


def test_send_hab_alert_via_webhook(tmp_path: Path) -> None:
    alert = create_hab_alert(
        "reference_lake", "Reference Lake",
        _make_anomaly_pred(), _make_forecast_pred(),
        intakes_threatened=1,
    )
    channel = AlertChannel(kind="webhook", url="http://mock.example.com/webhook")
    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_session.post.return_value = mock_resp

    result = send_alert(alert, [channel], session=mock_session)
    assert result.status == "sent"
    assert mock_session.post.called


def test_send_hab_alert_no_channels_remains_pending() -> None:
    alert = create_hab_alert(
        "reference_lake", "Reference Lake",
        _make_anomaly_pred(), _make_forecast_pred(),
    )
    result = send_alert(alert, [])
    assert result.status == "pending"


# ── WQ product exports ────────────────────────────────────────────────────────


def test_export_wq_geojson_creates_file(tmp_path: Path) -> None:
    path = tmp_path / "wq.geojson"
    result = export_wq_geojson([_WB_ENTRY], path)
    assert result.exists()


def test_export_wq_geojson_is_feature_collection(tmp_path: Path) -> None:
    path = tmp_path / "wq.geojson"
    export_wq_geojson([_WB_ENTRY], path)
    data = json.loads(path.read_text())
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 1


def test_export_wq_geojson_properties_include_anomaly_sigma(tmp_path: Path) -> None:
    path = tmp_path / "wq.geojson"
    export_wq_geojson([_WB_ENTRY], path)
    props = json.loads(path.read_text())["features"][0]["properties"]
    assert props["anomaly_sigma"] == pytest.approx(3.5)


def test_export_wq_geojson_properties_include_intakes_threatened(tmp_path: Path) -> None:
    path = tmp_path / "wq.geojson"
    export_wq_geojson([_WB_ENTRY], path)
    props = json.loads(path.read_text())["features"][0]["properties"]
    assert props["intakes_threatened"] == 1


def test_export_wq_summary_creates_file(tmp_path: Path) -> None:
    path = tmp_path / "summary.json"
    result = export_wq_summary([_WB_ENTRY], path)
    assert result.exists()


def test_export_wq_summary_ranked_by_risk(tmp_path: Path) -> None:
    low_risk = {**_WB_ENTRY, "target_id": "low_risk_lake", "anomaly_sigma": 0.5, "forecast_value": 5.0}
    path = tmp_path / "summary.json"
    export_wq_summary([low_risk, _WB_ENTRY], path)
    data = json.loads(path.read_text())
    # Higher risk should be rank 1
    assert data["water_bodies"][0]["target_id"] == "reference_lake"
    assert data["water_bodies"][1]["target_id"] == "low_risk_lake"


def test_export_wq_products_creates_all_artifacts(tmp_path: Path) -> None:
    artifacts = export_wq_products([_WB_ENTRY], tmp_path / "wq_out")
    assert "geojson" in artifacts
    assert "png" in artifacts
    assert "summary" in artifacts
    assert artifacts["geojson"].exists()
    assert artifacts["png"].exists()
    assert artifacts["summary"].exists()


def test_export_wq_products_png_is_nonempty(tmp_path: Path) -> None:
    artifacts = export_wq_products([_WB_ENTRY], tmp_path / "wq_out")
    assert artifacts["png"].stat().st_size > 0


def test_export_wq_products_summary_has_water_bodies(tmp_path: Path) -> None:
    artifacts = export_wq_products([_WB_ENTRY], tmp_path / "wq_out")
    data = json.loads(artifacts["summary"].read_text())
    assert len(data["water_bodies"]) == 1
    assert data["water_bodies"][0]["intakes_threatened"] == 1
