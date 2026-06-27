"""F-005 tests: SQLite store — AnalysisRun and Observation CRUD."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from argus.core.models import AnalysisRun, Observation
from argus.core.store import Store

_GEOM = {
    "type": "Polygon",
    "coordinates": [[[-61.0, 11.0], [-60.9, 11.0], [-60.9, 11.1], [-61.0, 11.1], [-61.0, 11.0]]],
}


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "argus.db")


def _make_run(**kw: object) -> AnalysisRun:
    defaults: dict[str, object] = {
        "id": "run-001",
        "aoi_id": "tobago",
        "domain_id": "marine_oil",
        "scene_id": "scene-001",
        "started_at": datetime(2024, 2, 7, 22, 0, 0, tzinfo=UTC),
        "status": "complete",
        "n_observations": 1,
    }
    defaults.update(kw)
    return AnalysisRun(**defaults)  # type: ignore[arg-type]


def _make_obs(**kw: object) -> Observation:
    defaults: dict[str, object] = {
        "id": "obs-001",
        "analysis_run_id": "run-001",
        "scene_id": "scene-001",
        "obs_type": "oil_slick",
        "evidence_class": "measured",
        "geometry": _GEOM,
        "area_km2": 42.5,
        "confidence": 0.85,
        "status": "candidate",
    }
    defaults.update(kw)
    return Observation(**defaults)  # type: ignore[arg-type]


# ── AnalysisRun ───────────────────────────────────────────────────────────────


def test_save_and_get_analysis_run(store: Store) -> None:
    run = _make_run()
    store.save_analysis_run(run)
    retrieved = store.get_analysis_run(run.id)
    assert retrieved is not None
    assert retrieved.id == run.id


def test_analysis_run_nonexistent_returns_none(store: Store) -> None:
    assert store.get_analysis_run("no-such-run") is None


def test_analysis_run_round_trip_domain_id(store: Store) -> None:
    run = _make_run(domain_id="marine_oil")
    store.save_analysis_run(run)
    retrieved = store.get_analysis_run(run.id)
    assert retrieved is not None
    assert retrieved.domain_id == "marine_oil"


def test_analysis_run_round_trip_status(store: Store) -> None:
    run = _make_run(status="complete")
    store.save_analysis_run(run)
    retrieved = store.get_analysis_run(run.id)
    assert retrieved is not None
    assert retrieved.status == "complete"


def test_analysis_run_round_trip_n_observations(store: Store) -> None:
    run = _make_run(n_observations=3)
    store.save_analysis_run(run)
    retrieved = store.get_analysis_run(run.id)
    assert retrieved is not None
    assert retrieved.n_observations == 3


def test_analysis_run_round_trip_completed_at(store: Store) -> None:
    completed = datetime(2024, 2, 7, 22, 5, 0, tzinfo=UTC)
    run = _make_run(completed_at=completed)
    store.save_analysis_run(run)
    retrieved = store.get_analysis_run(run.id)
    assert retrieved is not None
    assert retrieved.completed_at == completed


def test_analysis_run_null_completed_at(store: Store) -> None:
    run = _make_run(completed_at=None, status="running")
    store.save_analysis_run(run)
    retrieved = store.get_analysis_run(run.id)
    assert retrieved is not None
    assert retrieved.completed_at is None


# ── Observation ───────────────────────────────────────────────────────────────


def test_save_and_get_observation(store: Store) -> None:
    obs = _make_obs()
    store.save_observation(obs)
    retrieved = store.get_observation(obs.id)
    assert retrieved is not None
    assert retrieved.id == obs.id


def test_observation_nonexistent_returns_none(store: Store) -> None:
    assert store.get_observation("no-such-obs") is None


def test_observation_round_trip_obs_type(store: Store) -> None:
    obs = _make_obs(obs_type="oil_slick")
    store.save_observation(obs)
    retrieved = store.get_observation(obs.id)
    assert retrieved is not None
    assert retrieved.obs_type == "oil_slick"


def test_observation_round_trip_evidence_class(store: Store) -> None:
    obs = _make_obs(evidence_class="measured")
    store.save_observation(obs)
    retrieved = store.get_observation(obs.id)
    assert retrieved is not None
    assert retrieved.evidence_class == "measured"


def test_observation_round_trip_area(store: Store) -> None:
    obs = _make_obs(area_km2=123.456)
    store.save_observation(obs)
    retrieved = store.get_observation(obs.id)
    assert retrieved is not None
    assert abs(retrieved.area_km2 - 123.456) < 0.001


def test_observation_round_trip_confidence(store: Store) -> None:
    obs = _make_obs(confidence=0.75)
    store.save_observation(obs)
    retrieved = store.get_observation(obs.id)
    assert retrieved is not None
    assert abs(retrieved.confidence - 0.75) < 0.001


def test_observation_round_trip_geometry(store: Store) -> None:
    obs = _make_obs()
    store.save_observation(obs)
    retrieved = store.get_observation(obs.id)
    assert retrieved is not None
    assert retrieved.geometry["type"] == "Polygon"


def test_get_observations_for_run(store: Store) -> None:
    run_id = "run-multi"
    store.save_observation(_make_obs(id="obs-a", analysis_run_id=run_id))
    store.save_observation(_make_obs(id="obs-b", analysis_run_id=run_id))
    store.save_observation(_make_obs(id="obs-c", analysis_run_id="other-run"))

    run_obs = store.get_observations_for_run(run_id)
    assert len(run_obs) == 2
    assert all(o.analysis_run_id == run_id for o in run_obs)


def test_get_observations_empty_run(store: Store) -> None:
    assert store.get_observations_for_run("no-run") == []
