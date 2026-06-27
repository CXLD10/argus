"""Canonical exception hierarchy for Argus.

All Argus exceptions inherit from ArgusError. Every error message must be
actionable: it tells the user or operator *what to do*, not only *what failed*.

Usage:
    from argus.core.errors import ArgusError, QuotaExceededError, ...
"""

from __future__ import annotations


class ArgusError(Exception):
    """Base class for all Argus exceptions."""


# ── Configuration ──────────────────────────────────────────────────────────────


class ConfigError(ArgusError):
    """Invalid or missing configuration.

    Check config/settings.yaml and the ARGUS_* environment variables.
    """


# ── Store / database ──────────────────────────────────────────────────────────


class StoreError(ArgusError):
    """SQLite store access failure.

    Ensure the database file is writable and not locked by another process.
    """


# ── AOI loading ───────────────────────────────────────────────────────────────


class AOIError(ArgusError):
    """Invalid or unloadable AOI definition.

    Check the GeoJSON file in config/aois/ for geometry validity.
    """


class BelowResolutionError(AOIError):
    """Target or water body is below the sensor resolution gate.

    Use a target that meets the minimum area threshold for the requested domain.
    """


# ── Data acquisition ──────────────────────────────────────────────────────────


class AcquisitionError(ArgusError):
    """Scene acquisition failure (quota, API, or config).

    Check CDSE credentials, quota status, and network connectivity.
    """


class QuotaExceededError(AcquisitionError):
    """Daily CDSE data-transfer quota exceeded.

    The daily 1 GB CDSE quota has been reached. Wait until midnight UTC or
    reduce the requested AOI subset size.
    """


class ProcessApiError(AcquisitionError):
    """Sentinel Hub Process API request failed.

    Check the API credentials, evalscript syntax, and the Sentinel Hub status page.
    """


class CatalogueError(ArgusError):
    """CDSE STAC catalogue search failure.

    Check CDSE credentials and network connectivity. The STAC endpoint may be
    temporarily unavailable.
    """


class CdseAuthError(ArgusError):
    """CDSE OAuth authentication failure.

    Set ARGUS_CDSE_USER and ARGUS_CDSE_PASSWORD environment variables, or
    check that the credentials in config/settings.yaml are valid.
    """


class CmemsUnavailableError(ArgusError):
    """CMEMS marine data service unavailable.

    The fallback Open-Meteo marine forcing will be used instead. This is
    expected during CMEMS maintenance windows.
    """


# ── Oil trajectory / simulation ───────────────────────────────────────────────


class OilTypeRequiredError(ArgusError):
    """oil_type is missing from the simulation configuration (INV-5).

    Set oil_type in your AOI config or provide it via the CLI. Valid types are
    listed in config/oil_types.yaml.
    """


class OilTypeNotFoundError(ArgusError):
    """Requested oil_type is not in the type registry.

    Add the oil type to config/oil_types.yaml or use an existing type.
    Valid types are listed in config/oil_types.yaml.
    """


class SimulationError(ArgusError):
    """OpenOil subprocess exited with a non-zero status.

    Check the stderr output above for the root cause. Ensure opendrift is
    installed in the simulation environment.
    """


# ── Observation schema ────────────────────────────────────────────────────────


class ObservationTypeError(ArgusError, ValueError):
    """obs_type is not in the registered type registry.

    Use one of the types defined in argus.core.models.VALID_OBS_TYPES.
    Inherits from ValueError so Pydantic field_validators wrap it in ValidationError.
    """


# ── AI / grounding ────────────────────────────────────────────────────────────


class GroundingError(ArgusError):
    """AI output contains a claim not traceable to a record id (INV-4).

    Every factual claim in AI-generated text must reference a record id
    in the citations list. Review the grounding guard configuration.
    """
