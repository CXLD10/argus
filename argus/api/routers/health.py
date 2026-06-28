"""Health, liveness, and readiness endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from argus.api.schemas import HealthResponse, QuotaStatus, ReadyResponse, RunSummary, StatusResponse
from argus.core.config import load_settings
from argus.core.store import Store

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    """Liveness probe — always returns 200 OK if the server is running."""
    return HealthResponse()


@router.get("/ready", response_model=ReadyResponse, tags=["meta"])
def ready(request: Request) -> ReadyResponse:
    """Readiness probe — returns 200 if the store is accessible, 503 otherwise."""
    db_path: Path = request.app.state.db_path
    try:
        store = Store(db_path)
        store.ping()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return ReadyResponse(status="ready")


@router.get("/status", response_model=StatusResponse, tags=["meta"])
def status(request: Request) -> StatusResponse:
    """System status: version, store accessibility, last run timestamp, quota."""
    db_path: Path = request.app.state.db_path
    settings = load_settings()

    store_accessible = False
    last_run_at: datetime | None = None
    cdse_bytes_today = 0
    domain_runs: list[RunSummary] = []

    try:
        store = Store(db_path)
        store.ping()
        store_accessible = True
        last_run_at = store.get_last_analysis_run_at()
        cdse_bytes_today = store.daily_bytes_total(datetime.now(UTC))
        domain_runs = _build_domain_runs(store)
    except Exception:
        pass

    cdse_limit_bytes = int(settings.cdse.daily_quota_gb * 1024**3)
    remaining = max(0, cdse_limit_bytes - cdse_bytes_today)

    return StatusResponse(
        store_accessible=store_accessible,
        last_analysis_run_at=last_run_at,
        quota=QuotaStatus(
            cdse_bytes_today=cdse_bytes_today,
            cdse_daily_limit_gb=settings.cdse.daily_quota_gb,
            cdse_remaining_bytes=remaining,
        ),
        domain_runs=domain_runs,
        open_meteo_calls_today=0,  # populated when D3 is implemented (F-041)
    )


def _build_domain_runs(store: Store) -> list[RunSummary]:
    """Summarise the most recent RunHistory entry per domain × AOI pair."""
    all_runs = store.get_run_history(limit=500)
    # Deduplicate: keep the newest (first, since sorted newest-first) per (domain, aoi).
    seen: set[tuple[str, str]] = set()
    summaries: list[RunSummary] = []
    for run in all_runs:
        key = (run.domain_id, run.aoi_id)
        if key not in seen:
            seen.add(key)
            summaries.append(
                RunSummary(
                    domain_id=run.domain_id,
                    aoi_id=run.aoi_id,
                    last_run_at=run.created_at,
                    last_run_status=run.status,
                    scenes_fetched=run.scenes_fetched,
                    observations_created=run.observations_created,
                    bytes_used=run.bytes_used,
                )
            )
    return summaries
