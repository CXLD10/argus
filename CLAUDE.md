# CLAUDE.md — Argus Repository Operating Guide

- **Scope:** Every Claude session working on this repository reads this file first.
- **Last updated:** 2026-06-27
- **Status:** Active governance document

---

## 1. Project Identity

Argus is a **Water Health Intelligence Platform** that fuses free Earth-observation and weather
data into actionable intelligence about water bodies and water-related hazards. It monitors
lakes/reservoirs for algal blooms and quality decline, predicts rain-driven flooding, models
acid-deposition risk, finds hydrological choke points, and detects marine oil slicks — then
turns all outputs into plain-language reports answerable by AI.

**Development environment:** local WSL, zero cost. Zero recurring cost for data sources, tools,
and libraries. Zero exceptions.

**Production deployment (post-MVP):** Vercel (frontend) + GCP Cloud Run (API) + Cloud Storage
(artifacts). See §14 and ADR-0008. GCP $300 credits must last many months; maximize
scale-to-zero usage.

---

## 2. MVP Definition (Authoritative — ADR-0005)

The MVP is the **complete Argus Environmental Intelligence Platform**. It is complete only when:

- All 4 observation domains are operational (D1 oil, D2 inland WQ, D3 weather/hydro, D4 choke points)
- All 5 predictors are validated and operational
- The full AI layer (NL reports, NL query, anomaly explanation) is grounded and functional
- All 4 data integrations are functioning (CDSE, Open-Meteo, Copernicus DEM, CMEMS)
- The complete alerting pipeline is operational
- Every API endpoint is implemented and documented
- A polished, production-quality UI/UX dashboard exists
- All validation pipelines pass
- The full system completes an end-to-end run in < 10 min per AOI on a laptop

There is no "Vertical-Slice MVP" or "Platform MVP" checkpoint. Those terms are retired.
Internal phase checkpoints exist for tracking but are not MVP declarations.

---

## 3. Before Starting Any Task

**Read in this order:**
1. This file (CLAUDE.md)
2. `docs/status/DASHBOARD.md` — current project state
3. `BOARD.md` — task status (source of truth for what is TODO/IN_PROGRESS/DONE)
4. The feature spec for your assigned task (`docs/features/phase-N.md`)
5. The relevant domain spec if the task touches a domain (`docs/domains/`)
6. `docs/standards/TESTING.md` — testing requirements
7. `docs/standards/CODING.md` — coding conventions

**Run the pre-session checklist:**
- [ ] Is the task in BOARD.md with status TODO or explicitly IN_PROGRESS for me?
- [ ] Have I read the feature spec for this task?
- [ ] Are my owned files listed in the spec and not owned by another in-flight task?
- [ ] Do I understand the acceptance criteria?
- [ ] Will any dependency I'm adding incur recurring cost? (See §14 if yes.)
- [ ] Does any new infrastructure or service touch the GCP credits? (Must estimate impact.)

If any item fails: stop. Consult the relevant spec, then proceed.

---

## 4. Architecture Invariants (Never Violate)

These are binding. If any implementation would violate one, stop and raise it.

**INV-1 Zero cost for data and development.** No recurring cost for data sources, libraries,
or development tooling. All data sources (CDSE, Open-Meteo, CMEMS, DEM) must remain on free
tiers. Any library with copyleft (GPL) must be isolated behind a process boundary.
*Production hosting (GCP + Vercel) is governed separately by §14 and ADR-0008.*

**INV-2 Domain modularity.** Adding a domain = implement `Domain` protocol + register + optional
`Predictor` + exposure layer. The spine (`argus.core`, `.tasking`, `.ingest`, `.impact`, `.api`,
`.alert`), the `Predictor` interface, and the `Assistant` interface are never edited to
accommodate a domain.

**INV-3 Honesty by design.** Every value-bearing record carries
`evidence_class ∈ {measured, modeled, inferred}`. Values that are not observable from orbit
are never stored as `measured`. This is enforced at the schema level.

**INV-4 AI grounding.** The LLM layer never originates an environmental value. Every factual
claim in AI-generated text references a record id. Ungrounded claims are a defect, not a
warning.

**INV-5 No hardcoded oil type.** Oil trajectory simulations accept an `oil_type` parameter from
config. No default is acceptable. Validation fails if `oil_type` is absent or not in the
registered type registry.

**INV-6 Store abstraction.** All database access goes through `argus.core.store` accessors.
No stage or domain imports SQLite directly.

**INV-7 No live network in CI.** Unit tests are offline by default. Live network tests
require `--live` flag and are excluded from the default test run and CI.

**INV-8 Reproducibility.** Stochastic models use fixed RNG seeds. Pinned product IDs.
A case must re-run to tolerance.

**INV-9 Uncertainty required.** Every `Prediction` record must carry an `uncertainty` JSON
field. Predictors without uncertainty quantification are not trusted in the UI.

**INV-10 Scale-to-zero in production.** Every cloud service used in production must support
scale-to-zero (no always-on compute cost). Exceptions require an ADR with explicit cost
justification.

---

## 5. Repository Structure

```
argus/                     ← Python package (created F-000)
tests/                     ← test suite (F-000)
frontend/                  ← React + Vite dashboard (Phase 10)
config/                    ← AOI definitions, oil_types.yaml, settings
data/eval/                 ← EvalCase references (no raw imagery)
data/static/               ← small static fixtures (coastline, exposure)
docs/
  product/                 ← PRD.md, OPEN_QUESTIONS.md
  architecture/            ← ARCHITECTURE.md, DATA_MODELS.md, STACK.md
  adr/                     ← ADR-0001 through ADR-0008+
  domains/                 ← D1-D4 domain specifications
  prediction/              ← predictor specifications
  ai/                      ← AI assistant specification
  features/                ← phase-0.md through phase-11.md
  standards/               ← TESTING.md, CODING.md, QUOTAS.md
  status/                  ← DASHBOARD.md, program_log.md, decision_log.md, ...
  governance/              ← VALIDATORS.md, HARNESS.md
  api/                     ← API_SPEC.md
scripts/
  harness/                 ← validation scripts
CLAUDE.md                  ← this file (root, agent entry point)
README.md                  ← project overview (root)
BOARD.md                   ← live task board (root, operational)
ROADMAP.md                 ← phased roadmap (root, operational)
```

---

## 6. Key Interfaces (Stable — Do Not Modify Without ADR)

```python
# argus/domains/base.py
class Domain(Protocol):
    domain_id: str
    def search(self, target: MonitorTarget, t0, t1) -> list[SourceRef]: ...
    def acquire(self, ref: SourceRef) -> Acquisition: ...
    def analyze(self, acq: Acquisition) -> list[Observation]: ...

# argus/predict/base.py
class Predictor(Protocol):
    predictor_id: str
    def predict(self, ctx: PredictContext, rng_seed: int) -> Prediction: ...
    def validate(self, history: EvalSet) -> SkillReport: ...

# argus/ai/base.py
class Assistant(Protocol):
    def report(self, scope: Scope) -> GroundedText: ...
    def answer(self, question: str, scope: Scope) -> GroundedAnswer: ...
```

---

## 7. Data Entity Naming (v2.0 — Canonical)

| Concept | Canonical Name | Notes |
|---|---|---|
| What domains produce | `Observation` | Oil slick = `Observation(obs_type="oil_slick")` |
| Execution record | `AnalysisRun` | NOT DetectionRun (v1.0, retired) |
| AOI enabled-domains field | `domains` | NOT `hazard_types` (v1.0, retired) |
| Domain interface | `Domain` in `argus/domains/base.py` | NOT `Detector` in `argus/detect/` |
| Domain method | `analyze()` | NOT `detect()` |
| Oil slick subtype | `Observation(obs_type="oil_slick", evidence_class="measured")` | NOT a separate Detection class |
| Quality observation | `Observation(obs_type="chlorophyll_a"|"turbidity"|...)` | Per DATA_MODELS.md |

---

## 8. Testing Requirements (Summary)

Full rules: `docs/standards/TESTING.md`.

- Unit tests: offline, fixture-only, no network.
- Live integration tests: `--live` flag, skip in CI, document quota impact.
- AI layer tests: recorded/mock LLM responses, no live Anthropic API in default suite.
- Every acceptance criterion in a feature spec = a test or a manual verification step.
- `evidence_class` field must be present and correct in every Observation/Prediction test.

---

## 9. Quota Tracking

Full rules: `docs/standards/QUOTAS.md`.

- CDSE: ≤ 1 GB transfer/day (general-user quota).
- Open-Meteo: ≤ 10,000 calls/day (free non-commercial, CC BY 4.0 attribution required).
- Anthropic API: log all calls; keep within educational/free limits; degrade to templated
  reports if over budget.
- Every `Scene.bytes_or_calls` must be populated at acquisition.

---

## 10. Ending a Session

Before stopping, complete all of the following:

1. Update `BOARD.md`: set your task(s) to the correct status; never leave IN_PROGRESS on
   something that is actually blocked.
2. Append a HANDOFF note to `BOARD.md` (newest on top):
   ```
   ### YYYY-MM-DD — <task id(s)>
   - Did: <what landed + file paths>
   - State: <acceptance criteria pass/fail; tests green?>
   - Git: <branch/commit or "uncommitted">
   - Quota: <CDSE bytes / Open-Meteo calls used, if any live fetch>
   - Next: <single next action>
   - Blockers: <anything needing human or new ADR>
   ```
3. Append to `docs/status/program_log.md`.
4. If you made an architectural decision: add it to `docs/status/decision_log.md`.
5. If you changed a document structure: add it to `docs/status/change_log.md`.

---

## 11. Raising Issues

If you discover an inconsistency, architectural violation, or blocker:

1. Do not guess or work around it.
2. Document it in `docs/status/program_log.md` under today's date.
3. If it requires an architectural decision: draft an ADR stub in `docs/adr/`.
4. Update `BOARD.md` with a BLOCKED status and explanation.
5. Stop work on that task.

---

## 12. Open Questions

All open questions are tracked in `docs/product/OPEN_QUESTIONS.md`.
Resolved questions become ADRs. Never resolve an OQ by assumption — get explicit confirmation.

**Currently resolved:** OQ-A (full platform MVP), OQ-F (configurable oil types, no default).
**Currently open:** OQ-B (choke-point definition), OQ-C (calibration data), OQ-D (LLM tier),
OQ-E (NL-query read-only).

---

## 13. Git & Version Control Identity

These rules apply to every commit in this repository. **No exceptions.**

**Author identity:**
- Git username: `CXLD10`
- Git email: the GitHub no-reply email for the CXLD10 account
  (`{numeric-id}+CXLD10@users.noreply.github.com`; find the numeric ID at
  GitHub → Settings → Emails)
- Configure locally: `git config user.name "CXLD10"` and
  `git config user.email "{id}+CXLD10@users.noreply.github.com"`

**Never:**
- Use any other author name or email address
- Add Claude, Anthropic, AI assistants, or any other tool as a co-author
- Include "Generated by Claude", "Co-Authored-By: Claude", or any AI attribution in commit
  messages or trailers
- Modify the configured Git identity without explicit approval from Josh

**Commit discipline (conventional commits — required):**

Format: `<type>(<scope>): <short imperative description>`

| Type | Use for |
|---|---|
| `feat` | New feature that adds capability |
| `fix` | Bug fix |
| `docs` | Documentation changes only |
| `chore` | Maintenance, config, tooling, dependency updates |
| `refactor` | Code restructuring with no behaviour change |
| `test` | Adding or updating tests |
| `ci` | CI/CD configuration |
| `build` | Build system changes |
| `perf` | Performance improvements |

**Rules:**
- Commits must be small, logical, and atomic. One commit = one logical change.
- Present tense, imperative mood: "add oil type registry" not "added oil type registry".
- Scope is optional but encouraged: `feat(D1): add SAR dark-spot segmentation`.
- Body is optional for obvious changes; include it when the "why" is non-obvious.
- Never batch unrelated changes in a single commit to keep history clean and reviewable.
- Even as a solo developer: open a feature branch per feature, push, open a PR (self-review),
  merge. This keeps the main branch releasable at all times.

**Branch naming:** `feat/<feature-id>-<slug>`, `fix/<slug>`, `docs/<slug>`, `chore/<slug>`.
Example: `feat/F-000-repo-scaffold`, `docs/adr-0008-deployment`.

---

## 14. Production Deployment Constraints (ADR-0008)

These constraints govern all infrastructure and hosting decisions post-MVP.

**Principle:** minimize recurring cost; maximize use of GCP $300 credits; every service must
scale to zero or be free at rest. Full specification: `docs/adr/ADR-0008-deployment-strategy.md`.

**Hosting decisions (locked):**

| Layer | Service | Cost model |
|---|---|---|
| Frontend | Vercel (Hobby / Pro) | Free for open-source; zero ops |
| API / backend | GCP Cloud Run | Scales to zero; billed per-request |
| Artifact store | GCP Cloud Storage | ~$0.02/GB/month; free 5 GB/month |
| Database (dev) | SQLite (local) | Free |
| Database (prod) | Cloud SQL (PostgreSQL) or Supabase free tier | Cost impact requires ADR before provisioning |
| Domain / TLS | Vercel (frontend) + Cloud Run custom domain (backend) | Free with Vercel |

**Rules:**
- Never provision an always-on VM for the API. Cloud Run only.
- Never use Cloud SQL without first estimating monthly cost and confirming with Josh.
- GCP credits must last many months; optimize for idle periods costing near $0.
- Every new GCP service must include a brief cost impact statement in its ADR or feature spec.
- Production secrets (API keys, DB passwords) live in GCP Secret Manager; never in code or config files.
- `ARGUS_ENV=production` flag gates prod-only behaviour (Cloud Run paths, GCS artifact store).
