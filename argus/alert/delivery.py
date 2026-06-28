"""Alert delivery: webhook (HTTP POST) and email (SMTP).

Channel config is loaded from config/alert_channels.yaml. If no channels are
configured (file absent or empty list), send_alert() is a silent no-op.
No credentials may appear in log output.
"""

from __future__ import annotations

import json
import smtplib
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import requests
import yaml


@dataclass
class AlertChannel:
    """Single alerting destination."""

    kind: str  # "webhook" | "email"
    # Webhook fields
    url: str | None = None
    # Email fields
    smtp_host: str | None = None
    smtp_port: int = 587
    from_addr: str | None = None
    to_addrs: list[str] = field(default_factory=list)
    username: str | None = None
    password: str | None = None


@dataclass
class Alert:
    """One alert payload, with lifecycle status tracking."""

    domain: str
    target: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    observation_id: str | None = None
    prediction_id: str | None = None
    confidence: float = 0.0
    eta_hours: float | None = None
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending | sent | failed
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_payload(self) -> dict[str, Any]:
        """Serialise alert to a JSON-safe dict for transport."""
        payload: dict[str, Any] = {
            "id": self.id,
            "domain": self.domain,
            "target": self.target,
            "observation_id": self.observation_id,
            "prediction_id": self.prediction_id,
            "confidence": self.confidence,
            "eta_hours": self.eta_hours,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
        }
        if self.details:
            payload["details"] = self.details
        return payload


def load_channels(path: Path) -> list[AlertChannel]:
    """Load alert channels from YAML; return empty list if file absent."""
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text()) or {}
    raw_channels: list[dict[str, Any]] = data.get("channels", [])
    channels = []
    for ch in raw_channels:
        kind = ch.get("kind", "")
        if kind == "webhook":
            channels.append(AlertChannel(kind="webhook", url=ch.get("url")))
        elif kind == "email":
            channels.append(
                AlertChannel(
                    kind="email",
                    smtp_host=ch.get("smtp_host"),
                    smtp_port=int(ch.get("smtp_port", 587)),
                    from_addr=ch.get("from"),
                    to_addrs=ch.get("to", []),
                    username=ch.get("username"),
                    password=ch.get("password"),
                )
            )
    return channels


def _send_webhook(alert: Alert, channel: AlertChannel, *, session: requests.Session | None) -> None:
    s = session or requests.Session()
    resp = s.post(
        channel.url or "",
        data=json.dumps(alert.to_payload()),
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    resp.raise_for_status()


def _send_email(alert: Alert, channel: AlertChannel) -> None:
    msg = EmailMessage()
    msg["From"] = channel.from_addr or ""
    msg["To"] = ", ".join(channel.to_addrs)
    msg["Subject"] = f"[Argus] {alert.domain} alert — {alert.target}"
    body_lines = [
        f"Domain: {alert.domain}",
        f"Target: {alert.target}",
        f"Confidence: {alert.confidence:.0%}",
    ]
    if alert.eta_hours is not None:
        body_lines.append(f"ETA: {alert.eta_hours:.1f} hours")
    if alert.message:
        body_lines.append(f"\n{alert.message}")
    if alert.observation_id:
        body_lines.append(f"\nObservation ID: {alert.observation_id}")
    if alert.prediction_id:
        body_lines.append(f"Prediction ID: {alert.prediction_id}")
    msg.set_content("\n".join(body_lines))

    with smtplib.SMTP(channel.smtp_host or "localhost", channel.smtp_port) as smtp:
        if channel.username and channel.password:
            smtp.login(channel.username, channel.password)
        smtp.send_message(msg)


_HAB_ALERT_SIGMA_THRESHOLD: float = 2.5   # z-score threshold for anomaly trigger
_HAB_BLOOM_RISK_THRESHOLD: float = 25.0   # µg/L chlorophyll-a threshold for forecast trigger


def should_alert_hab(
    anomaly_pred: Any,
    forecast_pred: Any,
    *,
    alert_sigma_threshold: float = _HAB_ALERT_SIGMA_THRESHOLD,
    bloom_risk_threshold: float = _HAB_BLOOM_RISK_THRESHOLD,
) -> bool:
    """Return True when BOTH anomaly AND forecast exceed their thresholds.

    HAB early-warning fires only when two independent signals align:
    - anomaly z_score > threshold (current deviation from baseline)
    - forecast value > bloom_risk_threshold (predicted bloom in 7 days)

    This dual-signal gate reduces false positives (INV-3: advisory, not automated action).
    """
    anomaly_sigma = abs(float(anomaly_pred.attrs.get("z_score", 0.0)))
    forecast_value = float(forecast_pred.attrs.get("value", 0.0))
    return bool(anomaly_sigma > alert_sigma_threshold and forecast_value > bloom_risk_threshold)


def create_hab_alert(
    target_id: str,
    target_name: str,
    anomaly_pred: Any,
    forecast_pred: Any,
    *,
    intakes_threatened: int = 0,
    recreation_sites_threatened: int = 0,
) -> Alert:
    """Create an Alert for a HAB (Harmful Algal Bloom) early-warning event.

    The alert is advisory only — no automated action is taken. The payload includes
    the water body name, anomaly sigma, bloom-risk forecast value, and impact counts
    for downstream human review.
    """
    anomaly_sigma = round(abs(anomaly_pred.attrs.get("z_score", 0.0)), 4)
    forecast_value = round(forecast_pred.attrs.get("value", 0.0), 4)
    horizon_days = forecast_pred.attrs.get("horizon_days", 7)

    message = (
        f"HAB early-warning: {target_name} — "
        f"anomaly z={anomaly_sigma:.1f}σ, "
        f"forecast chl-a={forecast_value:.1f} µg/L ({horizon_days}d horizon)"
    )
    if intakes_threatened:
        message += f", {intakes_threatened} intake(s) at risk"
    if recreation_sites_threatened:
        message += f", {recreation_sites_threatened} recreation site(s) at risk"

    return Alert(
        domain="inland_wq",
        target=target_name,
        observation_id=anomaly_pred.source_obs_ids[0] if anomaly_pred.source_obs_ids else None,
        prediction_id=forecast_pred.id,
        confidence=min(anomaly_sigma / 5.0, 1.0),  # scaled 0–1
        message=message,
        details={
            "target_id": target_id,
            "anomaly_sigma": anomaly_sigma,
            "bloom_risk_forecast": forecast_value,
            "intakes_threatened": intakes_threatened,
            "recreation_sites_threatened": recreation_sites_threatened,
            "horizon_days": horizon_days,
        },
    )


def send_alert(
    alert: Alert,
    channels: list[AlertChannel],
    *,
    session: requests.Session | None = None,
) -> Alert:
    """Deliver *alert* to all configured channels; update alert.status.

    Returns the same Alert with status set to "sent" or "failed".
    If channels is empty, returns the alert unchanged (status stays "pending").
    """
    if not channels:
        return alert

    last_exc: Exception | None = None
    for channel in channels:
        try:
            if channel.kind == "webhook":
                _send_webhook(alert, channel, session=session)
            elif channel.kind == "email":
                _send_email(alert, channel)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            continue

    alert.status = "failed" if last_exc is not None else "sent"
    return alert
