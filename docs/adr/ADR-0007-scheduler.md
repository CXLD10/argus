# ADR-0007 — Scheduler Technology for Unattended Domain Monitoring

- **Status:** ACCEPTED — 2026-06-28
- **Created:** 2026-06-27
- **Accepted:** 2026-06-28
- **Required before:** Phase 8 / F-037
- **Deciders:** Josh
- **Related:** [phase-8.md](../features/phase-8.md) · [ADR-0002](ADR-0002-data-and-simulation-stack.md)

---

## Decision

**Option B — APScheduler (in-process background scheduler).**

APScheduler 3.x (MIT licensed) runs as a background thread inside `argus serve` for local
development and Docker. All scheduling logic is behind a `Scheduler` protocol so the
backend is swappable.

---

## Context

Phase 8 adds unattended, per-domain monitoring (F-037). The scheduler must:
- Trigger domain runs per AOI on a configurable cadence (e.g. daily, S2 revisit ~5d).
- Be quota-aware (stop/backoff before hitting CDSE ≤1GB/day or Open-Meteo ≤10k calls/day).
- Run in WSL with zero recurring cost.
- Be simple to operate solo — not a distributed job system.
- Support incremental/idempotent ingestion (F-038).

---

## Design Principles (required by Josh)

1. **Backend independence:** All scheduling is behind a `Scheduler` protocol. Implementations
   can be swapped without touching business logic.

2. **Stateless jobs:** Each scheduled task calls a stateless `run_domain_task()` function.
   The same function is used by the CLI, API, and scheduler — no scheduler-specific code in
   the execution path.

3. **Manual invocation parity:** Every scheduled task is also invokable via:
   - CLI: `argus run --domain X --aoi Y`
   - API: `POST /run/domain/{domain_id}/aoi/{aoi_id}`
   - Direct function call (for tests)

4. **Cloud Run compatibility:** On Google Cloud Run, Cloud Scheduler fires HTTP requests to
   `POST /run/domain/{domain_id}/aoi/{aoi_id}`. The same handler as the API endpoint above.
   No APScheduler is needed in the Cloud Run environment (Cloud Scheduler replaces it).
   Business logic is unchanged.

5. **Configuration in `settings.yaml`:** Schedule cadences, enabled/disabled jobs, and quota
   thresholds are all in `config/settings.yaml` (new `scheduler` section).

6. **Quota-aware:** A `QuotaGuard` pre-flight check prevents task execution when daily limits
   are within 10% of exhaustion.

7. **Run history:** `RunHistory` records are persisted through the existing store (INV-6).

---

## Interface

```python
# argus/tasking/base.py

class Scheduler(Protocol):
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def schedule(self, job: ScheduledJob, callback: Callable[[], None]) -> None: ...
    def unschedule(self, job_id: str) -> None: ...
    def list_jobs(self) -> list[ScheduledJob]: ...
    def trigger(self, job_id: str) -> None: ...

@dataclass
class ScheduledJob:
    job_id: str
    domain_id: str
    aoi_id: str
    cadence_hours: int
    enabled: bool = True
```

---

## Consequences

- APScheduler runs as a daemon thread inside `argus serve`. If the process dies, scheduled
  jobs stop. This is acceptable for a solo-operator tool on WSL.
- On Cloud Run, APScheduler is not used. Cloud Scheduler makes HTTP calls instead.
- Adding a new backend (e.g., systemd timer, Cloud Tasks) requires only a new class
  implementing the `Scheduler` protocol.
- No migration needed: the run history table is in SQLite, portable to Cloud SQL.

---

## Cost Validation

- APScheduler: MIT licensed, zero recurring cost.
- tzlocal (APScheduler dependency): MIT licensed.
- No additional infrastructure required for local development.
