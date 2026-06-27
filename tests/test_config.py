"""F-001 tests: configuration loading and credential validation."""

from __future__ import annotations

import pytest

from argus.core.config import (
    CdseConfig,
    ConfigError,
    Settings,
    load_settings,
    require_cdse_credentials,
)


def test_load_settings_returns_settings_instance() -> None:
    settings = load_settings()
    assert isinstance(settings, Settings)


def test_load_settings_cdse_defaults() -> None:
    settings = load_settings()
    assert settings.cdse.daily_quota_gb == 1.0


def test_load_settings_open_meteo_defaults() -> None:
    settings = load_settings()
    assert settings.open_meteo.daily_call_limit == 10_000


def test_load_settings_store_defaults() -> None:
    settings = load_settings()
    assert settings.store.db_path is not None
    assert settings.store.artifact_dir is not None


def test_load_settings_env_override_cdse_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARGUS_CDSE_USER", "envuser")
    settings = load_settings()
    assert settings.cdse.user == "envuser"


def test_load_settings_env_override_cdse_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARGUS_CDSE_PASSWORD", "envpass")
    settings = load_settings()
    assert settings.cdse.password == "envpass"


def test_load_settings_env_override_logging_level(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARGUS_LOGGING_LEVEL", "DEBUG")
    settings = load_settings()
    assert settings.logging.level == "DEBUG"


def test_require_cdse_credentials_raises_when_missing() -> None:
    settings = Settings(cdse=CdseConfig(user="", password=""))
    with pytest.raises(ConfigError):
        require_cdse_credentials(settings)


def test_require_cdse_credentials_raises_when_user_only() -> None:
    settings = Settings(cdse=CdseConfig(user="someone", password=""))
    with pytest.raises(ConfigError):
        require_cdse_credentials(settings)


def test_require_cdse_credentials_raises_when_password_only() -> None:
    settings = Settings(cdse=CdseConfig(user="", password="secret"))
    with pytest.raises(ConfigError):
        require_cdse_credentials(settings)


def test_require_cdse_credentials_passes_when_both_set() -> None:
    settings = Settings(cdse=CdseConfig(user="user", password="pass"))
    require_cdse_credentials(settings)  # must not raise


def test_config_error_contains_remediation_text() -> None:
    settings = Settings(cdse=CdseConfig(user="", password=""))
    with pytest.raises(ConfigError) as exc_info:
        require_cdse_credentials(settings)
    msg = str(exc_info.value)
    assert "ARGUS_CDSE_USER" in msg
    assert "ARGUS_CDSE_PASSWORD" in msg


def test_config_error_no_secrets_in_output() -> None:
    """Credential values must never appear in the ConfigError message."""
    settings = Settings(cdse=CdseConfig(user="secret_user", password=""))
    with pytest.raises(ConfigError) as exc_info:
        require_cdse_credentials(settings)
    assert "secret_user" not in str(exc_info.value)


def test_load_settings_missing_file_uses_defaults(tmp_path: pytest.TempPathFactory) -> None:
    from pathlib import Path

    missing = Path(tmp_path) / "nonexistent.yaml"  # type: ignore[arg-type]
    settings = load_settings(path=missing)
    assert isinstance(settings, Settings)
    assert settings.cdse.daily_quota_gb == 1.0
