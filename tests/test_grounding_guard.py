"""F-030 tests: grounding guard, Anthropic client scaffold, templated fallback."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from argus.ai.base import GroundedText, Scope
from argus.ai.client import ArgusAIClient, _PINNED_MODEL
from argus.ai.fallback import generate_template_report, is_offline
from argus.ai.grounding import GroundingGuard, _is_factual, _split_sentences
from argus.core.errors import GroundingError
from argus.core.models import Observation, Prediction
from argus.core.store import Store

# ── Fixture directory ─────────────────────────────────────────────────────────

_FIXTURES = Path(__file__).parent / "fixtures" / "ai"


def _load_grounded() -> dict:
    return json.loads((_FIXTURES / "grounded_response.json").read_text())


def _load_ungrounded() -> dict:
    return json.loads((_FIXTURES / "ungrounded_response.json").read_text())


# ── Store helpers ─────────────────────────────────────────────────────────────

_GEOMETRY = {"type": "Point", "coordinates": [0.0, 0.0]}


def _make_obs(obs_id: str) -> Observation:
    return Observation(
        id=obs_id,
        analysis_run_id="run_001",
        scene_id="scene_001",
        obs_type="chlorophyll_a",
        evidence_class="measured",
        geometry=_GEOMETRY,
        area_km2=1.0,
        confidence=0.9,
        value=0.127,
        unit="ndci",
    )


def _make_pred(pred_id: str) -> Prediction:
    return Prediction(
        id=pred_id,
        predictor_id="anomaly_detector_wq",
        source_obs_ids=["obs_001"],
        kind="anomaly",
        evidence_class="modeled",
        uncertainty={"sigma": 0.5},
        rng_seed=42,
        attrs={"anomaly_detected": False, "z_score": 0.5},
    )


def _seed_store(store: Store) -> None:
    store.save_observation(_make_obs("obs_001"))
    store.save_prediction(_make_pred("pred_001"))


# ── GroundingGuard: grounded response ─────────────────────────────────────────


def test_grounded_fixture_passes_validation(tmp_store: Store) -> None:
    """AC: grounded response (fixture) → passes validation, returns GroundedText."""
    _seed_store(tmp_store)
    fixture = _load_grounded()
    guard = GroundingGuard()
    result = guard.validate(fixture["text"], fixture["citations"], tmp_store)
    assert isinstance(result, GroundedText)


def test_grounded_fixture_citations_preserved(tmp_store: Store) -> None:
    """Returned GroundedText citations match the input list."""
    _seed_store(tmp_store)
    fixture = _load_grounded()
    guard = GroundingGuard()
    result = guard.validate(fixture["text"], fixture["citations"], tmp_store)
    assert result.citations == fixture["citations"]


def test_grounded_fixture_text_preserved(tmp_store: Store) -> None:
    """Returned GroundedText text matches the input text."""
    _seed_store(tmp_store)
    fixture = _load_grounded()
    guard = GroundingGuard()
    result = guard.validate(fixture["text"], fixture["citations"], tmp_store)
    assert result.text == fixture["text"]


def test_grounded_model_is_pinned(tmp_store: Store) -> None:
    """AC: APIReport.model field set to pinned model version; never 'latest'."""
    _seed_store(tmp_store)
    fixture = _load_grounded()
    guard = GroundingGuard()
    result = guard.validate(fixture["text"], fixture["citations"], tmp_store)
    assert result.model == _PINNED_MODEL
    assert "latest" not in result.model


def test_grounded_model_not_unversioned(tmp_store: Store) -> None:
    """Model string must include a version identifier."""
    _seed_store(tmp_store)
    fixture = _load_grounded()
    guard = GroundingGuard()
    result = guard.validate(fixture["text"], fixture["citations"], tmp_store)
    # e.g. "claude-sonnet-4-6" contains at least one digit
    assert any(c.isdigit() for c in result.model)


# ── GroundingGuard: ungrounded response ──────────────────────────────────────


def test_ungrounded_fixture_raises_grounding_error(tmp_store: Store) -> None:
    """AC: ungrounded response (fixture with invented value) → raises GroundingError."""
    _seed_store(tmp_store)
    fixture = _load_ungrounded()
    guard = GroundingGuard()
    with pytest.raises(GroundingError):
        guard.validate(fixture["text"], [], tmp_store)


def test_ungrounded_error_mentions_sentence(tmp_store: Store) -> None:
    """GroundingError message contains the offending sentence."""
    fixture = _load_ungrounded()
    guard = GroundingGuard()
    with pytest.raises(GroundingError, match="47.3"):
        guard.validate(fixture["text"], [], tmp_store)


# ── GroundingGuard: citation existence ────────────────────────────────────────


def test_missing_citation_raises_grounding_error(tmp_store: Store) -> None:
    """Citation id not in store → GroundingError."""
    guard = GroundingGuard()
    text = "Non-factual sentence with no numbers or keywords."
    with pytest.raises(GroundingError, match="not found in store"):
        guard.validate(text, ["nonexistent_id"], tmp_store)


def test_citation_found_in_observations(tmp_store: Store) -> None:
    """Citations backed by Observation records pass the existence check."""
    store = tmp_store
    store.save_observation(_make_obs("obs_abc"))
    guard = GroundingGuard()
    result = guard.validate(
        "Chlorophyll-a at 0.05 [obs_abc].", ["obs_abc"], store
    )
    assert "obs_abc" in result.citations


def test_citation_found_in_predictions(tmp_store: Store) -> None:
    """Citations backed by Prediction records pass the existence check."""
    store = tmp_store
    store.save_prediction(_make_pred("pred_xyz"))
    guard = GroundingGuard()
    result = guard.validate(
        "No anomaly detected [pred_xyz].", ["pred_xyz"], store
    )
    assert "pred_xyz" in result.citations


def test_empty_citations_non_factual_text_passes(tmp_store: Store) -> None:
    """Non-factual text with no citations → passes (no factual claims to ground)."""
    guard = GroundingGuard()
    result = guard.validate(
        "Welcome to the Argus monitoring platform.", [], tmp_store
    )
    assert isinstance(result, GroundedText)
    assert result.citations == []


# ── Sentence splitting helper ─────────────────────────────────────────────────


def test_split_sentences_basic() -> None:
    text = "First sentence. Second sentence. Third sentence."
    parts = _split_sentences(text)
    assert len(parts) == 3


def test_split_sentences_single() -> None:
    text = "Only one sentence."
    parts = _split_sentences(text)
    assert len(parts) == 1
    assert parts[0] == "Only one sentence."


def test_split_sentences_empty() -> None:
    assert _split_sentences("") == []


# ── Factual detection helper ──────────────────────────────────────────────────


def test_factual_detects_digit() -> None:
    assert _is_factual("Value is 0.127 today.")


def test_factual_detects_bloom_keyword() -> None:
    assert _is_factual("A bloom event was observed.")


def test_factual_detects_elevated_keyword() -> None:
    assert _is_factual("Turbidity is elevated.")


def test_factual_non_factual_text() -> None:
    assert not _is_factual("Welcome to the platform.")


def test_factual_detects_anomaly_keyword() -> None:
    assert _is_factual("No anomaly detected.")


# ── ArgusAIClient: scaffold ───────────────────────────────────────────────────


def test_client_model_is_pinned() -> None:
    """AC: client.model returns the pinned model string, never 'latest'."""
    client = ArgusAIClient()
    assert client.model == _PINNED_MODEL
    assert "latest" not in client.model


def test_client_usage_starts_at_zero() -> None:
    client = ArgusAIClient()
    usage = client.usage
    assert usage["calls"] == 0
    assert usage["input_tokens"] == 0
    assert usage["output_tokens"] == 0


def test_client_complete_raises_import_error_without_anthropic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without the anthropic package, complete() raises ImportError (not AttributeError)."""
    import builtins

    real_import = builtins.__import__

    def mock_import(name: str, *args, **kwargs):
        if name == "anthropic":
            raise ImportError("No module named 'anthropic'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)
    client = ArgusAIClient()
    with pytest.raises(ImportError, match="anthropic package"):
        client.complete("Hello")


# ── Fallback: is_offline ──────────────────────────────────────────────────────


def test_is_offline_false_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ARGUS_AI_OFFLINE", raising=False)
    assert is_offline() is False


def test_is_offline_true_when_env_set(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC: ARGUS_AI_OFFLINE=true → is_offline() returns True."""
    monkeypatch.setenv("ARGUS_AI_OFFLINE", "true")
    assert is_offline() is True


def test_is_offline_true_when_env_1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARGUS_AI_OFFLINE", "1")
    assert is_offline() is True


def test_is_offline_false_when_env_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARGUS_AI_OFFLINE", "false")
    assert is_offline() is False


# ── Fallback: generate_template_report ────────────────────────────────────────


def test_template_report_no_observations(tmp_store: Store) -> None:
    """AC: fallback triggered when ARGUS_AI_OFFLINE=true → returns GroundedText."""
    from datetime import UTC, datetime

    scope = Scope(
        aoi_id="test_aoi",
        t0=datetime(2024, 2, 1, tzinfo=UTC),
        t1=datetime(2024, 2, 28, tzinfo=UTC),
    )
    result = generate_template_report(scope, [])
    assert isinstance(result, GroundedText)
    assert result.citations == []
    assert "test_aoi" in result.text


def test_template_report_with_observations(tmp_store: Store) -> None:
    """Template report cites each observation by id."""
    from datetime import UTC, datetime

    scope = Scope(
        aoi_id="lake_001",
        t0=datetime(2024, 2, 1, tzinfo=UTC),
        t1=datetime(2024, 2, 28, tzinfo=UTC),
    )
    obs = [_make_obs("obs_t1"), _make_obs("obs_t2")]
    obs[1] = obs[1].model_copy(update={"id": "obs_t2"})
    result = generate_template_report(scope, obs)
    assert "obs_t1" in result.citations
    assert "obs_t2" in result.citations
    assert "[obs_t1]" in result.text
    assert "[obs_t2]" in result.text


def test_template_report_model_contains_template_marker() -> None:
    """Fallback model string distinguishes templated from live-LLM output."""
    from datetime import UTC, datetime

    scope = Scope(
        aoi_id="x",
        t0=datetime(2024, 1, 1, tzinfo=UTC),
        t1=datetime(2024, 1, 31, tzinfo=UTC),
    )
    result = generate_template_report(scope, [])
    assert "template" in result.model


def test_template_report_grounding_guard_passes(tmp_store: Store) -> None:
    """Template report output passes the grounding guard when obs are in the store."""
    from datetime import UTC, datetime

    obs1 = _make_obs("obs_tg_a")
    obs2 = _make_obs("obs_tg_b")
    obs2 = obs2.model_copy(update={"id": "obs_tg_b"})
    tmp_store.save_observation(obs1)
    tmp_store.save_observation(obs2)

    # Use digit-free AOI id to avoid triggering the factual check on the header
    scope = Scope(
        aoi_id="test_lake",
        t0=datetime(2024, 2, 1, tzinfo=UTC),
        t1=datetime(2024, 2, 28, tzinfo=UTC),
    )
    report = generate_template_report(scope, [obs1, obs2])

    guard = GroundingGuard()
    result = guard.validate(report.text, report.citations, tmp_store)
    assert isinstance(result, GroundedText)
