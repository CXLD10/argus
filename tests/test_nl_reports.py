"""F-031 tests: NL situation reports — grounded, cited, mocked LLM."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from argus.ai.base import GroundedText, Scope
from argus.ai.client import ArgusAIClient
from argus.ai.grounding import GroundingGuard
from argus.ai.reports import SituationReporter
from argus.api.app import create_app
from argus.core.errors import GroundingError
from argus.core.models import Observation
from argus.core.store import Store

# ── Fixtures ──────────────────────────────────────────────────────────────────

_FIXTURES = Path(__file__).parent / "fixtures" / "ai"
_GEOMETRY = {"type": "Point", "coordinates": [0.0, 0.0]}


def _load_report_fixture() -> dict:
    return json.loads((_FIXTURES / "report_wq_grounded.json").read_text())


def _make_scope(target_id: str = "wb_test") -> Scope:
    now = datetime.now(UTC)
    return Scope(
        aoi_id="lake_test",
        target_id=target_id,
        t0=now - timedelta(days=30),
        t1=now,
    )


def _make_obs(obs_id: str, target_id: str = "wb_test", value: float = 0.127) -> Observation:
    return Observation(
        id=obs_id,
        analysis_run_id="run_001",
        scene_id="scene_001",
        obs_type="chlorophyll_a",
        evidence_class="measured",
        geometry=_GEOMETRY,
        area_km2=1.0,
        confidence=0.9,
        target_id=target_id,
        value=value,
        unit="ndci",
    )


def _seed_store(store: Store) -> None:
    store.save_observation(_make_obs("obs_r1"))
    store.save_observation(_make_obs("obs_r2", value=0.200))


# ── SituationReporter: offline mode ──────────────────────────────────────────


def test_report_offline_mode_returns_grounded_text(
    tmp_store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC: ARGUS_AI_OFFLINE=true → template GroundedText, no LLM call."""
    monkeypatch.setenv("ARGUS_AI_OFFLINE", "true")
    scope = _make_scope("wb_offline")
    reporter = SituationReporter(ArgusAIClient(), GroundingGuard(), tmp_store)
    result = reporter.report(scope)
    assert isinstance(result, GroundedText)


def test_report_offline_mode_no_observations(
    tmp_store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Offline mode with empty store returns a GroundedText with empty citations."""
    monkeypatch.setenv("ARGUS_AI_OFFLINE", "true")
    scope = _make_scope("wb_empty")
    reporter = SituationReporter(ArgusAIClient(), GroundingGuard(), tmp_store)
    result = reporter.report(scope)
    assert isinstance(result, GroundedText)
    assert result.citations == []


def test_report_offline_model_contains_template_marker(
    tmp_store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ARGUS_AI_OFFLINE", "true")
    scope = _make_scope("wb_offline")
    reporter = SituationReporter(ArgusAIClient(), GroundingGuard(), tmp_store)
    result = reporter.report(scope)
    assert "template" in result.model


# ── SituationReporter: mocked LLM ────────────────────────────────────────────


def test_report_mocked_llm_returns_grounded_text(
    tmp_store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC: mocked LLM returning grounded fixture → passes validation, returns GroundedText."""
    monkeypatch.delenv("ARGUS_AI_OFFLINE", raising=False)
    _seed_store(tmp_store)
    fixture = _load_report_fixture()

    client = ArgusAIClient()
    with patch.object(client, "complete", return_value=fixture["text"]):
        reporter = SituationReporter(client, GroundingGuard(), tmp_store)
        result = reporter.report(_make_scope())

    assert isinstance(result, GroundedText)


def test_report_mocked_llm_citations_include_obs_ids(
    tmp_store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC: AIReport.citations non-empty; all IDs exist in mocked store."""
    monkeypatch.delenv("ARGUS_AI_OFFLINE", raising=False)
    _seed_store(tmp_store)
    fixture = _load_report_fixture()

    client = ArgusAIClient()
    with patch.object(client, "complete", return_value=fixture["text"]):
        reporter = SituationReporter(client, GroundingGuard(), tmp_store)
        result = reporter.report(_make_scope())

    assert "obs_r1" in result.citations
    assert "obs_r2" in result.citations


def test_report_mocked_llm_citations_non_empty(
    tmp_store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ARGUS_AI_OFFLINE", raising=False)
    _seed_store(tmp_store)
    fixture = _load_report_fixture()

    client = ArgusAIClient()
    with patch.object(client, "complete", return_value=fixture["text"]):
        reporter = SituationReporter(client, GroundingGuard(), tmp_store)
        result = reporter.report(_make_scope())

    assert len(result.citations) > 0


def test_report_ungrounded_llm_raises_grounding_error(
    tmp_store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC: LLM returns an invented value with no citation → GroundingError."""
    monkeypatch.delenv("ARGUS_AI_OFFLINE", raising=False)
    ungrounded = (
        "The chlorophyll-a concentration is severely elevated at 47.3 µg/L, "
        "indicating a major bloom event."
    )
    client = ArgusAIClient()
    with patch.object(client, "complete", return_value=ungrounded):
        reporter = SituationReporter(client, GroundingGuard(), tmp_store)
        with pytest.raises(GroundingError):
            reporter.report(_make_scope())


def test_report_grounded_fixture_all_sentences_cited(
    tmp_store: Store, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Grounded fixture text: all factual sentences contain inline citations."""
    monkeypatch.delenv("ARGUS_AI_OFFLINE", raising=False)
    _seed_store(tmp_store)
    fixture = _load_report_fixture()

    client = ArgusAIClient()
    with patch.object(client, "complete", return_value=fixture["text"]):
        reporter = SituationReporter(client, GroundingGuard(), tmp_store)
        result = reporter.report(_make_scope())

    # The guard passed, so every factual sentence is cited.
    assert result.text == fixture["text"]


# ── Store: get_observations_by_target ────────────────────────────────────────


def test_get_observations_by_target_returns_matching(tmp_store: Store) -> None:
    """Store method returns observations for the given target_id."""
    tmp_store.save_observation(_make_obs("obs_t1", target_id="wb_alpha"))
    tmp_store.save_observation(_make_obs("obs_t2", target_id="wb_beta"))
    results = tmp_store.get_observations_by_target("wb_alpha")
    assert len(results) == 1
    assert results[0].id == "obs_t1"


def test_get_observations_by_target_empty_when_no_match(tmp_store: Store) -> None:
    results = tmp_store.get_observations_by_target("nonexistent_wb")
    assert results == []


def test_get_observations_by_target_since_filter(tmp_store: Store) -> None:
    """since= filter excludes observations older than the cutoff."""
    old_obs = _make_obs("obs_old", target_id="wb_x")
    old_obs = old_obs.model_copy(
        update={"created_at": datetime(2020, 1, 1, tzinfo=UTC)}
    )
    recent_obs = _make_obs("obs_new", target_id="wb_x")
    tmp_store.save_observation(old_obs)
    tmp_store.save_observation(recent_obs)

    cutoff = datetime(2023, 1, 1, tzinfo=UTC)
    results = tmp_store.get_observations_by_target("wb_x", since=cutoff)
    assert len(results) == 1
    assert results[0].id == "obs_new"


def test_get_observations_by_target_obs_type_filter(tmp_store: Store) -> None:
    """obs_types= filter returns only matching types."""
    tmp_store.save_observation(_make_obs("obs_chl", target_id="wb_y"))
    turb_obs = _make_obs("obs_turb", target_id="wb_y")
    turb_obs = turb_obs.model_copy(update={"obs_type": "turbidity"})
    tmp_store.save_observation(turb_obs)

    results = tmp_store.get_observations_by_target("wb_y", obs_types=["turbidity"])
    assert len(results) == 1
    assert results[0].id == "obs_turb"


def test_get_observations_by_target_ordered_newest_first(tmp_store: Store) -> None:
    """Results are ordered newest-first."""
    obs_a = _make_obs("obs_a", target_id="wb_z")
    obs_a = obs_a.model_copy(update={"created_at": datetime(2024, 1, 1, tzinfo=UTC)})
    obs_b = _make_obs("obs_b", target_id="wb_z")
    obs_b = obs_b.model_copy(update={"created_at": datetime(2024, 2, 1, tzinfo=UTC)})
    tmp_store.save_observation(obs_a)
    tmp_store.save_observation(obs_b)
    results = tmp_store.get_observations_by_target("wb_z")
    assert results[0].id == "obs_b"
    assert results[1].id == "obs_a"


# ── API: GET /waterbody/{id}/report ──────────────────────────────────────────


@pytest.fixture()
def ai_client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "argus_ai_test.db"
    app = create_app(db_path=db_path, config_dir=Path("config"))
    return TestClient(app)


def test_report_endpoint_returns_200_offline(
    ai_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """GET /waterbody/{id}/report returns 200 in offline mode."""
    monkeypatch.setenv("ARGUS_AI_OFFLINE", "true")
    resp = ai_client.get("/waterbody/test_lake/report")
    assert resp.status_code == 200


def test_report_endpoint_has_text_field(
    ai_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ARGUS_AI_OFFLINE", "true")
    resp = ai_client.get("/waterbody/test_lake/report")
    data = resp.json()
    assert "text" in data
    assert isinstance(data["text"], str)


def test_report_endpoint_has_citations_field(
    ai_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ARGUS_AI_OFFLINE", "true")
    resp = ai_client.get("/waterbody/test_lake/report")
    data = resp.json()
    assert "citations" in data
    assert isinstance(data["citations"], list)


def test_report_endpoint_has_model_field(
    ai_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ARGUS_AI_OFFLINE", "true")
    resp = ai_client.get("/waterbody/test_lake/report")
    data = resp.json()
    assert "model" in data
    assert "latest" not in data["model"]


def test_report_endpoint_has_attribution(
    ai_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ARGUS_AI_OFFLINE", "true")
    resp = ai_client.get("/waterbody/test_lake/report")
    data = resp.json()
    assert "_attribution" in data
