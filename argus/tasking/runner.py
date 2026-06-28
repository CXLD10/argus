"""Stateless domain task runner.

run_domain_task() is the single entrypoint for all scheduled and manually triggered
domain analysis tasks. It is called by:
  - APSchedulerBackend (scheduled runs)
  - The CLI `argus task run` command
  - The API `POST /task/run` endpoint (for manual triggering and Cloud Scheduler hooks)

Keeping the logic here — not inside the scheduler — ensures Cloud Run can invoke the
same function via HTTP without any changes to business logic (ADR-0007).
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from argus.aoi.loader import load_aoi
from argus.core.config import Settings
from argus.core.models import AnalysisRun, MonitorTarget, RunHistory
from argus.core.store import Store
from argus.tasking.base import ScheduledJob, TaskResult
from argus.tasking.quota_guard import check_domain_quota

logger = logging.getLogger(__name__)

# How far back to search for new scenes if no prior run exists.
_DEFAULT_LOOKBACK_HOURS = 72


def run_domain_task(
    job: ScheduledJob,
    store: Store,
    settings: Settings,
    config_dir: Path | None = None,
    *,
    dry_run: bool = False,
) -> TaskResult:
    """Execute one full domain analysis cycle for the AOI in *job*.

    Steps:
      1. Pre-flight quota check — skip and return if over limit.
      2. Load AOI from config.
      3. Resolve or construct MonitorTarget(s) for the domain.
      4. Import and instantiate the domain.
      5. search() → acquire() → analyze() → persist Observations.
      6. Record an AnalysisRun in the store.
      7. Return a populated TaskResult.

    This function is domain-agnostic. Domain-specific logic lives entirely inside
    each domain's Domain implementation.

    Args:
        job: Identifies domain and AOI to run.
        store: Argus store instance (INV-6).
        settings: Platform settings.
        config_dir: Override for the config directory root (default: Path("config")).
        dry_run: If True, skip acquisition and persistence (useful for quota tests).
    """
    cfg_dir = config_dir or Path("config")
    result = TaskResult(job_id=job.job_id, domain_id=job.domain_id, aoi_id=job.aoi_id)

    # Search window — set early so RunHistory can record it on all code paths.
    t1 = datetime.now(UTC)
    t0 = t1 - timedelta(hours=job.cadence_hours or _DEFAULT_LOOKBACK_HOURS)

    # ── 1. Quota check ────────────────────────────────────────────────────────
    decision = check_domain_quota(
        job.domain_id,
        store,
        daily_quota_gb=settings.cdse.daily_quota_gb,
        daily_call_limit=settings.open_meteo.daily_call_limit,
    )
    if not decision.allowed:
        logger.warning("Job %s skipped: %s", job.job_id, decision.reason)
        result.finish(status="skipped")
        result.error = decision.reason
        _save_run_history(result, store, t0, t1)
        return result

    # ── 2. Load AOI ───────────────────────────────────────────────────────────
    aoi_path = cfg_dir / "aois" / f"{job.aoi_id}.geojson"
    try:
        aoi = load_aoi(aoi_path)
    except Exception as exc:
        logger.error("Job %s: cannot load AOI %r — %s", job.job_id, job.aoi_id, exc)
        result.fail(f"AOI load error: {exc}")
        _save_run_history(result, store, t0, t1)
        return result

    # ── 3. Resolve MonitorTarget ──────────────────────────────────────────────
    try:
        target = _resolve_target(job, aoi.id, cfg_dir)
    except Exception as exc:
        logger.error("Job %s: cannot resolve MonitorTarget — %s", job.job_id, exc)
        result.fail(f"MonitorTarget error: {exc}")
        _save_run_history(result, store, t0, t1)
        return result

    # ── 4. Import domain ──────────────────────────────────────────────────────
    try:
        domain = _load_domain(job.domain_id, settings)
    except Exception as exc:
        logger.error("Job %s: cannot instantiate domain %r — %s", job.job_id, job.domain_id, exc)
        result.fail(f"Domain load error: {exc}")
        _save_run_history(result, store, t0, t1)
        return result

    # ── 5. Search / acquire / analyze ─────────────────────────────────────────

    try:
        refs = domain.search(target, t0, t1)
    except Exception as exc:
        logger.error("Job %s: domain.search() failed — %s", job.job_id, exc)
        result.fail(f"search() error: {exc}")
        _save_run_history(result, store, t0, t1)
        return result

    if not refs:
        logger.info("Job %s: no new scenes found in window %s–%s", job.job_id, t0.date(), t1.date())
        result.finish(status="complete", scenes=0, obs=0)
        _save_run_history(result, store, t0, t1)
        return result

    total_obs = 0
    total_bytes = 0

    for ref in refs:
        if dry_run:
            logger.debug("Job %s: dry_run — skipping acquire for %s", job.job_id, ref.product_id)
            continue

        try:
            acq = domain.acquire(ref)
        except Exception as exc:
            logger.warning("Job %s: acquire() failed for %s — %s", job.job_id, ref.product_id, exc)
            continue

        try:
            observations = domain.analyze(acq)
        except Exception as exc:
            logger.warning("Job %s: analyze() failed for %s — %s", job.job_id, ref.product_id, exc)
            continue

        run_id = str(uuid.uuid4())
        analysis_run = AnalysisRun(
            id=run_id,
            aoi_id=job.aoi_id,
            domain_id=job.domain_id,
            scene_id=acq.scene_id,
            started_at=t0,
            completed_at=datetime.now(UTC),
            status="complete",
            n_observations=len(observations),
        )
        store.save_analysis_run(analysis_run)

        for obs in observations:
            store.save_observation(obs)

        total_obs += len(observations)
        if ref.bytes_estimated:
            total_bytes += ref.bytes_estimated

    result.finish(status="complete", scenes=len(refs), obs=total_obs, bytes_used=total_bytes)
    logger.info(
        "Job %s complete: %d scene(s), %d observation(s)",
        job.job_id,
        len(refs),
        total_obs,
    )

    _save_run_history(result, store, t0, t1)
    return result


def _save_run_history(result: TaskResult, store: Store, t0: datetime, t1: datetime) -> None:
    """Persist a RunHistory record for the completed task."""
    # Map TaskResult status to RunHistory status. "running" means interrupted → "partial".
    status_map = {
        "complete": "complete",
        "failed": "failed",
        "skipped": "skipped",
        "running": "partial",
    }
    rh_status = status_map.get(result.status, "failed")
    run = RunHistory(
        id=str(uuid.uuid4()),
        domain_id=result.domain_id,
        aoi_id=result.aoi_id,
        t_start=t0,
        t_end=t1,
        scenes_fetched=result.scenes_fetched,
        observations_created=result.observations_created,
        bytes_used=result.bytes_used,
        status=rh_status,  # type: ignore[arg-type]  # validated by status_map keys
        error=result.error,
    )
    try:
        store.save_run_history(run)
    except Exception:
        logger.exception("Failed to persist RunHistory for job %s", result.job_id)


# ── Private helpers ────────────────────────────────────────────────────────────


def _resolve_target(job: ScheduledJob, aoi_id: str, cfg_dir: Path) -> MonitorTarget:
    """Build a simple MonitorTarget covering the AOI for the given domain.

    For D2 (inland_wq), the runner loads the first water-body GeoJSON under
    config/water_bodies/<aoi_id>/. For other domains it constructs a region target
    from the AOI geometry.

    The real production runner (future work) will iterate all targets in an AOI;
    this stub keeps F-037 self-contained.
    """
    from argus.aoi.loader import load_aoi, load_water_body_target

    aoi_path = cfg_dir / "aois" / f"{aoi_id}.geojson"
    aoi = load_aoi(aoi_path)

    if job.domain_id == "inland_wq":
        wb_dir = cfg_dir / "water_bodies" / aoi_id
        geojson_files = sorted(wb_dir.glob("*.geojson")) if wb_dir.exists() else []
        if geojson_files:
            meta_path = wb_dir / (geojson_files[0].stem + "_meta.yaml")
            return load_water_body_target(
                geojson_files[0],
                meta_path=meta_path if meta_path.exists() else None,
                aoi_id=aoi_id,
            )

    # Default: region target covering the full AOI extent.
    return MonitorTarget(
        id=f"{aoi_id}_{job.domain_id}",
        aoi_id=aoi_id,
        kind="region",
        name=f"{aoi.name} ({job.domain_id})",
        geometry=aoi.geometry,
        domains=[job.domain_id],
    )


def _load_domain(domain_id: str, settings: Settings) -> Any:
    """Return a Domain instance for the given domain_id.

    Each domain is imported lazily to keep startup time fast and to avoid importing
    optional heavy dependencies until they are actually needed.
    """
    if domain_id == "marine_oil":
        from argus.domains.marine_oil.detector import MarineOilDomain

        return MarineOilDomain()
    if domain_id == "inland_wq":
        from argus.domains.inland_wq.analyzer import InlandWqDomain

        return InlandWqDomain()
    if domain_id == "hydro_chokepoints":
        from argus.domains.hydro_chokepoints.analyzer import HydroChokepointsDomain

        return HydroChokepointsDomain()
    if domain_id == "weather_hydro":
        from argus.domains.weather_hydro.analyzer import WeatherHydroDomain

        return WeatherHydroDomain()
    raise ValueError(f"Unknown domain_id {domain_id!r}. Register it in argus.tasking.runner._load_domain.")
