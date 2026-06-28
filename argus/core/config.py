"""Argus configuration: load settings.yaml + environment variable overrides.

Profile loading: set ARGUS_PROFILE=<name> to load config/settings.<name>.yaml on
top of the base settings.yaml. Profile values override base values; ARGUS_* env
vars override both.

  ARGUS_PROFILE=test  → loads config/settings.test.yaml after base
  ARGUS_PROFILE=dev   → loads config/settings.dev.yaml after base
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError

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


class HydroChokepointsConfig(BaseModel):
    """Configurable thresholds for D4 choke-point detection (OQ-B resolution)."""

    cell_size_m: float = 30.0
    min_upstream_area_km2: float = 1.0
    min_constriction_score: float = 0.05
    max_candidates: int = 50
    dem_source: str = "cop_glo30"


class FloodRiskConfig(BaseModel):
    """Thresholds for the rule-based FloodRisk predictor."""

    precip_high_mm: float = 100.0
    precip_extreme_mm: float = 200.0
    discharge_high_m3s: float = 500.0
    discharge_extreme_m3s: float = 2000.0
    risk_score_medium: float = 0.25
    risk_score_high: float = 0.50
    risk_score_extreme: float = 0.75


class DomainsConfig(BaseModel):
    hydro_chokepoints: HydroChokepointsConfig = Field(
        default_factory=HydroChokepointsConfig
    )
    flood_risk: FloodRiskConfig = Field(default_factory=FloodRiskConfig)


class Settings(BaseModel):
    cdse: CdseConfig = Field(default_factory=CdseConfig)
    open_meteo: OpenMeteoConfig = Field(default_factory=OpenMeteoConfig)
    cmems: CmemsConfig = Field(default_factory=CmemsConfig)
    ai: AiConfig = Field(default_factory=AiConfig)
    store: StoreConfig = Field(default_factory=StoreConfig)
    alerts: AlertsConfig = Field(default_factory=AlertsConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    prediction: PredictionConfig = Field(default_factory=PredictionConfig)
    domains: DomainsConfig = Field(default_factory=DomainsConfig)


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


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Merge override into base one level deep (section → field)."""
    result = dict(base)
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = {**result[key], **val}
        else:
            result[key] = val
    return result


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open() as fh:
        loaded = yaml.safe_load(fh)
    return loaded if isinstance(loaded, dict) else {}


def load_settings(path: Path | None = None) -> Settings:
    """Load settings from a YAML file, apply profile overrides, then apply ARGUS_* env vars.

    Resolution order (later wins):
    1. config/settings.yaml (base)
    2. config/settings.<ARGUS_PROFILE>.yaml (profile override, if ARGUS_PROFILE set)
    3. ARGUS_* environment variables

    Raises:
        ConfigError: if the resulting config fails Pydantic validation (invalid type/value).
    """
    settings_path = path or _DEFAULT_SETTINGS_PATH
    data = _load_yaml(settings_path)

    profile = os.environ.get("ARGUS_PROFILE")
    if profile:
        profile_path = settings_path.parent / f"settings.{profile}.yaml"
        profile_data = _load_yaml(profile_path)
        if profile_data:
            data = _deep_merge(data, profile_data)

    data = _apply_env_overrides(data)
    try:
        return Settings.model_validate(data)
    except ValidationError as exc:
        raise ConfigError(f"Invalid configuration: {exc}") from exc


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
