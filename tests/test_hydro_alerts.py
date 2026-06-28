"""Tests for F-044: FloodRisk and AcidDepositionRisk alert functions.

All tests are offline (INV-7).  Synthetic Prediction objects are used.

Acceptance criteria:
  - FloodRisk alert fires for synthetic high-risk scenario (risk_level="high"/"extreme")
  - AcidDepositionRisk alert fires when acid_risk_index >= 7.0
  - Alert payloads include honesty labels (not measurements, advisory only)
  - Alert.domain is "weather_hydro" for both
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest

from argus.alert.delivery import (
    Alert,
    create_acid_risk_alert,
    create_flood_risk_alert,
    should_alert_acid_risk,
    should_alert_flood_risk,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _flood_pred(
    risk_level: str = "high",
    risk_score: float = 0.65,
    peak_precip: float = 150.0,
    peak_discharge: float = 800.0,
) -> Any:
    return SimpleNamespace(
        id=str(uuid.uuid4()),
        predictor_id="FloodRisk",
        kind="risk",
        evidence_class="modeled",
        source_obs_ids=[str(uuid.uuid4())],
        created_at=datetime(2024, 6, 1, tzinfo=UTC),
        attrs={
            "risk_level": risk_level,
            "label": "modeled flood risk at choke point (not a measured flood)",
            "peak_precip_mm": peak_precip,
            "peak_discharge_m3s": peak_discharge,
            "choke_point_count": 2,
            "aoi_id": "tobago",
        },
        uncertainty={
            "risk_score": risk_score,
            "model_type": "rule_based",
        },
    )


def _acid_pred(
    acid_index: float = 7.5,
    peak_so2: float = 55.0,
) -> Any:
    return SimpleNamespace(
        id=str(uuid.uuid4()),
        predictor_id="AcidDepositionRisk",
        kind="risk",
        evidence_class="modeled",
        source_obs_ids=[str(uuid.uuid4())],
        created_at=datetime(2024, 6, 1, tzinfo=UTC),
        attrs={
            "acid_risk_index": acid_index,
            "label": "modeled acid-deposition risk index (0–10 scale) — NOT a pH measurement",
            "peak_so2_ug_m3": peak_so2,
            "aoi_id": "tobago",
        },
        uncertainty={
            "index_range": [max(0.0, acid_index - 1.5), min(10.0, acid_index + 1.5)],
            "methodology": "SO2 × NO2 × precip × catchment sensitivity index",
        },
    )


# ── should_alert_flood_risk ───────────────────────────────────────────────────


def test_flood_alert_fires_for_high() -> None:
    assert should_alert_flood_risk(_flood_pred(risk_level="high")) is True


def test_flood_alert_fires_for_extreme() -> None:
    assert should_alert_flood_risk(_flood_pred(risk_level="extreme")) is True


def test_flood_alert_silent_for_medium() -> None:
    assert should_alert_flood_risk(_flood_pred(risk_level="medium")) is False


def test_flood_alert_silent_for_low() -> None:
    assert should_alert_flood_risk(_flood_pred(risk_level="low")) is False


def test_flood_alert_silent_missing_risk_level() -> None:
    pred = _flood_pred()
    pred.attrs.pop("risk_level")
    assert should_alert_flood_risk(pred) is False


# ── create_flood_risk_alert ───────────────────────────────────────────────────


@pytest.fixture()
def high_flood_pred() -> Any:
    return _flood_pred(risk_level="high", risk_score=0.65)


def test_flood_alert_is_alert_instance(high_flood_pred: Any) -> None:
    alert = create_flood_risk_alert("tobago", "Tobago", high_flood_pred)
    assert isinstance(alert, Alert)


def test_flood_alert_domain_is_weather_hydro(high_flood_pred: Any) -> None:
    alert = create_flood_risk_alert("tobago", "Tobago", high_flood_pred)
    assert alert.domain == "weather_hydro"


def test_flood_alert_target_is_aoi_name(high_flood_pred: Any) -> None:
    alert = create_flood_risk_alert("tobago", "Tobago Island", high_flood_pred)
    assert alert.target == "Tobago Island"


def test_flood_alert_prediction_id_set(high_flood_pred: Any) -> None:
    alert = create_flood_risk_alert("tobago", "Tobago", high_flood_pred)
    assert alert.prediction_id == high_flood_pred.id


def test_flood_alert_message_mentions_risk_level(high_flood_pred: Any) -> None:
    alert = create_flood_risk_alert("tobago", "Tobago", high_flood_pred)
    assert "high" in alert.message.lower()


def test_flood_alert_message_mentions_precip(high_flood_pred: Any) -> None:
    alert = create_flood_risk_alert("tobago", "Tobago", high_flood_pred)
    assert "150" in alert.message or "precip" in alert.message


def test_flood_alert_confidence_matches_risk_score(high_flood_pred: Any) -> None:
    alert = create_flood_risk_alert("tobago", "Tobago", high_flood_pred)
    assert alert.confidence == pytest.approx(0.65)


def test_flood_alert_details_include_label(high_flood_pred: Any) -> None:
    alert = create_flood_risk_alert("tobago", "Tobago", high_flood_pred)
    assert "not a measured" in alert.details.get("label", "").lower()


def test_flood_alert_details_include_choke_point_count(high_flood_pred: Any) -> None:
    alert = create_flood_risk_alert(
        "tobago", "Tobago", high_flood_pred, choke_point_count=3
    )
    assert alert.details["choke_point_count"] == 3


def test_flood_alert_status_is_pending(high_flood_pred: Any) -> None:
    alert = create_flood_risk_alert("tobago", "Tobago", high_flood_pred)
    assert alert.status == "pending"


# ── should_alert_acid_risk ────────────────────────────────────────────────────


def test_acid_alert_fires_at_threshold() -> None:
    assert should_alert_acid_risk(_acid_pred(acid_index=7.0)) is True


def test_acid_alert_fires_above_threshold() -> None:
    assert should_alert_acid_risk(_acid_pred(acid_index=9.5)) is True


def test_acid_alert_silent_below_threshold() -> None:
    assert should_alert_acid_risk(_acid_pred(acid_index=6.9)) is False


def test_acid_alert_silent_at_zero() -> None:
    assert should_alert_acid_risk(_acid_pred(acid_index=0.0)) is False


def test_acid_alert_silent_missing_index() -> None:
    pred = _acid_pred()
    pred.attrs.pop("acid_risk_index")
    assert should_alert_acid_risk(pred) is False


# ── create_acid_risk_alert ────────────────────────────────────────────────────


@pytest.fixture()
def high_acid_pred() -> Any:
    return _acid_pred(acid_index=8.2, peak_so2=60.0)


def test_acid_alert_is_alert_instance(high_acid_pred: Any) -> None:
    alert = create_acid_risk_alert("tobago", "Tobago", high_acid_pred)
    assert isinstance(alert, Alert)


def test_acid_alert_domain_is_weather_hydro(high_acid_pred: Any) -> None:
    alert = create_acid_risk_alert("tobago", "Tobago", high_acid_pred)
    assert alert.domain == "weather_hydro"


def test_acid_alert_target_is_aoi_name(high_acid_pred: Any) -> None:
    alert = create_acid_risk_alert("tobago", "Tobago Island", high_acid_pred)
    assert alert.target == "Tobago Island"


def test_acid_alert_message_says_not_ph(high_acid_pred: Any) -> None:
    """Honesty check — alert message must explicitly state this is NOT a pH measurement."""
    alert = create_acid_risk_alert("tobago", "Tobago", high_acid_pred)
    assert "NOT a pH measurement" in alert.message


def test_acid_alert_message_includes_index(high_acid_pred: Any) -> None:
    alert = create_acid_risk_alert("tobago", "Tobago", high_acid_pred)
    assert "8.2" in alert.message


def test_acid_alert_message_includes_so2(high_acid_pred: Any) -> None:
    alert = create_acid_risk_alert("tobago", "Tobago", high_acid_pred)
    assert "60" in alert.message or "SO" in alert.message


def test_acid_alert_confidence_scaled_to_index(high_acid_pred: Any) -> None:
    alert = create_acid_risk_alert("tobago", "Tobago", high_acid_pred)
    assert alert.confidence == pytest.approx(0.82, abs=0.01)


def test_acid_alert_details_include_label(high_acid_pred: Any) -> None:
    alert = create_acid_risk_alert("tobago", "Tobago", high_acid_pred)
    assert "NOT a pH measurement" in alert.details.get("label", "")


def test_acid_alert_status_is_pending(high_acid_pred: Any) -> None:
    alert = create_acid_risk_alert("tobago", "Tobago", high_acid_pred)
    assert alert.status == "pending"


def test_acid_alert_prediction_id_set(high_acid_pred: Any) -> None:
    alert = create_acid_risk_alert("tobago", "Tobago", high_acid_pred)
    assert alert.prediction_id == high_acid_pred.id
