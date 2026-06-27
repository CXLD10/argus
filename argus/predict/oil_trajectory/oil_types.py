"""Oil type registry — loads config/oil_types.yaml; validates oil_type at runtime.

INV-5: no default oil type. Any simulation must supply an explicit, registered oil_type.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_DEFAULT_REGISTRY = Path("config") / "oil_types.yaml"


class OilTypeRequiredError(ValueError):
    """Raised when oil_type is absent or empty (INV-5)."""


class OilTypeNotFoundError(ValueError):
    """Raised when oil_type is not in the registry (INV-5)."""


@dataclass(frozen=True)
class OilType:
    id: str
    name: str
    openoil_name: str
    viscosity_est: str | None = None
    validated: bool = False


class OilTypeRegistry:
    """Loaded from oil_types.yaml; validates and resolves oil_type identifiers."""

    def __init__(self, oil_types: list[OilType]) -> None:
        self._by_id: dict[str, OilType] = {ot.id: ot for ot in oil_types}

    @property
    def available_ids(self) -> list[str]:
        return sorted(self._by_id)

    def get(self, oil_type_id: str) -> OilType:
        """Return the OilType for *oil_type_id*.

        Raises:
            OilTypeRequiredError: if oil_type_id is empty.
            OilTypeNotFoundError: if not in registry.
        """
        if not oil_type_id:
            raise OilTypeRequiredError(
                "oil_type is required and must not be empty (INV-5). "
                f"Available: {self.available_ids}"
            )
        if oil_type_id not in self._by_id:
            raise OilTypeNotFoundError(
                f"oil_type {oil_type_id!r} not in registry. Available: {self.available_ids}"
            )
        return self._by_id[oil_type_id]


def load_oil_types(path: Path = _DEFAULT_REGISTRY) -> OilTypeRegistry:
    """Load and return the OilTypeRegistry from *path*."""
    raw: dict[str, Any] = yaml.safe_load(path.read_text())
    oil_types = [
        OilType(
            id=entry["id"],
            name=entry["name"],
            openoil_name=entry["openoil_name"],
            viscosity_est=entry.get("viscosity_est"),
            validated=bool(entry.get("validated", False)),
        )
        for entry in raw["oil_types"]
    ]
    return OilTypeRegistry(oil_types)
