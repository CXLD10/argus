"""Argus Domain protocol and Acquisition container (INV-2: stable — do not edit without ADR)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from argus.core.models import MonitorTarget, Observation, SourceRef


@dataclass
class Acquisition:
    """Data container passed from Domain.acquire() to Domain.analyze()."""

    scene_id: str
    source_ref: SourceRef
    preprocessed: Any = None  # domain-specific payload; e.g. PreprocessedScene for marine_oil
    attrs: dict[str, Any] = field(default_factory=dict)


class Domain(Protocol):
    """Protocol all observation domains must satisfy (v2.0 canonical interface).

    INV-2: this interface is stable. Never edit without an ADR.
    """

    domain_id: str

    def search(
        self,
        target: MonitorTarget,
        t0: datetime,
        t1: datetime,
    ) -> list[SourceRef]: ...

    def acquire(self, ref: SourceRef) -> Acquisition: ...

    def analyze(self, acq: Acquisition) -> list[Observation]: ...
