# ADR-0001 — Vertical Pipeline and Staged Architecture

- **Status:** Partially superseded (framing superseded by ADR-0003; pipeline decisions retained)
- **Date:** 2026-06-01 (estimated; original date unknown)
- **Deciders:** Josh
- **Note:** This is a RECONSTRUCTED STUB. The original document is unavailable. Decisions
  are reconstructed from references in ADR-0003 ("supersedes ADR-0001 §Decision-1; keeps its
  pipeline decisions") and from the architecture as it stands today. Treat as informational.
- **Related:** [ADR-0002](ADR-0002-data-and-simulation-stack.md) · [ADR-0003](ADR-0003-water-health-platform-and-domains.md)

---

## Context

Early framing of Argus as a marine/coastal hazard detector (oil slick detection with drift
trajectory). The original question was whether to build a single monolithic pipeline or a
staged, modular architecture.

---

## Decisions

### D1 — Staged, Event-Producing Pipeline (RETAINED in ADR-0003)

The system is a **staged pipeline**: observe → predict → assess → explain. Each stage
communicates by writing durable records to a shared metadata store, not by in-process function
calls to the next stage. This makes every step inspectable, re-runnable, and independently
testable.

**RETAINED:** This decision is the foundation of the v2.0 architecture. The "stages" are now
more precisely named (tasking → ingestion → analysis → prediction → impact → delivery), but
the event-sourcing principle is identical.

### D2 — Detector as Plug-in (SUPERSEDED by ADR-0003 D2)

The original `Detector` was conceived as a plug-in interface for different hazard types. This
was correct directionally but named for a single domain (oil detection). ADR-0003 generalizes
this into the `Domain` abstraction, which is more appropriate for a multi-domain platform.

**SUPERSEDED framing:** "detector plug-in" → `Domain` protocol (search + acquire + analyze).

### D3 — CLI-First Delivery (RETAINED)

The primary interface is a CLI (`argus run`, `argus serve`). The API and viewer are layers
on top. This allows offline, reproducible runs without a browser or service dependency.

### D4 — One Domain First (RETAINED as Sequencing Strategy)

Build one domain end-to-end before adding others. This de-risks the pipeline and proves the
architecture generalizes. The domain chosen was D1 oil (already specced; best exercises the
simulation layer). ADR-0003 D5 formalizes the two-tier milestone structure that extends this.

---

## Consequences

- The staged pipeline is the core architectural invariant. Every domain, predictor, and AI
  feature must fit within it.
- The original Detector interface is now the Domain protocol. No code should reference
  `Detector` (v1.0); use `Domain` (v2.0).

## Cost Validation

All decisions in ADR-0001 are purely architectural (no cost implications). Zero recurring cost.

---

*[STUB] If the original ADR-0001 is recovered, this document should be replaced.*
