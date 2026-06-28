# Argus — Developer Onboarding Guide

- **Audience:** New contributors and developers picking up the project
- **Last updated:** 2026-06-29
- **Estimated reading time:** 20 minutes + setup (~30 minutes)

Read this document before touching any code. It will save you significant time.

---

## 1. What This Project Is

Argus is a **Water Health Intelligence Platform**. It takes free public satellite imagery and
weather model data and produces:
- Oil slick detections with trajectory forecasts
- Inland water quality observations and bloom-risk forecasts
- Flood risk and acid deposition risk indices
- Plain-English reports answerable by AI — with every claim grounded to a store record

Implementation is complete through Phase 10 (12-page React dashboard, 21 API endpoints, all
4 observation domains, all 5 predictors, AI layer). Phase 11 is end-to-end integration testing,
performance validation, and MVP sign-off.

Before doing anything else, read:
1. `CLAUDE.md` — operating rules for this repo (strict, enforced)
2. `docs/status/DASHBOARD.md` — current state of every component
3. `BOARD.md` — what tasks exist and their status

---

## 2. Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.11+ | Required |
| uv | Latest | Python package manager (faster than pip) |
| Node.js | 18+ | For frontend |
| pnpm | 8+ | Frontend package manager |
| Git | 2.34+ | Version control |

**Optional but useful:**
- `sqlite3` CLI — for inspecting the store directly
- `gdal-bin` or QGIS — for working with geospatial outputs

---

## 3. Environment Setup

### 3.1 Clone and install backend

```bash
git clone https://github.com/CXLD10/argus.git
cd argus

# Create the virtual environment and install all dependencies
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

Verify the install:
```bash
argus version      # should print current version
pytest tests/ -x  # run the test suite (all offline, ~30s)
```

All 1072 tests should pass. If any fail, stop and diagnose before proceeding.

### 3.2 Install frontend

```bash
cd frontend
pnpm install
pnpm build         # verify the build compiles (0 TypeScript errors)
cd ..
```

### 3.3 Environment variables

Copy `.env.example` to `.env` and fill in credentials (never committed — it's in `.gitignore`):

```bash
cp .env.example .env
# Edit .env with your values
```

Key variables:

```bash
# CDSE satellite imagery (not needed for offline tests or demo mode)
ARGUS_CDSE_USER=your_email@example.com
ARGUS_CDSE_PASSWORD=your_password

# Anthropic API (not needed for tests; ARGUS_AI_OFFLINE=true bypasses it)
ANTHROPIC_API_KEY=sk-ant-...

# Set to "true" to skip LLM calls — recommended for local development
ARGUS_AI_OFFLINE=true
```

For local development, `ARGUS_AI_OFFLINE=true` is recommended unless you're specifically
working on the AI layer.

### 3.4 Verify the full system

```bash
# Backend
argus serve &
curl http://localhost:8000/health  # → {"status":"ok"}

# Frontend (separate terminal)
cd frontend && pnpm dev
# → http://localhost:5173
```

---

## 4. Project Structure

```
argus/
├── argus/                   ← Python package
│   ├── core/                ← store, models, config, logging
│   ├── domains/             ← D1-D4 observation plug-ins
│   │   ├── base.py          ← Domain protocol (DO NOT MODIFY without ADR)
│   │   ├── marine_oil/      ← D1: Sentinel-1 SAR oil detection
│   │   ├── inland_wq/       ← D2: Sentinel-2/3 water quality
│   │   ├── weather_hydro/   ← D3: Open-Meteo + S5P
│   │   └── hydro_chokepoints/ ← D4: DEM choke point analysis
│   ├── predict/             ← 5 predictor plug-ins
│   │   ├── base.py          ← Predictor protocol (DO NOT MODIFY without ADR)
│   │   ├── oil_trajectory/  ← OpenDrift subprocess
│   │   ├── wq_forecast/     ← gradient-boosted regression
│   │   ├── anomaly_detector/ ← STL + z-score
│   │   ├── flood_risk/      ← weighted linear combination
│   │   └── acid_deposition/ ← index product
│   ├── ai/                  ← AI assistant layer
│   │   ├── base.py          ← Assistant protocol (DO NOT MODIFY without ADR)
│   │   ├── client.py        ← Anthropic API wrapper + offline fallback
│   │   ├── grounding.py     ← GroundingGuard (enforces INV-4)
│   │   ├── reports.py       ← SituationReporter
│   │   ├── query.py         ← QueryPipeline (read-only NL queries)
│   │   └── anomaly_explain.py ← AnomalyExplainer
│   ├── api/                 ← FastAPI routes (21 endpoints)
│   ├── tasking/             ← AOI management, domain scheduling
│   ├── ingest/              ← data acquisition (CDSE, Open-Meteo, DEM)
│   ├── impact/              ← exposure intersection
│   └── alert/               ← alert delivery
├── tests/                   ← 56 test files, 1072 tests
├── frontend/                ← React 19 + Vite 8 dashboard
│   └── src/
│       ├── api/             ← typed fetch functions + TypeScript types
│       ├── store/           ← Zustand stores (aoi, map, ui)
│       ├── components/      ← shared UI components
│       └── pages/           ← 12 page components
├── config/
│   ├── aois/                ← area of interest GeoJSON definitions
│   ├── oil_types.yaml       ← registered oil types (INV-5: no default)
│   └── settings.yaml        ← platform configuration
└── docs/                    ← all documentation
```

---

## 5. Architecture Rules You Must Know

These are binding. Violating them breaks the architecture invariants defined in `CLAUDE.md §4`.

### INV-2: Domains are additive plug-ins

The spine (`argus.core`, `.tasking`, `.ingest`, `.impact`, `.api`, `.alert`), the `Predictor`
interface, and the `Assistant` interface are **never edited to accommodate a domain**. Adding a
domain means implementing the `Domain` protocol only.

### INV-3: Every observation must carry evidence_class

`evidence_class ∈ {measured, modeled, inferred}`. This is enforced at the store boundary.
Tests validate it. Never store a value as `measured` if it was not directly observed.

### INV-4: The LLM never originates a value

Every factual claim in AI-generated text must cite a record ID. The `GroundingGuard` enforces
this. If you're working on the AI layer, failing this invariant is a defect, not a warning.

### INV-5: No default oil type

`oil_type` is always read from `config/oil_types.yaml`. Missing or unregistered oil types
fail validation. Never add a code-level default.

### INV-6: No direct SQLite imports

All database access goes through `argus.core.store` accessors. `import sqlite3` is only
permitted in `argus/core/store.py`.

### INV-7: No live network in tests

Unit tests are offline by default. Live tests require `@pytest.mark.live` and are excluded
from `pytest tests/` (the default). Never add a network call to an unmarked test.

---

## 6. Git Workflow

### Author identity (required — no exceptions)

```bash
# Verify your identity before the first commit
git config user.name   # must be: CXLD10
git config user.email  # must be: 200384814+CXLD10@users.noreply.github.com
```

If these are wrong, fix them before committing:
```bash
git config user.name "CXLD10"
git config user.email "200384814+CXLD10@users.noreply.github.com"
```

### Commit format (conventional commits — required)

```
feat(scope): short imperative description

Optional body when the "why" is non-obvious.
```

Types: `feat` · `fix` · `docs` · `chore` · `refactor` · `test` · `ci` · `build` · `perf`

**Never:**
- Batch unrelated changes in one commit
- Use past tense ("added", "fixed")
- Include AI attribution or "Co-Authored-By: Claude" in commit messages

### Branch naming

```
feat/F-052-e2e-integration-tests
fix/oil-trajectory-missing-uncertainty
docs/developer-onboarding
chore/update-pyproject-deps
```

### Workflow

```bash
git checkout -b feat/F-052-e2e-tests
# ... implement ...
git add argus/tests/test_e2e.py
git commit -m "test(F-052): add end-to-end integration tests for all 4 domains"
git push -u origin feat/F-052-e2e-tests
gh pr create --title "test(F-052): E2E integration tests"
```

Do not push directly to `main`. Open a PR (self-review is fine for solo work).

---

## 7. Running Tests

```bash
# All unit tests (offline, ~30 seconds)
pytest tests/

# Verbose output
pytest tests/ -v

# Single test file
pytest tests/test_oil_trajectory.py -v

# Specific test
pytest tests/test_oil_trajectory.py::test_trajectory_uncertainty_present -v

# Live tests (require network + credentials)
pytest tests/ --live

# Coverage report
pytest tests/ --cov=argus --cov-report=term-missing
```

**When to run tests:**
- Before every commit: `pytest tests/ -x` (stop on first failure)
- After any change to `argus/core/`: `pytest tests/ -v` (core affects everything)
- After any store schema change: `pytest tests/ -k "store"` (schema contracts)

---

## 8. Running Domain Analysis

```bash
# Run the offline spike (synthetic SAR data, no credentials needed)
argus run --aoi tobago --since 2026-06-01

# Run against the Gulf of Paria demo AOI (offline mode)
argus run --aoi gulf-paria-tt --since 2026-06-01

# Run with live CDSE imagery (requires CDSE credentials)
argus run --aoi gulf-paria-tt --since 2026-06-01 --live

# Write artifacts to a custom directory
argus run --aoi gulf-paria-tt --since 2026-06-01 --output-dir /tmp/argus-run
```

Supported flags: `--aoi` (required), `--since` (required), `--live` (optional),
`--output-dir` (optional, default: `.argus/`).

CDSE credentials (`ARGUS_CDSE_USER`, `ARGUS_CDSE_PASSWORD`) are required when using `--live`.
Open-Meteo does not require credentials.

---

## 9. Adding a New Area of Interest

Create a file at `config/aois/<slug>.geojson`:

```json
{
  "id": "my-aoi-001",
  "name": "My AOI Display Name",
  "geometry": {
    "type": "Polygon",
    "coordinates": [[
      [-62.0, 10.0], [-61.0, 10.0], [-61.0, 11.0], [-62.0, 11.0], [-62.0, 10.0]
    ]]
  },
  "domains": ["marine_oil", "inland_wq", "weather_hydro", "hydro_chokepoints"],
  "active": true,
  "description": "Optional description"
}
```

Restart the server. The AOI appears in the header dropdown and is available to `argus run`.

---

## 10. Working on the Frontend

The frontend uses:
- **React 19** + **Vite 8** + **TypeScript** (strict mode)
- **Tailwind CSS v4** — uses `@theme` blocks in CSS, NOT `tailwind.config.js`
- **shadcn/ui** (New York, Neutral variant, CSS variables)
- **TanStack Query v5** for all server state
- **Zustand v5** for client state (AOI selection, map layers, sidebar)
- **pnpm** as the package manager

Key conventions:
- Path alias: `@/` maps to `./src/`
- All API types in `frontend/src/api/types.ts` mirror Pydantic schemas
- No inline styles — use Tailwind utilities or design system classes
- Skeleton components in `frontend/src/components/ui/skeleton.tsx` for loading states
- All 12 pages use `page-enter` class on the root `<div>` for route transition animation

### Running the frontend

```bash
cd frontend
pnpm dev          # dev server at http://localhost:5173
pnpm build        # production build (TypeScript check + Vite)
pnpm lint         # ESLint
```

### TypeScript strictness

The frontend uses strict TypeScript. All API response types must be explicitly typed — no `any`.
The build will fail if types are incorrect.

---

## 11. Working on the AI Layer

The AI layer is in `argus/ai/`. Key files:

- `client.py` — wraps `anthropic.Anthropic`. Checks `ARGUS_AI_OFFLINE` env var.
- `grounding.py` — `GroundingGuard` validates citations. Call `.validate(text, scope)`.
- `reports.py` — `SituationReporter.report(scope)` → `GroundedText`
- `query.py` — `QueryPipeline.answer(question, scope)` → `GroundedAnswer`
- `fallback.py` — deterministic template fallback used when `ARGUS_AI_OFFLINE=true`

**AI layer rules:**
1. All tests use `ARGUS_AI_OFFLINE=true` + recorded responses. No live API in the test suite.
2. The grounding guard is not optional — never bypass it.
3. The query pipeline's write-action check is before any LLM call — never move it after.
4. All AI responses include `model: str` and `citations: list[str]` fields.

---

## 12. Working on Predictors

Predictors live in `argus/predict/`. Each implements the `Predictor` protocol from `base.py`.

**Checklist for any predictor change:**
- [ ] `predict()` returns `Prediction` with `uncertainty` non-empty (INV-9)
- [ ] `predict()` uses `rng_seed` for any stochastic operation (INV-8)
- [ ] `evidence_class` is always `"modeled"` (INV-3)
- [ ] `validate()` returns a `SkillReport` with `passed_gate: bool`
- [ ] Tests cover both the happy path and the `passed_gate=False` case
- [ ] The skill gate test in `tests/test_skill_gate.py` covers the new predictor

---

## 13. The BOARD.md Workflow

`BOARD.md` is the authoritative task board. Before picking up any task:

1. Check the task is `TODO` or assigned to you as `IN_PROGRESS`
2. Read the feature spec in `docs/features/phase-N.md`
3. Understand the acceptance criteria before writing any code

When done:
1. Update the task status in `BOARD.md`
2. Add a HANDOFF note (see `CLAUDE.md §10` for format)
3. Append to `docs/status/program_log.md`

If you hit a blocker:
1. Set the task to `BLOCKED` in `BOARD.md`
2. Document the blocker in `docs/status/program_log.md`
3. If it requires an architecture decision, draft an ADR stub in `docs/adr/`

---

## 14. Current Phase — Phase 11

Tasks in `BOARD.md` Phase 11 section:
- **F-052** — End-to-end integration tests (all 4 domains, full pipeline)
- **F-053** — Performance profiling (< 10 min/AOI target on laptop)
- **F-054** — Documentation finalization (this guide is part of it)
- **F-055** — Demo dataset preparation (wire fixtures.ts as API fallback)
- **F-056** — MVP validation checklist + Josh sign-off

Phase 11 is the final phase before MVP. No new features are added in Phase 11 — the focus is
validation, performance, and polish.

---

## 15. Common Mistakes to Avoid

| Mistake | Consequence | Prevention |
|---|---|---|
| Direct `import sqlite3` outside `argus/core/store.py` | INV-6 violation — test will catch | Always use `argus.core.store` accessors |
| Setting `evidence_class="measured"` on a modelled value | INV-3 violation | Read the evidence_class rules carefully |
| Adding a network call to a test without `@pytest.mark.live` | CI breaks (INV-7) | Always mark live tests |
| Omitting `uncertainty` from a Prediction | INV-9 violation | Validator will reject the prediction |
| Committing with wrong git identity | Governance violation | Verify `git config user.name` before every session |
| Editing the spine to accommodate a domain | INV-2 violation | The Domain protocol is the only touch point |
| Using `pnpm` commands in the root directory | Confuses Node and Python | `cd frontend` first for all frontend commands |
