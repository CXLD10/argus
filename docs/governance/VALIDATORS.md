# Argus — Architecture Validators

- **Owner:** Architecture Governance
- **Last updated:** 2026-06-27
- **Purpose:** Rules that must pass before every development session and before any PR merge.
- **Related:** docs/governance/HARNESS.md, CLAUDE.md

Run these validators at the start of every session. If any FAIL: stop, document in
`docs/status/program_log.md`, fix before proceeding.

---

## Specification Validators

### VAL-001 — Every FR maps to ≥1 Feature

**Check:** For each `FR-n` in `docs/product/PRD.md §7`, at least one feature ID exists in
`docs/features/` with a `Maps to` or `Requirements` reference.

**Failure:** "FR-{n} has no implementing feature in roadmap."

---

### VAL-002 — Every Feature maps to ≥1 Task

**Check:** For each feature F-XXX, the owning phase spec (`docs/features/phase-N.md`) contains
at least one task with acceptance criteria.

**Failure:** "F-{id} exists in roadmap but has no task specification."

---

### VAL-003 — Every Task owns at least one file

**Check:** Every task specification lists at least one `Owns / creates:` file path.

**Failure:** "Task in F-{id} has no owned files — cannot verify completion."

---

### VAL-004 — Every Observation record carries evidence_class

**Check:** Schema for `Observation` in `DATA_MODELS.md` includes `evidence_class` as required
(not nullable). Every test creating an `Observation` sets this field.

**Failure:** "Observation model missing required evidence_class field."

---

### VAL-005 — Every AI output carries citations

**Check:** `AIReport.citations` and `AIQueryLog.citations` are non-nullable JSON arrays.
Any test of AI output asserts `len(citations) > 0`.

**Failure:** "AI output created without citations — grounding invariant violated."

---

### VAL-006 — Every Prediction carries uncertainty

**Check:** `Prediction.uncertainty` is non-nullable JSON. Every `Predictor.predict()` call
in tests results in a `Prediction` with a non-null, non-empty `uncertainty` dict.

**Failure:** "Prediction.uncertainty is null — FR-12 violated."

---

### VAL-007 — No Predictor trusted in UI without SkillReport

**Check:** Any code path that surfaces a `Prediction` in the API or viewer must verify
`SkillReport.passed_gate == True` for the predictor. Test for the inverse: unvalidated
predictor must not appear in GET /forecasts.

**Failure:** "Predictor {id} has no passed SkillReport but is exposed in API."

---

### VAL-008 — No copyleft code in spine modules

**Check:** `argus/core/`, `argus/ingest/`, `argus/impact/`, `argus/api/`, `argus/alert/`
must not import any GPLv2/GPLv3-licensed library. `opendrift` imports may only appear in
`argus/predict/oil_trajectory/` subprocess runner.

**Failure:** "GPL-licensed import found outside isolation boundary."

---

### VAL-009 — Every document has a status header

**Check:** Every `.md` file under `docs/` begins with a YAML-like header containing at
minimum: `Status:`, `Last updated:`, `Owner:`.

**Failure:** "docs/{path} is missing required status header."

---

### VAL-010 — No live network in unit tests

**Check:** No test file in `tests/` (excluding `tests/integration/`) imports `requests`,
`httpx`, `sentinelhub`, `copernicusmarine`, `anthropic`, or makes socket connections without
the `live` pytest mark.

**Failure:** "tests/{file} makes live network call without --live flag."

---

### VAL-011 — Zero recurring cost

**Check:** Every dependency in `pyproject.toml` is either (a) open-source with no API cost,
or (b) documented in `docs/architecture/STACK.md` as a free-tier service with explicit
quota limits and attribution requirements.

**Failure:** "Dependency or service {name} incurs recurring cost — violates NFR-1."

---

### VAL-012 — No invented values in AI output

**Check:** `argus/ai/grounding.py` validates every AI response. The grounding guard rejects
any response with factual claims (numbers, dates, measurements, risks, conclusions) that are
not traceable to a record id in `citations`. Test: inject a hallucinated claim and assert
it is rejected.

**Failure:** "Grounding guard not implemented or bypassed."

---

### VAL-013 — Every Feature spec has acceptance criteria

**Check:** Every F-XXX block in `docs/features/phase-N.md` contains an `Acceptance criteria`
section with at least one criterion.

**Failure:** "F-{id} spec has no acceptance criteria — cannot be closed."

---

### VAL-014 — No orphaned Tasks

**Check:** Every task in `BOARD.md` maps to exactly one F-XXX in the roadmap, and vice versa.
No task exists without a parent feature; no feature has tasks not reflected in the board.

**Failure:** "Task {id} in BOARD.md has no parent feature." OR "F-{id} has no BOARD entry."

---

### VAL-015 — All cross-references resolve

**Check:** Every `[Link](path)` in every `.md` file in `docs/` resolves to an existing file.
No broken references.

**Failure:** "docs/{file} contains broken reference to {path}."

---

### VAL-016 — No duplicate canonical concepts

**Check:** Each concept has exactly one source of truth. Canonical locations:
- MVP definition → `docs/product/PRD.md §5` (and ADR-0005)
- Open questions → `docs/product/OPEN_QUESTIONS.md`
- Entity schemas → `docs/architecture/DATA_MODELS.md`
- Observability boundary → `docs/product/PRD.md §6`
- Technology stack → `docs/architecture/STACK.md`

**Failure:** "Concept {X} is defined in more than one canonical location."

---

### VAL-017 — Oil type must not be hardcoded

**Check:** `grep -r "generic_oil\|crude_oil\|diesel\|bunker" argus/` returns zero results
outside of `config/oil_types.yaml` and test fixtures. Every oil type reference in code
must read from the registry.

**Failure:** "Hardcoded oil type found in {file}:{line} — violates ADR-0006."

---

### VAL-018 — Every ADR has required fields

**Check:** Every `docs/adr/ADR-*.md` contains: `Status:`, `Date:`, `Deciders:`,
`## Decisions`, `## Consequences`, `## Cost Validation`.

**Failure:** "docs/adr/{ADR} missing required section {section}."

---

### VAL-019 — MonitorTarget resolution gate enforced

**Check:** `MonitorTarget.resolution_status == "below_resolution"` targets are never passed
to `Domain.search()` or `Domain.acquire()`. Test: create a below-resolution target, assert
it is rejected before any CDSE call.

**Failure:** "Below-resolution target processed — NFR-8 / ADR-0003 D3 violated."

---

### VAL-020 — evidence_class values never misassigned

**Check:** The following values are never stored as `evidence_class="measured"`:
pH, dissolved N/P, heavy metals, pathogens, acid-deposition index, modeled flood risk.
Test for each: attempt to create an Observation with wrong evidence_class → expect schema
rejection or assertion error.

**Failure:** "Modeled/not-observable value stored with evidence_class=measured."

---

### VAL-021 — SkillReport required before Phase 5 closes

**Check:** `F-029` (Predictor interface + validation gate) is in DONE status before
any Phase 5 feature is marked DONE in BOARD.md.

**Failure:** "Phase 5 feature marked DONE but F-029 is not DONE."

---

### VAL-022 — BOARD.md HANDOFF updated every session

**Check:** The HANDOFF log section in `BOARD.md` has an entry with today's date or the
most recent session date. If no entry exists for this session, the session is not complete.

**Failure:** "Session ended without HANDOFF note in BOARD.md."

---

## Running the Validators

Until automated scripts exist (`scripts/harness/`), run manually:

```bash
# VAL-001: Check all FRs are covered
grep -o 'FR-[0-9]*' docs/product/PRD.md | sort -u

# VAL-010: Check for live network in tests
grep -r "import requests\|import anthropic\|import sentinelhub" tests/ \
  | grep -v "integration/"

# VAL-011: Check for paid services
grep -v "free\|open-source\|$0" docs/architecture/STACK.md

# VAL-015: Check broken references (requires a link checker)
# Use: markdown-link-check docs/**/*.md

# VAL-017: Check hardcoded oil types
grep -r "generic_oil\|crude_oil\|bunker" argus/ | grep -v "oil_types.yaml"
```

Automated validator script target: `scripts/harness/validate.sh` (created in F-019).
