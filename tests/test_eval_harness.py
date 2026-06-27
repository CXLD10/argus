"""F-009 tests: eval harness, scorer, and SkillReport scaffold."""

from __future__ import annotations

from pathlib import Path

import pytest

from argus.core.models import Observation
from argus.eval.harness import EvalCase, SkillReport, run
from argus.eval.scorer import EvalResult, score

_REPO_ROOT = Path(__file__).parent.parent
_TOBAGO_EVAL_CASE = _REPO_ROOT / "data" / "eval" / "tobago_2024.json"

_SIMPLE_TRUTH = {
    "type": "Polygon",
    "coordinates": [[[-61.0, 11.0], [-60.5, 11.0], [-60.5, 11.5], [-61.0, 11.5], [-61.0, 11.0]]],
}


@pytest.fixture(scope="module")
def tobago_case() -> EvalCase:
    return EvalCase.from_json(_TOBAGO_EVAL_CASE)


# ── EvalCase.from_json ────────────────────────────────────────────────────────


def test_eval_case_loads_id(tobago_case: EvalCase) -> None:
    assert tobago_case.id == "tobago_2024"


def test_eval_case_loads_domain(tobago_case: EvalCase) -> None:
    assert tobago_case.domain == "marine_oil"


def test_eval_case_loads_oil_type(tobago_case: EvalCase) -> None:
    """ADR-0006: oil_type must be present and non-empty."""
    assert tobago_case.oil_type == "crude_medium"


def test_eval_case_loads_truth_geometry(tobago_case: EvalCase) -> None:
    assert tobago_case.truth_geometry["type"] == "Polygon"


def test_eval_case_has_provenance(tobago_case: EvalCase) -> None:
    assert len(tobago_case.provenance) > 0


# ── harness.run() ─────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def eval_result(tobago_case: EvalCase) -> EvalResult:
    return run(tobago_case, fixture_mode=True)


def test_harness_run_returns_eval_result(eval_result: EvalResult) -> None:
    assert isinstance(eval_result, EvalResult)


def test_harness_run_eval_case_id(eval_result: EvalResult, tobago_case: EvalCase) -> None:
    assert eval_result.eval_case_id == tobago_case.id


def test_harness_run_has_observations(eval_result: EvalResult) -> None:
    assert eval_result.n_observations >= 0


def test_harness_run_produces_tp(eval_result: EvalResult) -> None:
    """Acceptance criterion: ≥1 TP when fixture blob overlaps truth polygon."""
    assert eval_result.true_positives >= 1


def test_harness_run_recall_positive(eval_result: EvalResult) -> None:
    assert eval_result.recall > 0.0


def test_harness_live_mode_raises(tobago_case: EvalCase) -> None:
    with pytest.raises(NotImplementedError):
        run(tobago_case, fixture_mode=False)


# ── scorer.score() ────────────────────────────────────────────────────────────


def _make_obs(geometry: dict, confidence: float = 0.8) -> Observation:
    return Observation(
        id="obs-score",
        analysis_run_id="run-score",
        scene_id="scene-score",
        obs_type="oil_slick",
        evidence_class="measured",
        geometry=geometry,
        area_km2=10.0,
        confidence=confidence,
        status="confirmed",
    )


_OBS_INSIDE = _make_obs({"type": "Point", "coordinates": [-60.75, 11.15]}, confidence=0.9)
_OBS_OUTSIDE = _make_obs({"type": "Point", "coordinates": [-59.0, 9.0]}, confidence=0.9)


def test_scorer_tp_when_observation_inside_truth() -> None:
    result = score("test", [_OBS_INSIDE], _SIMPLE_TRUTH)
    assert result.true_positives == 1


def test_scorer_fp_when_observation_outside_truth() -> None:
    result = score("test", [_OBS_OUTSIDE], _SIMPLE_TRUTH)
    assert result.false_positives == 1


def test_scorer_fn_when_no_observations() -> None:
    result = score("test", [], _SIMPLE_TRUTH)
    assert result.false_negatives == 1


def test_scorer_precision_equals_one_for_single_tp() -> None:
    result = score("test", [_OBS_INSIDE], _SIMPLE_TRUTH)
    assert result.precision == pytest.approx(1.0)


def test_scorer_recall_equals_one_for_single_tp() -> None:
    result = score("test", [_OBS_INSIDE], _SIMPLE_TRUTH)
    assert result.recall == pytest.approx(1.0)


def test_scorer_f1_equals_one_for_single_tp() -> None:
    result = score("test", [_OBS_INSIDE], _SIMPLE_TRUTH)
    assert result.f1 == pytest.approx(1.0)


def test_scorer_low_confidence_excluded() -> None:
    low_conf = _make_obs({"type": "Point", "coordinates": [-60.75, 11.15]}, confidence=0.1)
    result = score("test", [low_conf], _SIMPLE_TRUTH, min_confidence=0.5)
    assert result.true_positives == 0


# ── SkillReport scaffold ──────────────────────────────────────────────────────


def test_skill_report_is_dataclass() -> None:
    report = SkillReport(
        predictor_id="marine_oil_v1",
        eval_case_id="tobago_2024",
        precision=0.8,
        recall=0.75,
        f1=0.77,
        n_observations=3,
    )
    assert report.predictor_id == "marine_oil_v1"
    assert report.precision == pytest.approx(0.8)


# ── Store SkillReport scaffold ─────────────────────────────────────────────────


def test_store_skill_report_scaffold(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    from argus.core.store import Store

    store = Store(tmp_path / "argus.db")
    store.save_skill_report(
        report_id="report-001",
        predictor_id="marine_oil_v1",
        eval_case_id="tobago_2024",
        precision=0.8,
        recall=0.75,
        f1=0.77,
        n_observations=3,
        created_at=datetime(2024, 2, 7, 22, 0, tzinfo=UTC),
    )
    reports = store.get_skill_reports_for_case("tobago_2024")
    assert len(reports) == 1
    assert reports[0]["predictor_id"] == "marine_oil_v1"
    assert reports[0]["f1"] == pytest.approx(0.77)
