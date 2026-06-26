# Phase 3.5 — Foundation Hardening

- **Status:** Specced; waiting for Phase 3
- **Priority:** P0
- **Last updated:** 2026-06-27
- **Features:** F-018–F-023
- **Depends on:** Phase 3 complete (CP-1 achieved)
- **Related:** [phase-3.md](phase-3.md) · [phase-4.md](phase-4.md) · [VALIDATORS.md](../governance/VALIDATORS.md)

**Goal:** Harden the foundation before expanding to Domain D2. This phase ensures that
adding a second domain doesn't expose brittleness in the API contracts, error handling,
logging, or test infrastructure. No new user-visible features; all improvements are
architectural.

> This phase exists because F-018–F-023 were left unassigned in the original roadmap
> (gap between Phase 3 end at F-017 and Phase 4 start at F-024). These IDs are now
> assigned here. See docs/status/change_log.md.

---

## F-018 — API Contract Specification + OpenAPI Schema

**Why:** Before adding D2 endpoints, the D1 API contracts must be formally specified and
tested, so D2 additions don't break existing consumers.

**Depends on:** F-015 (FastAPI service exists)

**Owns / creates:**
- `docs/api/API_SPEC.md`
- `argus/api/schemas.py` (extend + finalize Pydantic models for all D1 endpoints)
- `tests/test_api_contracts.py` (contract tests: schema validation, status codes, attribution field)

**Acceptance criteria:**
- `GET /aois/{id}/observations` response validated against Pydantic schema in tests
- OpenAPI spec auto-generated at `GET /openapi.json` (FastAPI built-in)
- `_attribution` field present in any response containing Open-Meteo-derived data
- Breaking change to any response schema fails the contract test

---

## F-019 — Integration Test Framework + Harness Scripts

**Why:** Establish the offline fixture system and implement the first harness validation scripts.

**Depends on:** F-018

**Owns / creates:**
- `tests/conftest.py` (shared fixtures: store, mock_anthropic, mock_cdse, mock_open_meteo)
- `tests/fixtures/` (organized fixture directory with README)
- `scripts/harness/validate.sh` (grep-based VAL-008, VAL-010, VAL-017 checks)
- `scripts/harness/spec_health.sh` (checks VAL-001, VAL-002, VAL-013)
- `tests/harness/test_validators.py` (test that validators catch real violations)
- `scripts/harness/run_all.sh`

**Acceptance criteria:**
- `scripts/harness/validate.sh` passes on the current codebase
- `scripts/harness/validate.sh` catches a synthetic VAL-017 violation (hardcoded oil type)
- `tests/conftest.py` shared fixtures used consistently by all existing tests

---

## F-020 — Structured Error Handling + Typed Exception Registry

**Why:** Error handling in Phase 0–3 was ad-hoc. Before D2, establish a consistent error
model so agents know what exceptions to expect and how to handle them.

**Depends on:** F-019

**Owns / creates:**
- `argus/core/errors.py` (all typed exceptions: `ArgusError`, `CdseAuthError`,
  `QuotaExceededError`, `OilTypeRequiredError`, `OilTypeNotFoundError`, `ConfigError`,
  `BelowResolutionError`, `StoreError`, `GroundingError`, etc.)
- Update all existing code to use canonical exceptions from `errors.py`
- `tests/test_error_handling.py`

**Acceptance criteria:**
- All exceptions inherit from `ArgusError`
- Every user-facing error message is actionable (tells the user what to do)
- No `raise Exception("...")` or bare `raise ValueError(...)` in argus/ code

---

## F-021 — Structured Logging Framework

**Why:** Phase 0–3 logging is unstructured. Structured JSON logs enable the observability
dashboard (Phase 8, F-039) and make debugging reproducible.

**Depends on:** F-020

**Owns / creates:**
- `argus/core/logging.py` (structured logger wrapper: JSON lines; correlation IDs)
- Update all existing code to use `argus.core.logging.get_logger(__name__)`
- `tests/test_logging.py`

**Log format:**
```json
{"ts": "...", "level": "INFO", "module": "argus.ingest", "run_id": "...",
 "event": "scene_acquired", "scene_id": "...", "bytes": 12345}
```

**Acceptance criteria:**
- All log output from argus/ is valid JSON when `LOG_FORMAT=json` set in env
- `run_id` correlation ID threads through all stages of a `argus run` invocation
- No `print()` statements in argus/ code

---

## F-022 — Configuration Management + Environment Profiles

**Why:** Single settings.yaml is not enough for supporting test/dev/production profiles.

**Depends on:** F-021

**Owns / creates:**
- `config/settings.yaml` (base config)
- `config/settings.dev.yaml` (override for development)
- `config/settings.test.yaml` (override for test: temp paths, mock flags)
- `argus/core/config.py` (extend: profile loading, env override, validation)

**Acceptance criteria:**
- `ARGUS_PROFILE=test pytest` loads test settings automatically
- Invalid config (missing required field) fails at startup, not mid-run
- `config/settings.yaml` does not contain credentials (tests validate this)

---

## F-023 — Health Check System + Readiness Probes

**Why:** Before Phase 8 automation, the API needs formal health + readiness probes to
know if the system is ready to process a run.

**Depends on:** F-022

**Owns / creates:**
- `argus/api/routers/health.py`
- `tests/test_health.py`

**Endpoints:**
- `GET /health` — liveness: always 200 if server is running
- `GET /ready` — readiness: 200 if store accessible + config valid; 503 otherwise
- `GET /status` — richer status: phase progress, last run timestamp, quota remaining

**Acceptance criteria:**
- `GET /ready` returns 503 if SQLite DB is not accessible
- `GET /status` returns correct quota remaining from daily CDSE/Open-Meteo counters

## Phase 3.5 Definition of Done

- [ ] F-018–F-023 acceptance criteria met
- [ ] `scripts/harness/run_all.sh` passes on the codebase
- [ ] All exceptions in argus/ use canonical types from `errors.py`
- [ ] All log output is structured JSON when `LOG_FORMAT=json`
- [ ] No unstructured errors or bare exceptions remain
