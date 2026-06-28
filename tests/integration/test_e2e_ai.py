"""F-052: AI layer end-to-end integration test — grounded report + NL query.

Covers the complete AI pipeline in offline mode (ARGUS_AI_OFFLINE=true):
  - SituationReporter.report() → grounded GroundedText with citations
  - QueryPipeline.answer() → grounded GroundedAnswer, write-action refusal
  - /waterbody/{id}/report API endpoint
  - /query API endpoint
  - Grounding guard rejects hallucinated claims (VAL-012)
  - AI outputs carry citations (VAL-005)

No live Anthropic API calls.  All LLM responses use the deterministic template
fallback (ARGUS_AI_OFFLINE=true) or recorded fixtures.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from argus.ai.base import GroundedAnswer, GroundedText, Scope
from argus.ai.client import ArgusAIClient
from argus.ai.fallback import generate_template_report
from argus.ai.grounding import GroundingGuard
from argus.ai.query import QueryPipeline
from argus.ai.reports import SituationReporter
from argus.api.app import create_app
from argus.core.errors import GroundingError
from argus.core.models import AnalysisRun, Observation, Prediction
from argus.core.store import Store

_REPO_ROOT = Path(__file__).parent.parent.parent
_FIXTURES = Path(__file__).parent.parent / "fixtures" / "ai"
_GEOMETRY = {"type": "Point", "coordinates": [-61.25, 11.15]}
_BASE_DATE = datetime.now(UTC)  # use "now" so reporter's 30-day lookback includes seeded obs


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_obs(obs_id: str, obs_type: str = "chlorophyll_a", value: float = 0.127) -> Observation:
    return Observation(
        id=obs_id,
        analysis_run_id="run_ai_001",
        scene_id="scene_ai_001",
        obs_type=obs_type,
        evidence_class="measured",
        geometry=_GEOMETRY,
        area_km2=0.5,
        confidence=0.9,
        value=value,
        unit="ndci",
        domain="inland_wq",
        target_id="wb-tobago",
        created_at=_BASE_DATE,
    )


def _make_pred(pred_id: str) -> Prediction:
    return Prediction(
        id=pred_id,
        predictor_id="anomaly_detector_wq",
        source_obs_ids=["obs_ai_001"],
        kind="anomaly",
        evidence_class="modeled",
        uncertainty={"sigma": 0.5},
        rng_seed=42,
        attrs={"anomaly_detected": False, "z_score": 0.5},
    )


def _seed_store(store: Store) -> None:
    run = AnalysisRun(
        id="run_ai_001",
        aoi_id="tobago",
        domain_id="inland_wq",
        scene_id="scene_ai_001",
        started_at=_BASE_DATE,
        status="complete",
        n_observations=1,
    )
    store.save_analysis_run(run)
    store.save_observation(_make_obs("obs_ai_001"))
    store.save_observation(_make_obs("obs_ai_002", obs_type="turbidity", value=0.35))
    store.save_prediction(_make_pred("pred_ai_001"))


@pytest.fixture()
def seeded_store(tmp_path: Path) -> Store:
    store = Store(tmp_path / "argus_ai.db")
    _seed_store(store)
    return store


@pytest.fixture()
def ai_scope() -> Scope:
    return Scope(
        aoi_id="tobago",
        target_id="wb-tobago",
        t0=_BASE_DATE - timedelta(days=30),
        t1=_BASE_DATE + timedelta(days=1),
    )


@pytest.fixture()
def ai_api_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    # Ensure offline mode is active before the app handles any requests.
    monkeypatch.setenv("ARGUS_AI_OFFLINE", "true")

    config_dir = tmp_path / "config"
    (config_dir / "aois").mkdir(parents=True)
    (config_dir / "aois" / "tobago.geojson").write_bytes(
        (_REPO_ROOT / "config" / "aois" / "tobago.geojson").read_bytes()
    )
    db_path = tmp_path / "argus_ai.db"
    store = Store(db_path)
    _seed_store(store)

    app = create_app(db_path=db_path, config_dir=config_dir)
    return TestClient(app)


# ── Offline mode: templated fallback ─────────────────────────────────────────


def test_ai_template_fallback_produces_grounded_text(ai_scope: Scope) -> None:
    """Offline fallback produces GroundedText with citations."""
    obs = [_make_obs("obs_t_001"), _make_obs("obs_t_002", obs_type="turbidity")]
    result = generate_template_report(ai_scope, obs)
    assert isinstance(result, GroundedText)
    assert len(result.citations) == 2
    assert "obs_t_001" in result.citations
    assert "obs_t_002" in result.citations


def test_ai_template_fallback_text_references_obs_ids(ai_scope: Scope) -> None:
    """VAL-005: template fallback text contains obs IDs (grounding invariant)."""
    obs = [_make_obs("obs_grounding_001")]
    result = generate_template_report(ai_scope, obs)
    assert "obs_grounding_001" in result.text


def test_ai_template_fallback_model_field_set(ai_scope: Scope) -> None:
    """GroundedText.model field must be set (non-empty)."""
    obs = [_make_obs("obs_m_001")]
    result = generate_template_report(ai_scope, obs)
    assert result.model


def test_ai_template_fallback_empty_obs_still_returns_text(ai_scope: Scope) -> None:
    result = generate_template_report(ai_scope, [])
    assert isinstance(result, GroundedText)
    assert result.text


# ── SituationReporter in offline mode ────────────────────────────────────────


def test_ai_reporter_offline_produces_grounded_text(
    seeded_store: Store, ai_scope: Scope, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SituationReporter in ARGUS_AI_OFFLINE mode returns GroundedText."""
    monkeypatch.setenv("ARGUS_AI_OFFLINE", "true")
    client = ArgusAIClient()
    guard = GroundingGuard()
    reporter = SituationReporter(client, guard, seeded_store)
    result = reporter.report(ai_scope)
    assert isinstance(result, GroundedText)


def test_ai_reporter_offline_citations_non_empty(
    seeded_store: Store, ai_scope: Scope, monkeypatch: pytest.MonkeyPatch
) -> None:
    """VAL-005: AI report must carry at least one citation."""
    monkeypatch.setenv("ARGUS_AI_OFFLINE", "true")
    client = ArgusAIClient()
    guard = GroundingGuard()
    reporter = SituationReporter(client, guard, seeded_store)
    result = reporter.report(ai_scope)
    assert len(result.citations) > 0


def test_ai_reporter_offline_text_non_empty(
    seeded_store: Store, ai_scope: Scope, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ARGUS_AI_OFFLINE", "true")
    client = ArgusAIClient()
    guard = GroundingGuard()
    reporter = SituationReporter(client, guard, seeded_store)
    result = reporter.report(ai_scope)
    assert len(result.text) > 10


# ── GroundingGuard ────────────────────────────────────────────────────────────


def test_ai_grounding_guard_accepts_valid_response(tmp_path: Path) -> None:
    """VAL-012: grounding guard accepts response when all citations exist in store."""
    fixture = json.loads((_FIXTURES / "grounded_response.json").read_text())
    # Seed a store with exactly the IDs the fixture cites (obs_001, pred_001)
    store = Store(tmp_path / "argus_guard_ok.db")
    store.save_observation(_make_obs("obs_001"))
    store.save_prediction(_make_pred("pred_001"))
    guard = GroundingGuard()
    result = guard.validate(fixture["text"], fixture["citations"], store)
    assert isinstance(result, GroundedText)
    assert result.citations == fixture["citations"]


def test_ai_grounding_guard_rejects_hallucinated_claims(seeded_store: Store) -> None:
    """VAL-012: grounding guard rejects citations that don't exist in the store."""
    guard = GroundingGuard()
    with pytest.raises(GroundingError):
        guard.validate(
            "The chlorophyll-a level is 0.45 ndci [nonexistent_record_999].",
            ["nonexistent_record_999"],
            seeded_store,
        )


def test_ai_grounding_guard_rejects_unfenced_factual_claims(seeded_store: Store) -> None:
    """VAL-012: grounding guard rejects factual claims without any citation."""
    fixture = json.loads((_FIXTURES / "ungrounded_response.json").read_text())
    guard = GroundingGuard()
    with pytest.raises(GroundingError):
        guard.validate(fixture["text"], fixture.get("citations", []), seeded_store)


# ── QueryPipeline ─────────────────────────────────────────────────────────────


def test_ai_query_write_action_refused(seeded_store: Store) -> None:
    """NL write-action questions must be refused before any LLM call."""
    pipeline = QueryPipeline(ArgusAIClient(), GroundingGuard(), seeded_store)
    result = pipeline.answer("Please delete the water body record for Lake A.")
    assert "I can only query records" in result.answer
    assert result.citations == []


def test_ai_query_write_delete_no_llm(seeded_store: Store) -> None:
    """Write-action refusal must not invoke the LLM (VAL-012 adjacent)."""
    client = ArgusAIClient()
    with patch.object(client, "complete", side_effect=AssertionError("LLM was called!")):
        pipeline = QueryPipeline(client, GroundingGuard(), seeded_store)
        result = pipeline.answer("Delete all anomaly records.")
    assert "I can only query records" in result.answer


def test_ai_query_write_configure_refused(seeded_store: Store) -> None:
    pipeline = QueryPipeline(ArgusAIClient(), GroundingGuard(), seeded_store)
    result = pipeline.answer("Configure the alert threshold.")
    assert "I can only query records" in result.answer


def test_ai_query_offline_answer_returns_grounded_answer(
    seeded_store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Read query in offline mode returns a GroundedAnswer."""
    monkeypatch.setenv("ARGUS_AI_OFFLINE", "true")
    pipeline = QueryPipeline(ArgusAIClient(), GroundingGuard(), seeded_store)
    result = pipeline.answer("What anomalies were detected this week?")
    assert isinstance(result, GroundedAnswer)


def test_ai_query_offline_answer_model_field_set(
    seeded_store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ARGUS_AI_OFFLINE", "true")
    pipeline = QueryPipeline(ArgusAIClient(), GroundingGuard(), seeded_store)
    result = pipeline.answer("Show me recent observations.")
    assert result.model


# ── API endpoints ─────────────────────────────────────────────────────────────


def test_ai_api_waterbody_report_endpoint_200(ai_api_client: TestClient) -> None:
    resp = ai_api_client.get("/waterbody/wb-tobago/report")
    assert resp.status_code == 200


def test_ai_api_waterbody_report_has_text(ai_api_client: TestClient) -> None:
    resp = ai_api_client.get("/waterbody/wb-tobago/report")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("text") or data.get("report")


def test_ai_api_query_endpoint_200(ai_api_client: TestClient) -> None:
    resp = ai_api_client.post("/query", json={"question": "What anomalies exist?"})
    assert resp.status_code == 200


def test_ai_api_query_write_action_refused_via_api(ai_api_client: TestClient) -> None:
    resp = ai_api_client.post("/query", json={"question": "Delete all records."})
    assert resp.status_code == 200
    data = resp.json()
    answer_text = data.get("answer", "")
    assert "I can only query records" in answer_text


def test_ai_api_anomaly_explanation_endpoint(ai_api_client: TestClient) -> None:
    """Anomaly explanation endpoint returns 200 (offline fallback) or 404 (pred not anomaly)."""
    resp = ai_api_client.get("/anomaly/pred_ai_001/explanation")
    # 200 = found and explained; 404 = prediction is not anomaly kind or not found
    assert resp.status_code in {200, 404}


def test_ai_api_status_endpoint(ai_api_client: TestClient) -> None:
    resp = ai_api_client.get("/status")
    assert resp.status_code == 200
