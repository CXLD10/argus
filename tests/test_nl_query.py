"""F-032 tests: NL query pipeline — read-only, grounded, mocked LLM."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from argus.ai.base import GroundedAnswer
from argus.ai.client import ArgusAIClient
from argus.ai.grounding import GroundingGuard
from argus.ai.query import QueryPipeline, StoreQuery, _parse_store_query
from argus.api.app import create_app
from argus.core.errors import GroundingError
from argus.core.models import Prediction
from argus.core.store import Store

# ── Helpers ────────────────────────────────────────────────────────────────────

_GEOMETRY = {"type": "Point", "coordinates": [0.0, 0.0]}


def _make_anomaly_pred(pred_id: str) -> Prediction:
    return Prediction(
        id=pred_id,
        predictor_id="anomaly_detector_wq",
        source_obs_ids=[],
        kind="anomaly",
        evidence_class="modeled",
        uncertainty={"sigma": 3.1},
        rng_seed=42,
        attrs={"anomaly_detected": True, "z_score": 3.1},
    )


def _make_sq_json(kind: str | None = "anomaly") -> str:
    return json.dumps(
        {"target_id": None, "aoi_id": None, "obs_type": None, "kind": kind, "since_iso": None}
    )


# ── QueryPipeline: write-action refusal ───────────────────────────────────────


def test_write_action_delete_returns_refusal(tmp_store: Store) -> None:
    """AC: write-action question → polite refusal, no error, no LLM call."""
    pipeline = QueryPipeline(ArgusAIClient(), GroundingGuard(), tmp_store)
    result = pipeline.answer("Please delete the water body record for Lake A.")
    assert "I can only query records" in result.answer
    assert result.citations == []


def test_write_action_configure_returns_refusal(tmp_store: Store) -> None:
    pipeline = QueryPipeline(ArgusAIClient(), GroundingGuard(), tmp_store)
    result = pipeline.answer("Configure the alert threshold for turbidity.")
    assert "I can only query records" in result.answer


def test_write_action_update_returns_refusal(tmp_store: Store) -> None:
    pipeline = QueryPipeline(ArgusAIClient(), GroundingGuard(), tmp_store)
    result = pipeline.answer("Update the monitoring schedule.")
    assert "I can only query records" in result.answer


def test_write_action_create_returns_refusal(tmp_store: Store) -> None:
    pipeline = QueryPipeline(ArgusAIClient(), GroundingGuard(), tmp_store)
    result = pipeline.answer("Create a new AOI for the southern reservoir.")
    assert "I can only query records" in result.answer


def test_write_action_no_llm_call(tmp_store: Store) -> None:
    """Write-action refusal must not invoke the LLM."""
    client = ArgusAIClient()
    with patch.object(client, "complete", side_effect=AssertionError("LLM called!")):
        pipeline = QueryPipeline(client, GroundingGuard(), tmp_store)
        result = pipeline.answer("Delete all records.")
    assert "I can only query records" in result.answer


def test_write_action_returns_grounded_answer_type(tmp_store: Store) -> None:
    pipeline = QueryPipeline(ArgusAIClient(), GroundingGuard(), tmp_store)
    result = pipeline.answer("Remove the lake from monitoring.")
    assert isinstance(result, GroundedAnswer)


# ── QueryPipeline: read query with mocked LLM ─────────────────────────────────


def test_anomaly_query_mocked_llm_returns_grounded_answer(
    tmp_store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC: 'Which water bodies had anomalies last month?' → mocked rows → cited answer."""
    monkeypatch.delenv("ARGUS_AI_OFFLINE", raising=False)
    pred = _make_anomaly_pred("pred_q1")
    tmp_store.save_prediction(pred)

    grounded_answer = "An anomaly was detected with z_score 3.1 [pred_q1]."
    client = ArgusAIClient()
    with patch.object(
        client, "complete", side_effect=[_make_sq_json("anomaly"), grounded_answer]
    ):
        pipeline = QueryPipeline(client, GroundingGuard(), tmp_store)
        result = pipeline.answer("Which water bodies had anomalies last month?")

    assert isinstance(result, GroundedAnswer)
    assert "pred_q1" in result.citations


def test_anomaly_query_citations_non_empty(
    tmp_store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ARGUS_AI_OFFLINE", raising=False)
    pred = _make_anomaly_pred("pred_q2")
    tmp_store.save_prediction(pred)

    grounded_answer = "An anomaly was detected with sigma 3.1 [pred_q2]."
    client = ArgusAIClient()
    with patch.object(
        client, "complete", side_effect=[_make_sq_json("anomaly"), grounded_answer]
    ):
        pipeline = QueryPipeline(client, GroundingGuard(), tmp_store)
        result = pipeline.answer("Were there any anomalies last month?")

    assert len(result.citations) > 0


def test_invented_fact_in_answer_raises_grounding_error(
    tmp_store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC: Invented fact in answer → GroundingError."""
    monkeypatch.delenv("ARGUS_AI_OFFLINE", raising=False)
    pred = _make_anomaly_pred("pred_q3")
    tmp_store.save_prediction(pred)

    invented_answer = (
        "Chlorophyll-a reached 83.7 µg/L last month, indicating severe bloom conditions."
    )
    client = ArgusAIClient()
    with patch.object(
        client, "complete", side_effect=[_make_sq_json("anomaly"), invented_answer]
    ):
        pipeline = QueryPipeline(client, GroundingGuard(), tmp_store)
        with pytest.raises(GroundingError):
            pipeline.answer("Were there anomalies last month?")


def test_empty_store_query_returns_grounded_answer(
    tmp_store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No rows in store → synthesized non-factual answer passes the guard."""
    monkeypatch.delenv("ARGUS_AI_OFFLINE", raising=False)
    # Non-factual (no digits or risk keywords) → guard passes with empty citations.
    no_records_answer = "The store returned no matching records for your question."
    client = ArgusAIClient()
    with patch.object(
        client, "complete", side_effect=[_make_sq_json("anomaly"), no_records_answer]
    ):
        pipeline = QueryPipeline(client, GroundingGuard(), tmp_store)
        result = pipeline.answer("Were there any anomalies?")

    assert isinstance(result, GroundedAnswer)
    assert result.citations == []


# ── QueryPipeline: offline mode ───────────────────────────────────────────────


def test_query_offline_mode_returns_grounded_answer(
    tmp_store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ARGUS_AI_OFFLINE", "true")
    pipeline = QueryPipeline(ArgusAIClient(), GroundingGuard(), tmp_store)
    result = pipeline.answer("What is the chlorophyll-a level?")
    assert isinstance(result, GroundedAnswer)
    assert "offline" in result.answer.lower()


def test_query_offline_no_llm_call(
    tmp_store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ARGUS_AI_OFFLINE", "true")
    client = ArgusAIClient()
    with patch.object(client, "complete", side_effect=AssertionError("LLM called!")):
        pipeline = QueryPipeline(client, GroundingGuard(), tmp_store)
        result = pipeline.answer("What is the turbidity trend?")
    assert isinstance(result, GroundedAnswer)


# ── StoreQuery parsing ────────────────────────────────────────────────────────


def test_parse_store_query_valid_json() -> None:
    sq_json = '{"target_id": "wb_a", "kind": "anomaly"}'
    sq = _parse_store_query(sq_json)
    assert sq.target_id == "wb_a"
    assert sq.kind == "anomaly"


def test_parse_store_query_with_prose() -> None:
    """LLM may wrap JSON in prose — extract the JSON object."""
    text = 'Here is the query: {"kind": "forecast", "obs_type": "chlorophyll_a"}'
    sq = _parse_store_query(text)
    assert sq.kind == "forecast"
    assert sq.obs_type == "chlorophyll_a"


def test_parse_store_query_empty_json() -> None:
    sq = _parse_store_query("{}")
    assert sq.target_id is None
    assert sq.kind is None


def test_parse_store_query_invalid_returns_default() -> None:
    sq = _parse_store_query("not valid json at all")
    assert isinstance(sq, StoreQuery)
    assert sq.kind is None


def test_parse_store_query_null_fields_become_none() -> None:
    sq_json = '{"target_id": null, "kind": null, "obs_type": null}'
    sq = _parse_store_query(sq_json)
    assert sq.target_id is None
    assert sq.kind is None


# ── API: POST /query ──────────────────────────────────────────────────────────


@pytest.fixture()
def query_client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "argus_query_test.db"
    app = create_app(db_path=db_path, config_dir=Path("config"))
    return TestClient(app)


def test_query_endpoint_returns_200_offline(
    query_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """POST /query returns 200 in offline mode."""
    monkeypatch.setenv("ARGUS_AI_OFFLINE", "true")
    resp = query_client.post("/query", json={"question": "What is the water quality?"})
    assert resp.status_code == 200


def test_query_endpoint_write_action_returns_refusal(
    query_client: TestClient,
) -> None:
    """Write-action question → 200 with refusal text (no error)."""
    resp = query_client.post("/query", json={"question": "Delete all monitoring records."})
    assert resp.status_code == 200
    data = resp.json()
    assert "I can only query records" in data["answer"]


def test_query_endpoint_has_answer_field(
    query_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ARGUS_AI_OFFLINE", "true")
    resp = query_client.post("/query", json={"question": "Any anomalies?"})
    assert "answer" in resp.json()


def test_query_endpoint_has_citations_field(
    query_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ARGUS_AI_OFFLINE", "true")
    resp = query_client.post("/query", json={"question": "Any anomalies?"})
    assert "citations" in resp.json()
    assert isinstance(resp.json()["citations"], list)


def test_query_endpoint_has_attribution(
    query_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ARGUS_AI_OFFLINE", "true")
    resp = query_client.post("/query", json={"question": "Any anomalies?"})
    assert "_attribution" in resp.json()


def test_query_endpoint_model_not_latest(
    query_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ARGUS_AI_OFFLINE", "true")
    resp = query_client.post("/query", json={"question": "Summarize the data."})
    data = resp.json()
    assert "model" in data
    assert "latest" not in data["model"]
