# ADR-0008 — Production Deployment Strategy

- **Status:** Accepted
- **Date:** 2026-06-27
- **Deciders:** Josh
- **Related:** [ARCHITECTURE.md](../architecture/ARCHITECTURE.md) · [STACK.md](../architecture/STACK.md)
  · [ADR-0002](ADR-0002-data-and-simulation-stack.md) · [ADR-0005](ADR-0005-mvp-redefinition.md)

---

## Context

Argus is intended to remain deployed continuously for real users after the MVP. The deployment
architecture must balance four goals, in priority order:

1. **Lowest possible recurring cost** — a solo project with $300 GCP credits that must last
   many months, not be spent rapidly during development
2. **Production reliability** — automatic HTTPS, professional URLs, minimal operational overhead
3. **Developer experience** — easy deployment, fast iteration, no devops complexity
4. **Scalability** — can handle growth without architectural rework

The development environment (local WSL) is zero-cost and always will be. This ADR governs only
the **production deployment** that runs after MVP sign-off.

---

## Decisions

### D1 — Frontend: Vercel

Deploy the React + Vite + Tailwind dashboard (Phase 10 / `frontend/`) to **Vercel**.

**Why:** Automatic HTTPS, custom domain, instant deploys from main branch, global CDN,
zero ops, zero cost on the Hobby plan for open-source projects. No compute cost since it
serves static assets only; all data comes from the API.

**Cost impact:** $0/month on Hobby plan. Upgrade to Pro (~$20/month) only if team features
or advanced analytics are needed post-MVP.

**Constraint:** Vercel has bandwidth limits on Hobby (100 GB/month). For a monitoring platform
with primarily API-driven data, this is unlikely to be hit.

### D2 — API / Backend: GCP Cloud Run

Deploy the FastAPI application (`argus serve`) as a **Docker container on GCP Cloud Run**.

**Why:** Cloud Run scales to zero when idle — no requests means no cost. This is the critical
property for a monitoring platform that may have quiet periods. Billed per-request and
per-CPU-second while handling requests. First 2M requests/month are free.

**Cost impact at idle:** $0/month when no requests are received.
**Cost impact under load:** ~$0.40/million requests + $0.00002400/vCPU-second. For a
low-traffic environmental monitoring platform this is negligible; well within the $300 credits.

**Constraint:** Cloud Run instances are stateless and ephemeral. The artifact store and
database cannot live on the Cloud Run filesystem. See D3 and D4.

**Constraint:** Cold starts add latency (~1–3s) after idle periods. Acceptable for a
monitoring platform; document in USER_GUIDE.md.

### D3 — Artifact Store: GCP Cloud Storage

Store all acquired rasters, time-series parquets, and generated reports in a **GCP Cloud
Storage bucket** (`argus-artifacts`).

**Why:** Persistent across Cloud Run instances. Cheap at scale ($0.02/GB/month standard
storage). First 5 GB/month is free. Integrates directly with Cloud Run via service accounts.

**Cost impact:** At MVP scale (<5 GB of EO artifacts), effectively $0/month on free tier.
Beyond 5 GB, ~$0.02/GB/month — predictable and low.

**Local development:** Uses the local filesystem artifact directory (`data/artifacts/`).
`ARGUS_ENV=production` switches to GCS. The `argus.core.store` accessor handles both paths
transparently (no domain code changes needed).

### D4 — Database: Deferred (Cloud SQL vs. Supabase)

The production database choice is **not yet decided**. Two options are under consideration:

**Option A: Cloud SQL (PostgreSQL)**
- Pro: Native GCP integration, PostGIS available, familiar SQL
- Con: Minimum ~$7–15/month even for smallest instance (`db-f1-micro`); does NOT scale to zero
- Can be stopped manually during inactive periods but requires operational discipline
- **Cost impact:** ~$7–15/month continuously, or ~$0 if stopped and only started on demand

**Option B: Supabase Free Tier (PostgreSQL)**
- Pro: Free up to 500 MB database size, 50K API requests/day, automatic HTTPS, zero ops
- Con: External service (not GCP); 500 MB limit may be binding at scale; pauses after 1 week
  of inactivity on free tier
- **Cost impact:** $0 on free tier; $25/month if Pro tier is needed

**Decision pending:** The choice between Cloud SQL and Supabase will be made in Phase 11
(F-054 deployment documentation) once the expected database size is better understood.
A new ADR stub will be written when this decision is made.

**For MVP development:** SQLite local file. The store accessor migration (SQLite → PostgreSQL)
is a single swap behind `argus.core.store` per ADR-0002 D5.

### D5 — Secrets Management: GCP Secret Manager

All production secrets (CDSE credentials, CMEMS credentials, Anthropic API key, DB password)
are stored in **GCP Secret Manager** and injected into Cloud Run as environment variables at
runtime.

**Why:** Never secrets in code, Docker images, or config files. Secret Manager is free for
≤6 active secret versions and ≤10K access operations/month.

**Cost impact:** $0 on free tier for MVP-scale secret volume.

**Local development:** Secrets are set in `config/settings.local.yaml` (gitignored) or
environment variables. Never committed.

### D6 — CI/CD: GitHub Actions

Use **GitHub Actions** for continuous integration and deployment.

**Why:** Free for public repositories (unlimited minutes). No additional service to manage.
Deploys to Cloud Run via `google-github-actions/deploy-cloudrun`. Deploys to Vercel via
the Vercel GitHub integration (automatic).

**Cost impact:** $0 for public repositories.

**Pipeline (when implemented, Phase 11):**
```
push to main → GitHub Actions
  ├─ run tests (offline, no --live)
  ├─ ruff check + mypy
  ├─ build Docker image
  ├─ push to GCP Artifact Registry
  ├─ deploy to Cloud Run
  └─ Vercel deploy (triggered automatically by GitHub integration)
```

### D7 — Custom Domains

- **Frontend:** configured via Vercel dashboard (automatic HTTPS via Let's Encrypt)
- **Backend API:** Cloud Run custom domain mapping (automatic HTTPS via Google-managed certificate)
- Both resolve from the same apex domain; e.g. `argus.example.com` (frontend),
  `api.argus.example.com` (backend)

**Cost impact:** Custom domain on Vercel is free (Hobby plan). Cloud Run custom domain mapping
is free. Domain registration cost is external and Josh's responsibility.

---

## Architecture Invariants Added

This ADR introduces **INV-10:** every cloud service in production must support scale-to-zero.
Any exception requires a cost-justified ADR.

---

## Credit Conservation Rules

To maximize the lifespan of the $300 GCP credits:

1. **No always-on VMs.** Cloud Run only for compute.
2. **No Cloud SQL until needed.** Use SQLite in development; delay Cloud SQL provisioning
   until scale forces the migration. Estimate: not before Phase 11 or post-MVP.
3. **GCS lifecycle policies.** Set auto-deletion on raw acquisition cache older than 90 days.
4. **Cloud Run min-instances = 0.** Never set `--min-instances > 0` without explicit cost review.
5. **Artifact Registry cleanup.** Delete old Docker image tags automatically (lifecycle policy).
6. **Budget alerts.** Set a GCP budget alert at $20/month and $50/month to catch runaway costs.

---

## Cost Summary (Expected Monthly at MVP Scale)

| Service | Expected cost | Notes |
|---|---|---|
| Vercel (frontend) | $0 | Hobby plan |
| Cloud Run (API) | ~$0 | Scales to zero; free tier covers low traffic |
| Cloud Storage (artifacts) | ~$0 | ≤5 GB free tier |
| Secret Manager | $0 | Free tier |
| Artifact Registry | ~$0 | Small Docker images; lifecycle policy |
| Cloud SQL | $0 | Not provisioned until needed |
| GitHub Actions | $0 | Public repository |
| **Total** | **~$0/month** | Well within credit lifespan |

Worst case at active use: ~$5–10/month from Cloud Run CPU + GCS egress + Artifact Registry.

---

## What This Doesn't Cover

- Database migration from SQLite to PostgreSQL (handled in Phase 11 / F-054)
- Multi-region deployment (out of scope; single-region for MVP)
- CDN for API responses (CloudFlare free tier can be added post-MVP if needed)
- Observability beyond Cloud Run built-in logs (covered in Phase 8 / F-039)
