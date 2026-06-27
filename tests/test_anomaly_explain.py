"""F-033 tests: anomaly explanation + triage — advisory, grounded, mocked LLM."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from argus.ai.anomaly_explain import AnomalyExplainer, AnomalyExplanation
from argus.ai.base import AIReport
from argus.ai.client import ArgusAIClient
from argus.ai.grounding import GroundingGuard
from argus.api.app import create_app
from argus.core.errors import GroundingError
from argus.core.models import Observation, Prediction
from argus.core.store import Store

# ── Helpers ────────────────────────────────────────────────────────────────────

_GEOMETRY = {"type": "Point", "coordinates": [0.0, 0.0]}
_VALID_CONFIDENCE = {"low", "medium", "high"}


def _make_anomaly_pred(pred_id: str, with_obs_ids: list[str] | None = None) -> Prediction:
    return Prediction(
        id=pred_id,
        predictor_id="anomaly_detector_wq",
        source_obs_ids=with_obs_ids or [],
        kind="anomaly",
        evidence_class="modeled",
        uncertainty={"sigma": 3.2},
        rng_seed=42,
        attrs={
            "anomaly_detected": True,
            "z_score": 3.2,
            "aoi_id": "lake_test",
            "target_id": "wb_test",
        },
    )


def _make_obs(obs_id: str, value: float = 0.35) -> Observation:
    return Observation(
        id=obs_id,
        analysis_run_id="run_001",
        scene_id="scene_001",
        obs_type="chlorophyll_a",
        evidence_class="measured",
        geometry=_GEOMETRY,
        area_km2=1.0,
        confidence=0.9,
        value=value,
        unit="ndci",
    )


def _grounded_response(pred_id: str, obs_id: str) -> str:
    return (
        f"HYPOTHESIS: Chlorophyll-a at 0.35 indicates elevated algal activity [{obs_id}]. "
        f"The z-score of 3.2 exceeds the anomaly threshold [{pred_id}].\n"
        "ADVISORY: Collect a water sample from the affected monitoring point "
        "and test for cyanobacteria and nutrient loading. This is advisory only.\n"
        "CONFIDENCE: medium"
    )


# ── AnomalyExplainer: offline mode ────────────────────────────────────────────


def test_explain_offline_returns_explanation(
    tmp_store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC: offline mode → AnomalyExplanation with template hypothesis + advisory."""
    monkeypatch.setenv("ARGUS_AI_OFFLINE", "true")
    pred = _make_anomaly_pred("pred_e1")
    tmp_store.save_prediction(pred)

    explainer = AnomalyExplainer(ArgusAIClient(), GroundingGuard(), tmp_store)
    result = explainer.explain("pred_e1")
    assert isinstance(result, AnomalyExplanation)


def test_explain_offline_confidence_valid(
    tmp_store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC: confidence label in {low, medium, high}."""
    monkeypatch.setenv("ARGUS_AI_OFFLINE", "true")
    pred = _make_anomaly_pred("pred_e2")
    tmp_store.save_prediction(pred)

    explainer = AnomalyExplainer(ArgusAIClient(), GroundingGuard(), tmp_store)
    result = explainer.explain("pred_e2")
    assert result.confidence in _VALID_CONFIDENCE


def test_explain_offline_hypothesis_non_empty(
    tmp_store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ARGUS_AI_OFFLINE", "true")
    pred = _make_anomaly_pred("pred_e3")
    tmp_store.save_prediction(pred)

    explainer = AnomalyExplainer(ArgusAIClient(), GroundingGuard(), tmp_store)
    result = explainer.explain("pred_e3")
    assert len(result.hypothesis) > 0


def test_explain_offline_advisory_non_empty(
    tmp_store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ARGUS_AI_OFFLINE", "true")
    pred = _make_anomaly_pred("pred_e4")
    tmp_store.save_prediction(pred)

    explainer = AnomalyExplainer(ArgusAIClient(), GroundingGuard(), tmp_store)
    result = explainer.explain("pred_e4")
    assert len(result.advisory) > 0


def test_explain_offline_has_report(
    tmp_store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC: explanation stored in AIReport with citations."""
    monkeypatch.setenv("ARGUS_AI_OFFLINE", "true")
    pred = _make_anomaly_pred("pred_e5")
    tmp_store.save_prediction(pred)

    explainer = AnomalyExplainer(ArgusAIClient(), GroundingGuard(), tmp_store)
    result = explainer.explain("pred_e5")
    assert isinstance(result.report, AIReport)
    assert len(result.report.citations) > 0


def test_explain_offline_report_kind_is_explanation(
    tmp_store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ARGUS_AI_OFFLINE", "true")
    pred = _make_anomaly_pred("pred_e6")
    tmp_store.save_prediction(pred)

    explainer = AnomalyExplainer(ArgusAIClient(), GroundingGuard(), tmp_store)
    result = explainer.explain("pred_e6")
    assert result.report.kind == "explanation"


def test_explain_offline_model_contains_template(
    tmp_store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ARGUS_AI_OFFLINE", "true")
    pred = _make_anomaly_pred("pred_e7")
    tmp_store.save_prediction(pred)

    explainer = AnomalyExplainer(ArgusAIClient(), GroundingGuard(), tmp_store)
    result = explainer.explain("pred_e7")
    assert "template" in result.model


# ── AnomalyExplainer: mocked LLM ─────────────────────────────────────────────


def test_explain_mocked_llm_returns_explanation(
    tmp_store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC: explanation generated from fixture context; returns AnomalyExplanation."""
    monkeypatch.delenv("ARGUS_AI_OFFLINE", raising=False)
    obs = _make_obs("obs_e1")
    pred = _make_anomaly_pred("pred_em1", with_obs_ids=["obs_e1"])
    tmp_store.save_observation(obs)
    tmp_store.save_prediction(pred)

    response = _grounded_response("pred_em1", "obs_e1")
    client = ArgusAIClient()
    with patch.object(client, "complete", return_value=response):
        explainer = AnomalyExplainer(client, GroundingGuard(), tmp_store)
        result = explainer.explain("pred_em1")

    assert isinstance(result, AnomalyExplanation)


def test_explain_mocked_llm_contains_hypothesis(
    tmp_store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC: explanation contains candidate hypothesis."""
    monkeypatch.delenv("ARGUS_AI_OFFLINE", raising=False)
    obs = _make_obs("obs_e2")
    pred = _make_anomaly_pred("pred_em2", with_obs_ids=["obs_e2"])
    tmp_store.save_observation(obs)
    tmp_store.save_prediction(pred)

    response = _grounded_response("pred_em2", "obs_e2")
    client = ArgusAIClient()
    with patch.object(client, "complete", return_value=response):
        explainer = AnomalyExplainer(client, GroundingGuard(), tmp_store)
        result = explainer.explain("pred_em2")

    assert "chlorophyll" in result.hypothesis.lower() or "z-score" in result.hypothesis.lower()


def test_explain_mocked_llm_contains_advisory(
    tmp_store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC: explanation contains recommended sampling action."""
    monkeypatch.delenv("ARGUS_AI_OFFLINE", raising=False)
    obs = _make_obs("obs_e3")
    pred = _make_anomaly_pred("pred_em3", with_obs_ids=["obs_e3"])
    tmp_store.save_observation(obs)
    tmp_store.save_prediction(pred)

    response = _grounded_response("pred_em3", "obs_e3")
    client = ArgusAIClient()
    with patch.object(client, "complete", return_value=response):
        explainer = AnomalyExplainer(client, GroundingGuard(), tmp_store)
        result = explainer.explain("pred_em3")

    assert len(result.advisory) > 0


def test_explain_mocked_llm_confidence_valid(
    tmp_store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC: confidence label present and in {low, medium, high}."""
    monkeypatch.delenv("ARGUS_AI_OFFLINE", raising=False)
    obs = _make_obs("obs_e4")
    pred = _make_anomaly_pred("pred_em4", with_obs_ids=["obs_e4"])
    tmp_store.save_observation(obs)
    tmp_store.save_prediction(pred)

    response = _grounded_response("pred_em4", "obs_e4")
    client = ArgusAIClient()
    with patch.object(client, "complete", return_value=response):
        explainer = AnomalyExplainer(client, GroundingGuard(), tmp_store)
        result = explainer.explain("pred_em4")

    assert result.confidence in _VALID_CONFIDENCE


def test_explain_mocked_llm_report_citations_non_empty(
    tmp_store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC: AIReport citations non-empty; grounding guard passes."""
    monkeypatch.delenv("ARGUS_AI_OFFLINE", raising=False)
    obs = _make_obs("obs_e5")
    pred = _make_anomaly_pred("pred_em5", with_obs_ids=["obs_e5"])
    tmp_store.save_observation(obs)
    tmp_store.save_prediction(pred)

    response = _grounded_response("pred_em5", "obs_e5")
    client = ArgusAIClient()
    with patch.object(client, "complete", return_value=response):
        explainer = AnomalyExplainer(client, GroundingGuard(), tmp_store)
        result = explainer.explain("pred_em5")

    assert len(result.report.citations) > 0


def test_explain_ungrounded_llm_raises_grounding_error(
    tmp_store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    """LLM response with invented values → GroundingError."""
    monkeypatch.delenv("ARGUS_AI_OFFLINE", raising=False)
    pred = _make_anomaly_pred("pred_em6")
    tmp_store.save_prediction(pred)

    ungrounded = (
        "HYPOTHESIS: Chlorophyll-a reached 83.7 µg/L due to industrial discharge.\n"
        "ADVISORY: Notify authorities immediately.\n"
        "CONFIDENCE: high"
    )
    client = ArgusAIClient()
    with patch.object(client, "complete", return_value=ungrounded):
        explainer = AnomalyExplainer(client, GroundingGuard(), tmp_store)
        with pytest.raises(GroundingError):
            explainer.explain("pred_em6")


def test_explain_missing_prediction_raises_value_error(tmp_store: Store) -> None:
    """Unknown prediction_id → ValueError."""
    explainer = AnomalyExplainer(ArgusAIClient(), GroundingGuard(), tmp_store)
    with pytest.raises(ValueError, match="not found"):
        explainer.explain("nonexistent_pred")


# ── API: GET /anomaly/{id}/explanation ────────────────────────────────────────


@pytest.fixture()
def explain_client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "argus_explain_test.db"
    app = create_app(db_path=db_path, config_dir=Path("config"))
    return TestClient(app)


def _get_store(client: TestClient) -> Store:
    return Store(client.app.state.db_path)


def test_explanation_endpoint_404_on_missing_prediction(
    explain_client: TestClient,
) -> None:
    resp = explain_client.get("/anomaly/nonexistent/explanation")
    assert resp.status_code == 404


def test_explanation_endpoint_returns_200_offline(
    explain_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ARGUS_AI_OFFLINE", "true")
    store = _get_store(explain_client)
    pred = _make_anomaly_pred("pred_api1")
    store.save_prediction(pred)

    resp = explain_client.get("/anomaly/pred_api1/explanation")
    assert resp.status_code == 200


def test_explanation_endpoint_has_hypothesis_field(
    explain_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ARGUS_AI_OFFLINE", "true")
    store = _get_store(explain_client)
    store.save_prediction(_make_anomaly_pred("pred_api2"))

    resp = explain_client.get("/anomaly/pred_api2/explanation")
    data = resp.json()
    assert "hypothesis" in data
    assert isinstance(data["hypothesis"], str)


def test_explanation_endpoint_has_advisory_field(
    explain_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ARGUS_AI_OFFLINE", "true")
    store = _get_store(explain_client)
    store.save_prediction(_make_anomaly_pred("pred_api3"))

    resp = explain_client.get("/anomaly/pred_api3/explanation")
    assert "advisory" in resp.json()


def test_explanation_endpoint_confidence_valid(
    explain_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC: confidence label present and in {low, medium, high}."""
    monkeypatch.setenv("ARGUS_AI_OFFLINE", "true")
    store = _get_store(explain_client)
    store.save_prediction(_make_anomaly_pred("pred_api4"))

    resp = explain_client.get("/anomaly/pred_api4/explanation")
    data = resp.json()
    assert data["confidence"] in _VALID_CONFIDENCE


def test_explanation_endpoint_has_attribution(
    explain_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ARGUS_AI_OFFLINE", "true")
    store = _get_store(explain_client)
    store.save_prediction(_make_anomaly_pred("pred_api5"))

    resp = explain_client.get("/anomaly/pred_api5/explanation")
    assert "_attribution" in resp.json()
