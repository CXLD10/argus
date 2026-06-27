"""AI layer endpoints — grounded NL reports, query, and anomaly explanation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Request

from argus.ai.base import Scope
from argus.ai.client import ArgusAIClient
from argus.ai.grounding import GroundingGuard
from argus.ai.reports import SituationReporter
from argus.api.schemas import AIReportResponse
from argus.core.store import Store

router = APIRouter()


@router.get(
    "/waterbody/{target_id}/report",
    response_model=AIReportResponse,
    response_model_by_alias=True,
    tags=["ai"],
)
def get_waterbody_report(target_id: str, request: Request) -> AIReportResponse:
    """Generate a grounded NL situation report for a water body.

    Every factual sentence in the report is cited with a [record_id] that
    resolves to a real Observation or Prediction in the store (INV-4).
    Falls back to a deterministic template when ARGUS_AI_OFFLINE=true.
    """
    db_path: Path = request.app.state.db_path
    store = Store(db_path)

    now = datetime.now(UTC)
    scope = Scope(
        aoi_id=target_id,
        target_id=target_id,
        t0=now - timedelta(days=30),
        t1=now,
    )

    client = ArgusAIClient()
    guard = GroundingGuard()
    reporter = SituationReporter(client, guard, store)
    result = reporter.report(scope)

    return AIReportResponse(
        text=result.text,
        citations=result.citations,
        model=result.model,
    )
