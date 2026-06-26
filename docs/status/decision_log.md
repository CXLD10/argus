# Argus — Decision Log

Every architectural, product, and process decision is recorded here.
Formal decisions become ADRs; informal/tactical decisions are logged here only.

---

## 2026-06-27 (Session 3)

| ID | Decision | Rationale | ADR |
|---|---|---|---|
| DEC-011 | Frontend → Vercel (Hobby plan) | Zero ops, free, automatic HTTPS, custom domain, global CDN | ADR-0008 |
| DEC-012 | API backend → GCP Cloud Run | Scales to zero; no always-on cost; billed per-request; $300 credits last months | ADR-0008 |
| DEC-013 | Artifact store → GCP Cloud Storage | Persistent across Cloud Run instances; 5 GB free; $0.02/GB beyond | ADR-0008 |
| DEC-014 | Database (prod) decision deferred to Phase 11 | Cloud SQL vs Supabase requires knowing actual data volume | ADR-0008 D4 |
| DEC-015 | INV-10 added: scale-to-zero mandatory in production | No always-on compute; GCP credits must last; exceptions need ADR | CLAUDE.md §14 |
| DEC-016 | Git author: CXLD10 / GitHub no-reply; no AI co-author attribution ever | Solo dev project; clean history; commits represent Josh's authorship | CLAUDE.md §13 |
| DEC-017 | Conventional commits required; atomic commits; feature branches | Maintainable history; solo dev with self-review PRs is best practice | CLAUDE.md §13 |
| DEC-018 | Root duplicate files deleted; one authoritative source per concept | Eliminated stub→authoritative confusion; repo safe to publish | — |

---

## 2026-06-27 (Session 2)

| ID | Decision | Rationale | ADR |
|---|---|---|---|
| DEC-001 | MVP = complete platform; two-tier MVP model retired | Full environmental intelligence platform is the only meaningful MVP milestone | ADR-0005 |
| DEC-002 | OQ-A resolved: full platform is the demo | No reduced vertical; the platform demonstrates all domains | ADR-0005 |
| DEC-003 | OQ-F resolved: no default oil type; configurable registry | No hardcoded assumption; oil type must be explicit in every simulation | ADR-0006 |
| DEC-004 | No AGENTS.md or GEMINI.md; only CLAUDE.md | Claude is the development agent; single adapter file reduces confusion | CLAUDE.md |
| DEC-005 | F-018–F-023 assigned to Phase 3.5 Foundation Hardening | Gap was unassigned; these features harden the foundation before D2 expansion | docs/features/phase-3.5.md |
| DEC-006 | Phase 10 (Production Dashboard) + Phase 11 (Validation) added | Full MVP requires polished UI/UX and system-wide validation | docs/features/ |
| DEC-007 | ADR-0001 + ADR-0002 reconstructed as stubs | Originals inaccessible; key decisions preserved via ADR-0003/0004 references | docs/adr/ |
| DEC-008 | All documentation moved to docs/ hierarchy; root files are operational only | Clean separation: docs/ = specifications; root = BOARD.md, ROADMAP.md, CLAUDE.md, README.md | README.md |
| DEC-009 | Cost validation section required in every new ADR | Zero-cost constraint must be explicitly validated per decision, not assumed | VALIDATORS.md VAL-020 |
| DEC-010 | `config/oil_types.yaml` is the registry for oil types | Central, versioned, extensible; no oil type can be used without being in this registry | ADR-0006 |
