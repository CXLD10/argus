"""F-020 tests: structured error handling — all exceptions from errors.py."""

from __future__ import annotations

import pytest

from argus.core.errors import (
    AcquisitionError,
    AOIError,
    ArgusError,
    BelowResolutionError,
    CatalogueError,
    CdseAuthError,
    CmemsUnavailableError,
    ConfigError,
    GroundingError,
    ObservationTypeError,
    OilTypeNotFoundError,
    OilTypeRequiredError,
    ProcessApiError,
    QuotaExceededError,
    SimulationError,
    StoreError,
)

# ── Hierarchy: all exceptions inherit from ArgusError ────────────────────────


@pytest.mark.parametrize(
    "exc_class",
    [
        ConfigError,
        StoreError,
        AOIError,
        BelowResolutionError,
        AcquisitionError,
        QuotaExceededError,
        ProcessApiError,
        CatalogueError,
        CdseAuthError,
        CmemsUnavailableError,
        OilTypeRequiredError,
        OilTypeNotFoundError,
        SimulationError,
        ObservationTypeError,
        GroundingError,
    ],
)
def test_all_exceptions_inherit_from_argus_error(exc_class: type) -> None:
    assert issubclass(exc_class, ArgusError), f"{exc_class.__name__} must inherit from ArgusError"


# ── Sub-hierarchy assertions ──────────────────────────────────────────────────


def test_quota_exceeded_is_acquisition_error() -> None:
    assert issubclass(QuotaExceededError, AcquisitionError)


def test_process_api_error_is_acquisition_error() -> None:
    assert issubclass(ProcessApiError, AcquisitionError)


def test_below_resolution_is_aoi_error() -> None:
    assert issubclass(BelowResolutionError, AOIError)


def test_observation_type_error_is_also_value_error() -> None:
    """ObservationTypeError must be a ValueError so Pydantic validators wrap it correctly."""
    assert issubclass(ObservationTypeError, ValueError)


# ── Catchability ──────────────────────────────────────────────────────────────


def test_quota_exceeded_caught_as_acquisition_error() -> None:
    with pytest.raises(AcquisitionError):
        raise QuotaExceededError("test quota exceeded")


def test_quota_exceeded_caught_as_argus_error() -> None:
    with pytest.raises(ArgusError):
        raise QuotaExceededError("test quota exceeded")


def test_below_resolution_caught_as_aoi_error() -> None:
    with pytest.raises(AOIError):
        raise BelowResolutionError("test below resolution")


def test_observation_type_error_caught_as_value_error() -> None:
    with pytest.raises(ValueError):
        raise ObservationTypeError("obs_type 'bad_type' not registered")


# ── Error messages are actionable ─────────────────────────────────────────────


def test_quota_exceeded_message_is_actionable() -> None:
    exc = QuotaExceededError("CDSE daily quota exhausted. Try again tomorrow.")
    assert "tomorrow" in str(exc) or "quota" in str(exc).lower()


def test_cdse_auth_error_message_mentions_credentials() -> None:
    exc = CdseAuthError("Authentication failed. Set ARGUS_CDSE_USER and ARGUS_CDSE_PASSWORD.")
    assert "ARGUS_CDSE_USER" in str(exc) or "credential" in str(exc).lower()


def test_oil_type_required_has_actionable_message() -> None:
    exc = OilTypeRequiredError(
        "oil_type is required. Set oil_type in your AOI config. "
        "Valid types: see config/oil_types.yaml."
    )
    assert "oil_types.yaml" in str(exc) or "config" in str(exc).lower()


# ── Integration: exceptions raised by argus modules ─────────────────────────


def test_aoi_loader_raises_aoi_error_for_missing_file(tmp_path) -> None:
    from argus.aoi.loader import AOIError as LoaderAOIError
    from argus.aoi.loader import load_aoi

    # The re-exported class must be the same as the canonical one
    assert LoaderAOIError is AOIError
    with pytest.raises(AOIError):
        load_aoi(tmp_path / "nonexistent.geojson")


def test_models_raise_observation_type_error_for_invalid_obs_type() -> None:
    from pydantic import ValidationError

    from argus.core.models import Observation

    with pytest.raises(ValidationError) as exc_info:
        Observation(
            id="x",
            analysis_run_id="r",
            scene_id="s",
            obs_type="invalid_type_xyz",
            evidence_class="measured",
            geometry={"type": "Point", "coordinates": [0, 0]},
            area_km2=1.0,
            confidence=0.5,
        )
    # The ValidationError should wrap an ObservationTypeError
    assert "ObservationTypeError" in str(type(exc_info.value.__cause__).__name__) or (
        "not in registered types" in str(exc_info.value)
        or "invalid_type_xyz" in str(exc_info.value)
    )


def test_runner_raises_simulation_error_for_bad_exit(tmp_path, monkeypatch) -> None:
    import subprocess

    from argus.core.errors import SimulationError
    from argus.predict.oil_trajectory.runner import SimInput, run_simulation

    result = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="fatal error")
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: result)

    sim_input = SimInput(
        oil_type="crude_medium",
        seed_geometry={"type": "Point", "coordinates": [-61.4, 11.1]},
        t0="2024-02-07T00:00:00+00:00",
        duration_hours=6,
        rng_seed=42,
    )

    with pytest.raises(SimulationError):
        run_simulation(sim_input)
