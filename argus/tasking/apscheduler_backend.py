"""APScheduler-backed implementation of the Scheduler protocol (ADR-0007 Option B).

This module is the only place that imports APScheduler. All callers depend on the
Scheduler protocol defined in argus.tasking.base — not on this module directly.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from argus.tasking.base import ScheduledJob

logger = logging.getLogger(__name__)


class APSchedulerBackend:
    """BackgroundScheduler implementation of the Scheduler protocol.

    Uses APScheduler 3.x BackgroundScheduler (runs in a daemon thread). Thread-safe
    for read operations on _jobs; mutations hold _lock.
    """

    def __init__(self) -> None:
        self._scheduler: BackgroundScheduler = BackgroundScheduler(timezone="UTC")
        self._jobs: dict[str, ScheduledJob] = {}
        self._callbacks: dict[str, Callable[[], None]] = {}
        self._lock = threading.RLock()  # reentrant: schedule() calls _unschedule_locked()

    # ── Scheduler protocol ────────────────────────────────────────────────────

    def start(self) -> None:
        if not self._scheduler.running:
            self._scheduler.start()
            logger.info("APScheduler started")

    def stop(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=True)
            logger.info("APScheduler stopped")

    def schedule(self, job: ScheduledJob, callback: Callable[[], None]) -> None:
        with self._lock:
            if job.job_id in self._jobs:
                self._unschedule_locked(job.job_id)

            trigger = IntervalTrigger(hours=job.cadence_hours, timezone="UTC")
            self._scheduler.add_job(
                func=self._wrapped_callback(job.job_id),
                trigger=trigger,
                id=job.job_id,
                replace_existing=True,
                misfire_grace_time=300,  # 5-minute window before treating as missed
            )
            self._jobs[job.job_id] = job
            self._callbacks[job.job_id] = callback
            logger.info("Scheduled job %s every %dh", job.job_id, job.cadence_hours)

    def unschedule(self, job_id: str) -> None:
        with self._lock:
            self._unschedule_locked(job_id)

    def _unschedule_locked(self, job_id: str) -> None:
        """Remove job while _lock is already held (or acquired by caller)."""
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)
        self._jobs.pop(job_id, None)
        self._callbacks.pop(job_id, None)
        logger.info("Unscheduled job %s", job_id)

    def list_jobs(self) -> list[ScheduledJob]:
        with self._lock:
            result: list[ScheduledJob] = []
            for job_id, job in self._jobs.items():
                aps_job = self._scheduler.get_job(job_id)
                next_run: datetime | None = None
                if aps_job is not None:
                    raw: Any = aps_job.next_run_time
                    if raw is not None:
                        next_run = datetime.fromtimestamp(raw.timestamp(), tz=UTC)
                result.append(
                    ScheduledJob(
                        job_id=job.job_id,
                        domain_id=job.domain_id,
                        aoi_id=job.aoi_id,
                        cadence_hours=job.cadence_hours,
                        enabled=job.enabled,
                        next_run_at=next_run,
                        attrs=dict(job.attrs),
                    )
                )
            return result

    def trigger(self, job_id: str) -> None:
        """Fire a job immediately without disturbing its regular schedule."""
        with self._lock:
            callback = self._callbacks.get(job_id)
        if callback is None:
            raise KeyError(f"No scheduled job with id={job_id!r}")
        # Run in background thread so the HTTP response returns immediately
        t = threading.Thread(target=callback, name=f"argus-trigger-{job_id}", daemon=True)
        t.start()
        logger.info("Manually triggered job %s", job_id)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _wrapped_callback(self, job_id: str) -> Callable[[], None]:
        def _run() -> None:
            with self._lock:
                cb = self._callbacks.get(job_id)
            if cb is not None:
                try:
                    cb()
                except Exception:
                    logger.exception("Job %s raised an exception", job_id)

        return _run
