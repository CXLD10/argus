"""F-001 / F-022 tests: configuration loading, credential validation, and profile system."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

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
    missing = Path(tmp_path) / "nonexistent.yaml"  # type: ignore[arg-type]
    settings = load_settings(path=missing)
    assert isinstance(settings, Settings)
    assert settings.cdse.daily_quota_gb == 1.0


# ── F-022: Profile loading ────────────────────────────────────────────────────


def test_profile_test_sets_ai_offline(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    base = tmp_path / "settings.yaml"
    base.write_text(yaml.dump({"ai": {"offline": False}}))
    (tmp_path / "settings.test.yaml").write_text(yaml.dump({"ai": {"offline": True}}))
    monkeypatch.setenv("ARGUS_PROFILE", "test")
    settings = load_settings(path=base)
    assert settings.ai.offline is True


def test_profile_dev_sets_log_level(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    base = tmp_path / "settings.yaml"
    base.write_text(yaml.dump({"logging": {"level": "INFO"}}))
    (tmp_path / "settings.dev.yaml").write_text(yaml.dump({"logging": {"level": "DEBUG"}}))
    monkeypatch.setenv("ARGUS_PROFILE", "dev")
    settings = load_settings(path=base)
    assert settings.logging.level == "DEBUG"


def test_profile_missing_file_falls_back_to_base(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    base = tmp_path / "settings.yaml"
    base.write_text(yaml.dump({"logging": {"level": "INFO"}}))
    monkeypatch.setenv("ARGUS_PROFILE", "nonexistent")
    settings = load_settings(path=base)
    assert settings.logging.level == "INFO"


def test_profile_merges_sections(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Profile override merges within a section — non-overridden keys are preserved."""
    base = tmp_path / "settings.yaml"
    base.write_text(yaml.dump({"cdse": {"user": "", "password": "", "daily_quota_gb": 1.0}}))
    (tmp_path / "settings.test.yaml").write_text(yaml.dump({"cdse": {"daily_quota_gb": 0.1}}))
    monkeypatch.setenv("ARGUS_PROFILE", "test")
    settings = load_settings(path=base)
    assert settings.cdse.daily_quota_gb == pytest.approx(0.1)
    assert settings.cdse.user == ""  # base key preserved


def test_env_var_wins_over_profile(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    base = tmp_path / "settings.yaml"
    base.write_text(yaml.dump({"logging": {"level": "INFO"}}))
    (tmp_path / "settings.test.yaml").write_text(yaml.dump({"logging": {"level": "WARNING"}}))
    monkeypatch.setenv("ARGUS_PROFILE", "test")
    monkeypatch.setenv("ARGUS_LOGGING_LEVEL", "ERROR")
    settings = load_settings(path=base)
    assert settings.logging.level == "ERROR"


def test_argus_profile_test_loaded_automatically(monkeypatch: pytest.MonkeyPatch) -> None:
    """ARGUS_PROFILE=test loads config/settings.test.yaml without explicit path."""
    monkeypatch.setenv("ARGUS_PROFILE", "test")
    settings = load_settings()
    assert settings.ai.offline is True


def test_invalid_config_type_raises_config_error(tmp_path: Path) -> None:
    """A bad value type (e.g. string for a float field) raises ConfigError at load time."""
    bad = tmp_path / "settings.yaml"
    bad.write_text("cdse:\n  daily_quota_gb: not_a_number\n")
    with pytest.raises(ConfigError, match="Invalid configuration"):
        load_settings(path=bad)


def test_settings_yaml_has_no_credentials() -> None:
    """Base settings.yaml must not contain actual credential values (AC: no secrets in repo)."""
    repo_root = Path(__file__).parent.parent
    settings_path = repo_root / "config" / "settings.yaml"
    with settings_path.open() as fh:
        data = yaml.safe_load(fh)
    cdse = data.get("cdse", {})
    assert cdse.get("user", "") == "", "cdse.user must be empty in settings.yaml"
    assert cdse.get("password", "") == "", "cdse.password must be empty in settings.yaml"
    cmems = data.get("cmems", {})
    assert cmems.get("user", "") == "", "cmems.user must be empty in settings.yaml"
    assert cmems.get("password", "") == "", "cmems.password must be empty in settings.yaml"


def test_no_profile_uses_base_only(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("ARGUS_PROFILE", raising=False)
    base = tmp_path / "settings.yaml"
    base.write_text(yaml.dump({"logging": {"level": "INFO"}}))
    settings = load_settings(path=base)
    assert settings.logging.level == "INFO"
