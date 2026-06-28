"""Scheduler protocol and data models for per-domain task scheduling.

The Scheduler interface is backend-agnostic (ADR-0007). APSchedulerBackend is the
default for local/Docker; Cloud Scheduler fires HTTP calls to the same API endpoints.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol


@dataclass
class ScheduledJob:
    """Configuration for one recurring domain analysis task."""

    job_id: str
    domain_id: str
    aoi_id: str
    cadence_hours: int
    enabled: bool = True
    next_run_at: datetime | None = None
    attrs: dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskResult:
    """Outcome of one domain task execution."""

    job_id: str
    domain_id: str
    aoi_id: str
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    status: str = "running"  # running | complete | failed | skipped
    scenes_fetched: int = 0
    observations_created: int = 0
    bytes_used: int = 0
    error: str | None = None

    def finish(self, *, status: str, scenes: int = 0, obs: int = 0, bytes_used: int = 0) -> None:
        self.completed_at = datetime.now(UTC)
        self.status = status
        self.scenes_fetched = scenes
        self.observations_created = obs
        self.bytes_used = bytes_used

    def fail(self, error: str) -> None:
        self.completed_at = datetime.now(UTC)
        self.status = "failed"
        self.error = error


class Scheduler(Protocol):
    """Backend-agnostic scheduler interface (ADR-0007).

    Implementations: APSchedulerBackend (default), NullScheduler (tests/CI).
    Cloud Run uses Cloud Scheduler → HTTP → same API endpoint; no Scheduler instance needed.
    """

    def start(self) -> None:
        """Start the scheduler background thread / service."""

    def stop(self) -> None:
        """Stop the scheduler, allowing in-flight tasks to complete."""

    def schedule(self, job: ScheduledJob, callback: Callable[[], None]) -> None:
        """Register a job to fire *callback* every job.cadence_hours hours."""

    def unschedule(self, job_id: str) -> None:
        """Remove a previously scheduled job."""

    def list_jobs(self) -> list[ScheduledJob]:
        """Return all currently registered jobs."""

    def trigger(self, job_id: str) -> None:
        """Manually fire a job immediately (for CLI/API invocation parity)."""
