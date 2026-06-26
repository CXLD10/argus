# Argus — Change Log

Records structural changes to documentation, specs, and architecture.

---

## 2026-06-27 (Session 3)

| Change | Type | Impact |
|---|---|---|
| Deleted root duplicate files (ADR-0003/4, ARCHITECTURE, DATA_MODELS, PRD, phase-0 stubs) | Cleanup | One authoritative source per concept now enforced |
| Fixed broken relative links in docs/adr/ADR-0003 and ADR-0004 | Link fix | Links to PRD.md and ARCHITECTURE.md now resolve correctly |
| Created docs/architecture/ARCHITECTURE.md v2.1 | New doc | Production deployment section added; supersedes root file |
| Created docs/architecture/DATA_MODELS.md v2.1 | New doc | v1→v2 migration table, oil_type field; supersedes root file |
| Created docs/architecture/STACK.md | New doc | Full stack with license, cost, production deployment |
| Created ADR-0007 (scheduler, DRAFT) | New ADR | Pending Josh decision; required before Phase 8 |
| Created ADR-0008 (deployment strategy, Accepted) | New ADR | Vercel + GCP Cloud Run + Cloud Storage; INV-10 added |
| Updated CLAUDE.md: §13 git identity, §14 deployment constraints | Doc update | Binding governance for commits and production infra |
| Updated STACK.md: production deployment section | Doc update | Ties to ADR-0008 |
| Updated ARCHITECTURE.md §7: production deployment | Doc update | Vercel + Cloud Run + GCS documented |
| Rewrote README.md (production-quality open-source) | Doc rewrite | New from scratch; no legacy content |
| Created .gitignore, .gitattributes, .editorconfig | New files | Repository hygiene; prevents tracking of secrets/artifacts |
| Created config/oil_types.yaml, config/settings.yaml | New files | Oil type registry and settings template |
| Created scripts/harness/check_architecture.py (stub) | New file | Implements harness entry point; logic in Phase 3.5 |
| Added .gitkeep to empty directories | New files | Preserves directory structure in git |
| Initialized git repository | Infrastructure | First commit pending email confirmation |

---

## 2026-06-27 (Session 2)

| Change | Type | Impact |
|---|---|---|
| Created docs/ hierarchy (12 directories, 47 files) | Structure | All new; no migration needed |
| Corrected phase-0.md: v1.0 → v2.0 entity names | Spec correction | Blocks any agent who reads old version |
| Retired two-tier MVP definition | PRD update | Milestone structure changed; BOARD/ROADMAP updated |
| OQ-A resolved (full platform demo) | OQ resolution | Phase sequencing unaffected; framing changes |
| OQ-F resolved (configurable oil types) | OQ resolution | F-011 spec updated; oil_types.yaml introduced |
| ADR-0005 published (MVP redefinition) | New ADR | Supersedes PRD §5 v1 milestone framing |
| ADR-0006 published (oil type configurability) | New ADR | Resolves OQ-F; binds F-011 implementation |
| ADR-0001 + ADR-0002 reconstructed (stubs) | Stub creation | Preserves decision lineage; not authoritative |
| Phase 3.5, Phase 10, Phase 11 added to roadmap | Roadmap expansion | 3 new phases; 14 new features (F-018–F-023, F-045–F-056) |
| CLAUDE.md created at root | New doc | Supersedes any prior agent instructions |
| 22 architecture validators defined | New governance | Pre-session validation checklist created |
| Risk register created | New doc | 12 risks tracked |
| Technical debt register created | New doc | 6 debts tracked |
