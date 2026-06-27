"""Core types and the Assistant protocol for the Argus AI layer (INV-4).

All AI-generated text must be grounded: every factual claim references a record
id. Ungrounded claims are a defect, not a warning — see GroundingError.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

from pydantic import BaseModel


class Scope(BaseModel):
    """The spatiotemporal context for an AI report or query."""

    aoi_id: str
    target_id: str | None = None
    t0: datetime
    t1: datetime
    obs_types: list[str] = []
    attrs: dict[str, Any] = {}


@dataclass
class GroundedText:
    """AI-generated report text with all citation IDs validated against the store."""

    text: str
    citations: list[str]
    model: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class GroundedAnswer:
    """AI-generated query answer with all citation IDs validated against the store."""

    answer: str
    citations: list[str]
    model: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class AIReport(BaseModel):
    """Persisted record of one AI interaction."""

    id: str
    kind: str  # "report" | "answer" | "explanation"
    text: str
    citations: list[str]
    model: str
    scope_aoi_id: str
    scope_target_id: str | None = None
    created_at: datetime = None  # type: ignore[assignment]

    def model_post_init(self, __context: Any) -> None:
        if self.created_at is None:
            object.__setattr__(self, "created_at", datetime.now(UTC))


class Assistant(Protocol):
    """Stable interface for the Argus AI assistant (INV-2, INV-4).

    Implementations must:
    - Produce GroundedText/GroundedAnswer where every factual claim cites a record id.
    - Never originate environmental values from training data.
    - Log all calls via ArgusAIClient.usage.
    """

    def report(self, scope: Scope) -> GroundedText:
        """Produce a grounded plain-language situation report for scope."""
        ...

    def answer(self, question: str, scope: Scope) -> GroundedAnswer:
        """Answer a natural-language question using only store records."""
        ...
