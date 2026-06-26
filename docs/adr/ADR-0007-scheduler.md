# ADR-0007 — Scheduler Technology for Unattended Domain Monitoring

- **Status:** DRAFT — not yet approved
- **Created:** 2026-06-27
- **Required before:** Phase 8 / F-037 starts
- **Deciders:** Josh
- **Related:** [phase-8.md](../features/phase-8.md) · [ADR-0002](ADR-0002-data-and-simulation-stack.md)

---

## Context

Phase 8 adds unattended, per-domain monitoring (F-037). The scheduler must:
- Trigger domain runs per AOI on a configurable cadence (e.g. daily, S2 revisit ~5d).
- Be quota-aware (stop/backoff before hitting CDSE ≤1GB/day or Open-Meteo ≤10k calls/day).
- Run in WSL with zero recurring cost.
- Be simple to operate solo — not a distributed job system.
- Support incremental/idempotent ingestion (F-038).

Three options are under consideration:

---

## Options

### Option A: `cron` + argus CLI invocations

`crontab` triggers `argus run --domain X --aoi Y` on a schedule.
- **Pro:** zero dependencies; trivially simple; WSL-native; zero cost.
- **Con:** no built-in quota tracking (must be in argus itself); no retry/backoff built in;
  hard to inspect state without reading logs.

### Option B: APScheduler (in-process Python scheduler)

Embed `APScheduler` in `argus serve`. Jobs are Python functions; state in SQLite.
- **Pro:** quota-aware logic in Python; inspectable via API; single process.
- **Con:** argus must be running continuously; more complex than cron; less familiar to ops.

### Option C: Prefect / Dagster local (workflow orchestrator)

Use a local OSS orchestrator (Prefect CE, Dagster open source).
- **Pro:** rich UI, retry/backoff built in, dependency graphs, logging.
- **Con:** significant operational complexity; substantial new dependency; overkill for a
  single-operator tool; risk of introducing heavyweight infra.

---

## Decision

**PENDING — requires human input.**

Recommended path: **Option B (APScheduler)**, because:
- Quota logic is native Python alongside the argus codebase.
- A lightweight background scheduler in `argus serve` is the minimal extra complexity.
- Avoids the external-process fragility of cron and the heavyweight orchestrator cost of C.

If Josh prefers operational simplicity over in-process integration, **Option A (cron)** is
acceptable — requires that quota tracking is entirely in the argus ingestion layer (which it
already is per QUOTAS.md).

**This ADR must be decided and approved before any code for F-037 is written.**

---

## Cost Validation

All three options are zero recurring cost:
- Option A: `cron` is part of the OS.
- Option B: `APScheduler` is MIT-licensed, free.
- Option C: Prefect CE and Dagster open source are free to self-host.

---

## Consequences

When decided:
- Update this ADR status to ACCEPTED.
- Implement scheduler in F-037 using the chosen approach.
- Document scheduler operation in DEPLOYMENT.md (Phase 11 / F-054).
