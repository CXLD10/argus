# Argus — Development Harness

- **Owner:** Architecture Governance
- **Last updated:** 2026-06-27
- **Purpose:** Specification for the harness that oversees repository health every session.
- **Related:** docs/governance/VALIDATORS.md, CLAUDE.md §3

The harness is the pre-flight check system. Every development session runs it before writing
code. It prevents architectural drift, catches spec violations, and surfaces blockers early.

---

## Harness Components

### 1. Repository Health Check

**What:** Verifies the repository is in a consistent, buildable state.

**Checks:**
- All directories in the expected hierarchy exist
- BOARD.md has been updated (HANDOFF entry exists for last session)
- No uncommitted changes from a prior session are in an ambiguous state
- All BLOCKED tasks in BOARD.md have documented blockers

**Script target:** `scripts/harness/repo_health.sh`

---

### 2. Specification Health Check

**What:** Validates that specifications are complete and consistent.

**Checks (subset of VALIDATORS.md):**
- VAL-001: All FRs have implementing features
- VAL-002: All features have task specs
- VAL-003: All tasks own files
- VAL-009: All docs have status headers
- VAL-013: All features have acceptance criteria
- VAL-015: No broken cross-references

**Script target:** `scripts/harness/spec_health.sh`

---

### 3. Architecture Consistency Check

**What:** Ensures code (once it exists) matches architectural contracts.

**Checks:**
- VAL-004: evidence_class present in Observation schema
- VAL-006: uncertainty present in Prediction schema
- VAL-008: No copyleft in spine modules (grep-based)
- VAL-010: No live network in unit tests (grep-based)
- VAL-017: No hardcoded oil types (grep-based)
- VAL-019: MonitorTarget resolution gate exists in code

**Script target:** `scripts/harness/arch_check.sh`

---

### 4. Progress Tracker

**What:** Generates a progress snapshot from BOARD.md.

**Output:**
- Count of DONE / IN_PROGRESS / TODO / BLOCKED tasks
- Phase completion percentages
- Distance to MVP
- Next recommended task

**Script target:** `scripts/harness/progress.sh`

---

### 5. Dependency Graph Validator

**What:** Verifies that task execution order is not violated.

**Checks:**
- No IN_PROGRESS or DONE task has an unmet dependency (a dep that is still TODO)
- No circular dependencies in the feature dependency graph

**Script target:** `scripts/harness/dep_check.sh`

---

### 6. Cost Compliance Check

**What:** Verifies no new paid dependencies have been introduced.

**Checks:**
- VAL-011: All deps in pyproject.toml are in the approved free list
- All services used in code are documented in STACK.md as free tier
- Open-Meteo attribution text exists in any output that uses Open-Meteo data (CC BY 4.0)

**Script target:** `scripts/harness/cost_check.sh`

---

### 7. Documentation Coverage Report

**What:** Reports which modules, domains, features, and ADRs have documentation.

**Metrics:**
- Docs per module (once argus/ exists)
- Feature specs vs. features in ROADMAP.md
- ADRs for all accepted architectural decisions
- Domain specs for all registered domains

**Script target:** `scripts/harness/doc_coverage.sh`

---

## Harness Entry Point

```bash
#!/bin/bash
# scripts/harness/run_all.sh
# Run before every development session

echo "=== Argus Development Harness ==="
echo "Date: $(date)"
echo ""

scripts/harness/repo_health.sh && echo "✓ Repo health" || echo "✗ REPO HEALTH FAILED"
scripts/harness/spec_health.sh && echo "✓ Spec health" || echo "✗ SPEC HEALTH FAILED"
scripts/harness/arch_check.sh  && echo "✓ Architecture" || echo "✗ ARCH CHECK FAILED"
scripts/harness/dep_check.sh   && echo "✓ Dependencies" || echo "✗ DEP CHECK FAILED"
scripts/harness/cost_check.sh  && echo "✓ Cost compliance" || echo "✗ COST CHECK FAILED"
scripts/harness/progress.sh

echo ""
echo "=== Harness complete. Proceed if all checks pass. ==="
```

---

## Harness Output Format

Each run should be appended to `docs/status/program_log.md` as:

```
### Harness Run — YYYY-MM-DD
- Repo health: PASS/FAIL
- Spec health: PASS/FAIL
- Architecture: PASS/FAIL
- Dependencies: PASS/FAIL
- Cost compliance: PASS/FAIL
- Progress: {N}/{total} tasks DONE; Phase {current}; {distance} to MVP
- Blockers: {list or "none"}
```

---

## Implementation Timeline

| Component | Target Feature | Status |
|---|---|---|
| `scripts/harness/` directory | F-000 (scaffold) | Placeholder created |
| `validate.sh` (grep-based validators) | F-019 (integration test framework) | TODO |
| `spec_health.sh` | F-019 | TODO |
| `arch_check.sh` | F-019 | TODO |
| `progress.sh` | F-039 (observability) | TODO |
| `doc_coverage.sh` | F-039 | TODO |
| Full automated harness | F-054 (documentation finalization) | TODO |
