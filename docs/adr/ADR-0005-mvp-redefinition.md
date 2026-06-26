# ADR-0005 — MVP Redefinition: Full Platform

- **Status:** Accepted
- **Date:** 2026-06-27
- **Deciders:** Josh
- **Supersedes:** The two-tier MVP milestone model in PRD v2.0 §5 (Vertical-Slice MVP + Platform MVP)
- **Resolves:** OQ-A (demo lead domain)
- **Related:** [PRD.md](../product/PRD.md) · [ROADMAP.md](../../ROADMAP.md) · [ADR-0003](ADR-0003-water-health-platform-and-domains.md)

---

## Context

The original PRD v2.0 defined two MVP milestones:
1. **Vertical-Slice MVP** — spine proven end-to-end on D1 oil (Phases 0–3)
2. **Platform MVP** — spine + D1 oil + D2 inland WQ + prediction + AI + viewer (Phase 7)

This model was designed to de-risk the architecture early and provide intermediate
deliverables. However, the project goal is a complete environmental intelligence platform
demonstrating all capabilities. Declaring "MVP complete" at Phase 3 or Phase 7 when two
domains (D3, D4), the full AI layer, and a production dashboard are missing would
misrepresent the product's maturity.

Additionally, OQ-A (which domain leads the platform demo) is moot if the demo is the
complete platform — there is no "demo lead" because all domains are present.

---

## Decisions

### D1 — MVP = Complete Platform

The MVP is achieved only when the complete Argus Environmental Intelligence Platform is
operational. The specific criteria are enumerated in PRD §5 and the MVP checklist (F-056).

All 4 domains, all 5 predictors, full AI layer, complete API, production-quality UI/UX
dashboard, validated end-to-end: that is the MVP.

### D2 — Retire Two-Tier Milestone Model

The terms "Vertical-Slice MVP" and "Platform MVP" are retired. They should not appear in
specifications, documentation, or code comments. If found, they are terminology debt.

### D3 — Internal Phase Checkpoints (Not Milestones)

Phase completions are **internal checkpoints**, not external milestones. They represent
technical readiness gates that ensure the architecture is sound before expansion:

| Checkpoint | Phases complete | Gate |
|---|---|---|
| CP-1: Oil pipeline complete | 0–3 | Domain + prediction + delivery working end-to-end on D1 |
| CP-2: WQ + prediction + AI | 4–7 | D2 operational; prediction engine validated; AI grounded |
| CP-3: Full domain coverage | 8–9 | D3 + D4 operational; automation running |
| CP-4: Production ready | 10–11 | Dashboard polished; system validated; MVP criteria met |

Only CP-4 = MVP.

### D4 — OQ-A Resolved

The platform demo is the complete Argus Environmental Intelligence Platform. All domains
are demonstrated simultaneously. D1 oil remains the first domain implemented (it best
exercises the simulation layer and is already specced) but it is not the "lead" —
all domains matter equally in the final product.

---

## Consequences

**Positive:**
- Honest about what the complete product is
- No premature "MVP complete" that hides missing capabilities
- Aligns all documentation, specs, and BOARD.md around a single clear target

**Negative/costs:**
- Longer path to MVP milestone
- More phases (10 + 11) required
- Phase 0–3 work was already specced for the old "Vertical-Slice MVP" framing — those
  specs remain valid; only the milestone framing changes

## Cost Validation

This ADR changes milestone definitions and project framing only. Zero cost impact.
All development remains on free tiers and open-source tools.

## Implementation

- BOARD.md: Remove ◆ and ◆◆ milestone markers from F-017 and F-036
- ROADMAP.md: Update critical path diagram; add Phase 10 + 11; change milestone language
- PRD.md: §5 updated to this definition (already done, v2.1)
- All feature specs: remove "MVP close" language; use "CP-N checkpoint" instead
