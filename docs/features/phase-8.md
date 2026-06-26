# Phase 8 — Automation & Scheduling

- **Status:** Specced (scheduler ADR needed before implementation)
- **Priority:** P1
- **Last updated:** 2026-06-27
- **Features:** F-037–F-039
- **Depends on:** Phase 7 complete; ADR-0005-scheduler (not yet written — required before F-037)
- **Related:** [phase-7.md](phase-7.md) · [phase-9.md](phase-9.md) · [QUOTAS.md](../standards/QUOTAS.md)
- **Checkpoint:** Part of CP-3 (full domain coverage + automation)

**Pre-requisite:** Before any feature in this phase begins, write and accept
`docs/adr/ADR-0005-scheduler.md` (note: different from ADR-0005 MVP redefinition — this
scheduler ADR needs a new number; use ADR-0007-scheduler.md).

> **Note on ADR numbering:** ADR-0005 is now the MVP redefinition. The scheduler ADR
> referenced in ARCHITECTURE.md §8 must be ADR-0007.

**Goal:** Add unattended per-domain scheduling so Argus polls sources automatically,
ingests incrementally, and is idempotent on re-runs.

---

## F-037 — Per-Domain Tasking + Scheduler

**Why:** Manual per-event runs cannot provide early warning across multiple water bodies.

**Pre-requisite:** ADR-0007 (scheduler technology) accepted.

**Depends on:** F-036, ADR-0007

**Owns / creates:**
- `argus/scheduler/__init__.py`
- `argus/scheduler/tasker.py` (per-domain task generator)
- `argus/scheduler/runner.py` (scheduler loop; cron or APScheduler)
- `config/schedule.yaml` (polling intervals per domain; quota limits per run)
- `tests/test_scheduler.py`

**Scheduler choices (to be decided in ADR-0007):**
- APScheduler (in-process, no daemon) — recommended for WSL/laptop
- systemd timer (OS-level, more reliable) — requires systemd in WSL
- cron (simplest, shell scripts) — least code, easy to understand

**Acceptance criteria:**
- Scheduled run generates Tasks for each active AOI + enabled domain
- Quota-aware: if daily CDSE budget is near limit, tasks are deferred
- Idempotent: re-running the same day does not re-fetch already-acquired scenes

---

## F-038 — Incremental Ingestion + Idempotency + Run History

**Why:** Idempotent ingestion is critical for quota safety — never double-fetch.

**Depends on:** F-037

**Owns / creates:**
- `argus/ingest/acquire.py` (extend: check if scene already acquired before fetching)
- `argus/core/store.py` (add RunHistory table; add scene deduplication query)
- `argus/core/models.py` (add RunHistory: domain, target, t_start, t_end, scenes_fetched, observations_created)
- `tests/test_incremental_ingest.py`

**Idempotency rule:**
- If a `Scene` with the same `product_id` already exists with `ingest_status="ready"`:
  skip fetch, return existing Scene. Do not re-download.

**Acceptance criteria:**
- Running the same date range twice: second run fetches zero bytes
- `RunHistory` record created per run with counts
- Partial run (quota interrupted): can be resumed from last successful Scene

---

## F-039 — Observability (Metrics + Run Dashboard)

**Why:** Operators need to know the system is running, what it's processing, and whether
quota is being consumed within limits.

**Depends on:** F-038

**Owns / creates:**
- `argus/api/routers/status.py` (extend `GET /status` with full observability data)
- `argus/api/static/app.js` (extend: system status panel)
- `tests/test_observability.py`

**Metrics exposed:**
- Last run per domain: timestamp, status, scenes_fetched, observations_created
- Daily quota: CDSE bytes used/limit, Open-Meteo calls used/limit
- Alerts: sent today, failed today
- System: store size, artifacts dir size, memory usage

**Acceptance criteria:**
- `GET /status` returns all metrics in structured JSON
- Status panel in viewer shows last-run timestamp per domain
- Quota gauge shows remaining capacity

## Phase 8 Definition of Done

- [ ] ADR-0007 (scheduler) accepted before any F-03X task starts
- [ ] F-037–F-039 acceptance criteria met
- [ ] Idempotency test: re-run same day → zero bytes fetched
- [ ] Quota metrics visible in API and viewer
