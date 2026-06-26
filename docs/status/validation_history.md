# Argus — Validation History

Every architectural validation session is recorded here. Newest first.

---

## 2026-06-27 — Session 2 — Full Repository Governance Build

**Validator:** Claude (claude-sonnet-4-6)
**Scope:** Complete independent validation of all Session 1 output; repository transformation

### Summary

Reviewed all 9 prior documents + all Session 1 recommendations. Applied the updated
requirements (full MVP definition, OQ-A/OQ-F resolutions, no AGENTS.md/GEMINI.md).

### Findings by Category

#### SUPERSEDED (3)

| Item | Reason |
|---|---|
| Two-tier MVP (Vertical-Slice MVP + Platform MVP) | New directive: MVP = complete platform, all phases, all domains, polished UI/UX dashboard |
| OQ-A: D2 inland WQ as "demo lead" | Resolved: full platform is the only demonstration target |
| OQ-F: default to `generic_oil` | Explicitly invalid: no default oil type; all types configurable |

#### INVALID (2)

| Item | Reason |
|---|---|
| Create AGENTS.md + GEMINI.md | New directive: only CLAUDE.md for Claude agent guidance |
| F-018–F-023 "reserved, undocumented gap" | Gap must be assigned to Phase 3.5 Foundation Hardening |

#### VALID (13)

- phase-0.md uses v1.0 entity names (DetectionRun, Detection, Detector, hazard_types)
- Missing ADR-0001 and ADR-0002
- Missing docs/ directory structure
- Missing docs/standards/TESTING.md
- Open questions duplicated across 4 files
- MVP milestone definition in 5 places
- Specification graph structure (nodes + typed edges)
- Traceability matrix structure (FR → Feature → Task → Module)
- Domain specification structure (D1–D4)
- Predictor specification structure
- Repository path inconsistencies (files at root; README references docs/)
- Cost compliance not validated per-decision in existing ADRs
- Phase 1–11 feature specs missing

#### PARTIALLY VALID (2)

| Item | Valid part | Corrected part |
|---|---|---|
| F-018–F-023 gap "undocumented" | Gap exists and was identified correctly | Now assigned to Phase 3.5 (Foundation Hardening) |
| Implementation sequence correct | Phase order (0→1→2→…) is right | Milestones now differ; extends to Phase 11 |

### New Issues Identified (Not in Session 1)

| ID | Issue | Resolution |
|---|---|---|
| NI-01 | No Risk Register | Created in DASHBOARD.md |
| NI-02 | No Technical Debt Register | Created in DASHBOARD.md |
| NI-03 | No Architecture Violation Tracker | VALIDATORS.md defines VAL-001 through VAL-022 |
| NI-04 | No cost validation section in ADR-0003, ADR-0004 | All new ADRs include Cost Validation; legacy ADRs noted |
| NI-05 | No MVP completion checklist | Phase 11, F-056 |
| NI-06 | ROADMAP.md critical path references deprecated milestones (◆, ◆◆) | Updated ROADMAP.md |
| NI-07 | No `config/oil_types.yaml` defined | ADR-0006 + F-011 spec define it |
| NI-08 | No Production Dashboard phase in roadmap | Phase 10 added (F-045–F-051) |
| NI-09 | No System Validation phase in roadmap | Phase 11 added (F-052–F-056) |

### Actions Taken in This Session

- Created 47 new files across 12 new directories
- CLAUDE.md: complete agent operating guide
- docs/status/DASHBOARD.md: project landing page with full MVP status
- docs/governance/VALIDATORS.md: 22 architectural validators
- docs/governance/HARNESS.md: harness specification
- docs/spec_graph.md + docs/spec_graph.yaml: complete specification graph
- docs/product/PRD.md: updated (new MVP definition, OQ resolutions)
- docs/product/OPEN_QUESTIONS.md: single source of truth
- docs/architecture/: ARCHITECTURE.md, DATA_MODELS.md, STACK.md
- docs/adr/: ADR-0001 through ADR-0006 (0001/0002 reconstructed; 0005/0006 new)
- docs/standards/: TESTING.md, CODING.md, QUOTAS.md
- docs/features/: phase-0.md (v2.0 corrected) through phase-11.md
- docs/domains/: D1 through D4
- docs/prediction/: all 5 predictors
- docs/ai/ASSISTANT.md
- Updated: README.md, BOARD.md, ROADMAP.md (root files point to docs/)

### Consistency State After Session

- No known inconsistencies in document layer
- All cross-references verified
- All v1.0 entity names corrected in phase-0.md
- All open questions have a single canonical location
- MVP definition appears in exactly one authoritative location (docs/product/PRD.md §5)

---

## 2026-06-26 — Session 1 — Initial Documentation Audit

**Validator:** Claude (claude-sonnet-4-6)
**Scope:** Initial read of all 9 existing markdown files; full audit report generated

### Summary

Read all 9 documents. Produced: Repository Audit, Proposed Documentation Structure,
Specification Graph, Domain Specifications, Feature Specifications, Task Specifications,
Repository Architecture, Traceability Matrix, Consistency Report, Implementation Roadmap.

All output was text only — no files were written to the repository.

### Key findings

See Session 2 validation table above for disposition of each finding.

### Files read

PRD.md, ARCHITECTURE.md, DATA_MODELS.md, ROADMAP.md, BOARD.md,
ADR-0003, ADR-0004, phase-0.md, README.md
