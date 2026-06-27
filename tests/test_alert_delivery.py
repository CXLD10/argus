"""F-017 tests: alert delivery (webhook, email, no-op) and metadata export."""

from __future__ import annotations

import json
import smtplib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import responses as resp_mock

from argus.alert.delivery import Alert, AlertChannel, load_channels, send_alert
from argus.core.models import AnalysisRun, ImpactAssessment, Observation, Prediction
from argus.export.products import export_metadata, export_products

# ── Fixtures ──────────────────────────────────────────────────────────────────

_GEOM = {
    "type": "Polygon",
    "coordinates": [[[-61.4, 11.0], [-61.1, 11.0], [-61.1, 11.3], [-61.4, 11.3], [-61.4, 11.0]]],
}

_WEBHOOK_URL = "https://hooks.example.com/argus"


def _make_alert(**kwargs) -> Alert:
    return Alert(
        domain="marine_oil",
        target="tobago",
        observation_id="obs-001",
        confidence=0.9,
        eta_hours=24.0,
        **kwargs,
    )


def _make_run() -> AnalysisRun:
    from datetime import UTC, datetime

    return AnalysisRun(
        id="run-001",
        aoi_id="tobago",
        domain_id="marine_oil",
        scene_id="scene-001",
        started_at=datetime.now(UTC),
        status="complete",
    )


def _make_obs() -> Observation:
    return Observation(
        id="obs-001",
        analysis_run_id="run-001",
        scene_id="scene-001",
        obs_type="oil_slick",
        evidence_class="measured",
        geometry=_GEOM,
        area_km2=5.0,
        confidence=0.85,
    )


def _make_prediction() -> Prediction:
    return Prediction(
        id="pred-001",
        predictor_id="oil_trajectory_v1",
        kind="trajectory",
        uncertainty={"particle_spread_km": 18.0},
        rng_seed=42,
    )


def _make_impact() -> ImpactAssessment:
    from datetime import UTC, datetime

    return ImpactAssessment(
        id="ia-001",
        prediction_id="pred-001",
        exposure_layer_id="coast-tobago",
        valid_at=datetime(2024, 2, 8, tzinfo=UTC),
        eta_hours=24.0,
        metrics={"coast_length_km": 12.5},
    )


# ── Alert model ───────────────────────────────────────────────────────────────


def test_alert_default_status_pending() -> None:
    a = _make_alert()
    assert a.status == "pending"


def test_alert_payload_contains_required_keys() -> None:
    a = _make_alert()
    payload = a.to_payload()
    for key in ("id", "domain", "target", "confidence", "eta_hours", "created_at"):
        assert key in payload


def test_alert_payload_domain() -> None:
    a = _make_alert()
    assert a.to_payload()["domain"] == "marine_oil"


def test_alert_payload_observation_id() -> None:
    a = _make_alert()
    assert a.to_payload()["observation_id"] == "obs-001"


# ── load_channels ─────────────────────────────────────────────────────────────


def test_load_channels_missing_file_returns_empty(tmp_path: Path) -> None:
    channels = load_channels(tmp_path / "nonexistent.yaml")
    assert channels == []


def test_load_channels_empty_channels_key(tmp_path: Path) -> None:
    cfg = tmp_path / "alert_channels.yaml"
    cfg.write_text("channels: []\n")
    assert load_channels(cfg) == []


def test_load_channels_webhook(tmp_path: Path) -> None:
    cfg = tmp_path / "alert_channels.yaml"
    cfg.write_text(f"channels:\n  - kind: webhook\n    url: {_WEBHOOK_URL}\n")
    channels = load_channels(cfg)
    assert len(channels) == 1
    assert channels[0].kind == "webhook"
    assert channels[0].url == _WEBHOOK_URL


def test_load_channels_email(tmp_path: Path) -> None:
    cfg = tmp_path / "alert_channels.yaml"
    cfg.write_text(
        "channels:\n"
        "  - kind: email\n"
        "    smtp_host: smtp.example.com\n"
        "    smtp_port: 587\n"
        "    from: argus@example.com\n"
        "    to:\n"
        "      - ops@example.com\n"
    )
    channels = load_channels(cfg)
    assert len(channels) == 1
    assert channels[0].kind == "email"
    assert channels[0].smtp_host == "smtp.example.com"
    assert "ops@example.com" in channels[0].to_addrs


# ── send_alert: no-op ─────────────────────────────────────────────────────────


def test_send_alert_no_channels_is_noop() -> None:
    alert = _make_alert()
    result = send_alert(alert, channels=[])
    assert result.status == "pending"


def test_send_alert_empty_channels_does_not_raise() -> None:
    alert = _make_alert()
    send_alert(alert, channels=[])  # must not raise


# ── send_alert: webhook ───────────────────────────────────────────────────────


@resp_mock.activate
def test_send_alert_webhook_posts_to_url() -> None:
    resp_mock.add(resp_mock.POST, _WEBHOOK_URL, json={"ok": True}, status=200)
    channel = AlertChannel(kind="webhook", url=_WEBHOOK_URL)
    alert = send_alert(_make_alert(), channels=[channel])
    assert len(resp_mock.calls) == 1
    assert alert.status == "sent"


@resp_mock.activate
def test_send_alert_webhook_payload_is_json() -> None:
    resp_mock.add(resp_mock.POST, _WEBHOOK_URL, json={"ok": True}, status=200)
    channel = AlertChannel(kind="webhook", url=_WEBHOOK_URL)
    send_alert(_make_alert(), channels=[channel])
    body = json.loads(resp_mock.calls[0].request.body)
    assert body["domain"] == "marine_oil"
    assert body["confidence"] == pytest.approx(0.9)


@resp_mock.activate
def test_send_alert_webhook_failure_sets_failed() -> None:
    resp_mock.add(resp_mock.POST, _WEBHOOK_URL, status=500)
    channel = AlertChannel(kind="webhook", url=_WEBHOOK_URL)
    alert = send_alert(_make_alert(), channels=[channel])
    assert alert.status == "failed"


# ── send_alert: email ─────────────────────────────────────────────────────────


def test_send_alert_email_sends_message() -> None:
    channel = AlertChannel(
        kind="email",
        smtp_host="smtp.example.com",
        smtp_port=587,
        from_addr="argus@example.com",
        to_addrs=["ops@example.com"],
    )
    mock_smtp = MagicMock()
    with patch("smtplib.SMTP", return_value=mock_smtp) as smtp_cls:
        smtp_cls.return_value.__enter__ = lambda s: mock_smtp
        smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
        alert = send_alert(_make_alert(), channels=[channel])
    assert alert.status == "sent"
    mock_smtp.send_message.assert_called_once()


def test_send_alert_email_subject_contains_domain() -> None:
    channel = AlertChannel(
        kind="email",
        smtp_host="smtp.example.com",
        smtp_port=587,
        from_addr="argus@example.com",
        to_addrs=["ops@example.com"],
    )
    captured: list = []
    mock_smtp = MagicMock()
    mock_smtp.send_message.side_effect = lambda msg: captured.append(msg)

    with patch("smtplib.SMTP", return_value=mock_smtp) as smtp_cls:
        smtp_cls.return_value.__enter__ = lambda s: mock_smtp
        smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
        send_alert(_make_alert(), channels=[channel])

    assert captured
    subject = captured[0]["Subject"]
    assert "marine_oil" in subject


def test_send_alert_email_failure_sets_failed() -> None:
    channel = AlertChannel(
        kind="email",
        smtp_host="smtp.example.com",
        smtp_port=587,
        from_addr="argus@example.com",
        to_addrs=["ops@example.com"],
    )
    with patch("smtplib.SMTP", side_effect=smtplib.SMTPException("connection refused")):
        alert = send_alert(_make_alert(), channels=[channel])
    assert alert.status == "failed"


# ── export_metadata ───────────────────────────────────────────────────────────


def test_export_metadata_creates_file(tmp_path: Path) -> None:
    path = tmp_path / "meta.json"
    export_metadata(_make_run(), [_make_obs()], path)
    assert path.exists()


def test_export_metadata_is_valid_json(tmp_path: Path) -> None:
    path = tmp_path / "meta.json"
    export_metadata(_make_run(), [_make_obs()], path)
    data = json.loads(path.read_text())
    assert isinstance(data, dict)


def test_export_metadata_n_observations(tmp_path: Path) -> None:
    path = tmp_path / "meta.json"
    export_metadata(_make_run(), [_make_obs(), _make_obs()], path)
    data = json.loads(path.read_text())
    assert data["n_observations"] == 2


def test_export_metadata_includes_prediction(tmp_path: Path) -> None:
    path = tmp_path / "meta.json"
    export_metadata(_make_run(), [_make_obs()], path, prediction=_make_prediction())
    data = json.loads(path.read_text())
    assert "prediction" in data
    assert data["prediction"]["id"] == "pred-001"


def test_export_metadata_includes_impact(tmp_path: Path) -> None:
    path = tmp_path / "meta.json"
    export_metadata(_make_run(), [_make_obs()], path, impact=[_make_impact()])
    data = json.loads(path.read_text())
    assert "impact" in data
    assert data["impact"][0]["eta_hours"] == pytest.approx(24.0)


def test_export_metadata_no_prediction_key_when_absent(tmp_path: Path) -> None:
    path = tmp_path / "meta.json"
    export_metadata(_make_run(), [_make_obs()], path)
    data = json.loads(path.read_text())
    assert "prediction" not in data


# ── export_products: metadata artifact ───────────────────────────────────────


def test_export_products_metadata_key_present(tmp_path: Path) -> None:
    import numpy as np

    from argus.preprocess.landmask import GeoTransform
    from argus.preprocess.sar import preprocess

    rng = np.random.default_rng(42)
    vv = rng.uniform(5e-4, 2e-3, (50, 50)).astype(np.float32)
    vh = rng.uniform(5e-5, 2e-4, (50, 50)).astype(np.float32)
    transform = GeoTransform(
        min_lon=-61.4, min_lat=11.0, max_lon=-61.1, max_lat=11.3, cols=50, rows=50
    )
    land_mask = np.zeros((50, 50), dtype=bool)
    prep = preprocess(vv, vh, land_mask, transform, "synthetic-001")

    artifacts = export_products([_make_obs()], _make_run(), prep, tmp_path / "out")
    assert "metadata" in artifacts
    assert artifacts["metadata"].exists()


def test_export_products_metadata_valid_json(tmp_path: Path) -> None:
    import numpy as np

    from argus.preprocess.landmask import GeoTransform
    from argus.preprocess.sar import preprocess

    rng = np.random.default_rng(42)
    vv = rng.uniform(5e-4, 2e-3, (50, 50)).astype(np.float32)
    vh = rng.uniform(5e-5, 2e-4, (50, 50)).astype(np.float32)
    transform = GeoTransform(
        min_lon=-61.4, min_lat=11.0, max_lon=-61.1, max_lat=11.3, cols=50, rows=50
    )
    land_mask = np.zeros((50, 50), dtype=bool)
    prep = preprocess(vv, vh, land_mask, transform, "synthetic-001")

    artifacts = export_products([_make_obs()], _make_run(), prep, tmp_path / "out")
    data = json.loads(artifacts["metadata"].read_text())
    assert data["aoi_id"] == "tobago"
