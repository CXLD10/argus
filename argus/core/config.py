"""Argus configuration: load settings.yaml + environment variable overrides."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from argus.core.errors import ConfigError  # noqa: E402 — re-export for backward compat

_REPO_ROOT = Path(__file__).parent.parent.parent
_DEFAULT_SETTINGS_PATH = _REPO_ROOT / "config" / "settings.yaml"

__all__ = ["ConfigError"]


class CdseConfig(BaseModel):
    user: str = ""
    password: str = ""
    daily_quota_gb: float = 1.0


class OpenMeteoConfig(BaseModel):
    daily_call_limit: int = 10000
    attribution: str = "Weather data by Open-Meteo (https://open-meteo.com/) — CC BY 4.0"


class CmemsConfig(BaseModel):
    user: str = ""
    password: str = ""


class AiConfig(BaseModel):
    offline: bool = False
    model: str = "claude-haiku-4-5-20251001"
    max_tokens: int = 2048


class StoreConfig(BaseModel):
    db_path: Path = Path("data/argus.db")
    artifact_dir: Path = Path("data/artifacts")


class AlertsConfig(BaseModel):
    webhook_url: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    from_address: str = ""


class LoggingConfig(BaseModel):
    format: str = "text"
    level: str = "INFO"


class AnomalyDetectorConfig(BaseModel):
    default_alert_sigma: float = 2.5


class WaterQualityForecastConfig(BaseModel):
    horizon_days: int = 14


class OilTrajectoryConfig(BaseModel):
    simulation_hours: int = 72
    particle_count: int = 1000


class PredictionConfig(BaseModel):
    anomaly_detector: AnomalyDetectorConfig = Field(default_factory=AnomalyDetectorConfig)
    water_quality_forecast: WaterQualityForecastConfig = Field(
        default_factory=WaterQualityForecastConfig
    )
    oil_trajectory: OilTrajectoryConfig = Field(default_factory=OilTrajectoryConfig)


class Settings(BaseModel):
    cdse: CdseConfig = Field(default_factory=CdseConfig)
    open_meteo: OpenMeteoConfig = Field(default_factory=OpenMeteoConfig)
    cmems: CmemsConfig = Field(default_factory=CmemsConfig)
    ai: AiConfig = Field(default_factory=AiConfig)
    store: StoreConfig = Field(default_factory=StoreConfig)
    alerts: AlertsConfig = Field(default_factory=AlertsConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    prediction: PredictionConfig = Field(default_factory=PredictionConfig)


# Explicit mapping of env vars to (section, field) paths.
# Add entries here when new overrideable fields are added to settings.yaml.
_ENV_MAP: dict[str, tuple[str, str]] = {
    "ARGUS_CDSE_USER": ("cdse", "user"),
    "ARGUS_CDSE_PASSWORD": ("cdse", "password"),
    "ARGUS_OPEN_METEO_DAILY_CALL_LIMIT": ("open_meteo", "daily_call_limit"),
    "ARGUS_CMEMS_USER": ("cmems", "user"),
    "ARGUS_CMEMS_PASSWORD": ("cmems", "password"),
    "ARGUS_AI_OFFLINE": ("ai", "offline"),
    "ARGUS_AI_MODEL": ("ai", "model"),
    "ARGUS_STORE_DB_PATH": ("store", "db_path"),
    "ARGUS_STORE_ARTIFACT_DIR": ("store", "artifact_dir"),
    "ARGUS_ALERTS_WEBHOOK_URL": ("alerts", "webhook_url"),
    "ARGUS_LOGGING_FORMAT": ("logging", "format"),
    "ARGUS_LOGGING_LEVEL": ("logging", "level"),
}


def _apply_env_overrides(data: dict[str, Any]) -> dict[str, Any]:
    for env_key, (section, field) in _ENV_MAP.items():
        val = os.environ.get(env_key)
        if val is not None:
            if section not in data:
                data[section] = {}
            data[section][field] = val
    return data


def load_settings(path: Path | None = None) -> Settings:
    """Load settings from a YAML file, then apply ARGUS_* env var overrides."""
    settings_path = path or _DEFAULT_SETTINGS_PATH
    data: dict[str, Any] = {}
    if settings_path.exists():
        with settings_path.open() as fh:
            loaded = yaml.safe_load(fh)
            if isinstance(loaded, dict):
                data = loaded
    data = _apply_env_overrides(data)
    return Settings.model_validate(data)


def require_cdse_credentials(settings: Settings) -> None:
    """Raise ConfigError if CDSE credentials are absent.

    Never includes credential values in the error message.
    """
    if not settings.cdse.user or not settings.cdse.password:
        raise ConfigError(
            "CDSE credentials are required but not configured.\n"
            "Set the following environment variables before running live acquisition:\n"
            "  ARGUS_CDSE_USER=<your-username>\n"
            "  ARGUS_CDSE_PASSWORD=<your-password>\n"
            "Register for free at https://dataspace.copernicus.eu/"
        )
