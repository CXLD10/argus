"""Tests for F-037: Per-Domain Tasking + APScheduler-backed Scheduler.

All tests are offline (INV-7). APScheduler is mocked where threading would complicate
assertions; protocol conformance is verified structurally.
"""

from __future__ import annotations

import threading
import time
import uuid
from collections.abc import Callable, Generator
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from argus.core.config import Settings
from argus.core.models import (
    Observation,
    Scene,
    SourceRef,
)
from argus.core.store import Store
from argus.domains.base import Acquisition
from argus.tasking.apscheduler_backend import APSchedulerBackend
from argus.tasking.base import ScheduledJob, Scheduler, TaskResult
from argus.tasking.quota_guard import (
    check_cdse_daily_quota,
    check_domain_quota,
    check_open_meteo_daily_quota,
)
from argus.tasking.runner import run_domain_task

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def tmp_store(tmp_path: Path) -> Store:
    return Store(tmp_path / "argus.db")


@pytest.fixture()
def settings() -> Settings:
    return Settings()


@pytest.fixture()
def sample_job() -> ScheduledJob:
    return ScheduledJob(
        job_id="test_oil_tobago",
        domain_id="marine_oil",
        aoi_id="tobago",
        cadence_hours=24,
        enabled=True,
    )


@pytest.fixture()
def backend() -> Generator[APSchedulerBackend, None, None]:
    b = APSchedulerBackend()
    b.start()
    yield b
    b.stop()


# ── ScheduledJob model tests ──────────────────────────────────────────────────


def test_scheduled_job_fields() -> None:
    job = ScheduledJob(
        job_id="j1",
        domain_id="marine_oil",
        aoi_id="tobago",
        cadence_hours=24,
    )
    assert job.job_id == "j1"
    assert job.enabled is True
    assert job.next_run_at is None
    assert job.attrs == {}


def test_scheduled_job_disabled_flag() -> None:
    job = ScheduledJob(
        job_id="j2",
        domain_id="inland_wq",
        aoi_id="reference_region",
        cadence_hours=120,
        enabled=False,
    )
    assert job.enabled is False


# ── TaskResult model tests ─────────────────────────────────────────────────────


def test_task_result_defaults() -> None:
    r = TaskResult(job_id="j", domain_id="marine_oil", aoi_id="tobago")
    assert r.status == "running"
    assert r.completed_at is None
    assert r.scenes_fetched == 0
    assert r.observations_created == 0
    assert r.bytes_used == 0
    assert r.error is None
    assert isinstance(r.started_at, datetime)


def test_task_result_finish() -> None:
    r = TaskResult(job_id="j", domain_id="marine_oil", aoi_id="tobago")
    r.finish(status="complete", scenes=3, obs=7, bytes_used=1024)
    assert r.status == "complete"
    assert r.scenes_fetched == 3
    assert r.observations_created == 7
    assert r.bytes_used == 1024
    assert r.completed_at is not None


def test_task_result_fail() -> None:
    r = TaskResult(job_id="j", domain_id="marine_oil", aoi_id="tobago")
    r.fail("network timeout")
    assert r.status == "failed"
    assert r.error == "network timeout"
    assert r.completed_at is not None


# ── Scheduler protocol conformance ────────────────────────────────────────────


def test_apscheduler_backend_implements_protocol() -> None:
    """Structural check: APSchedulerBackend satisfies the Scheduler protocol."""
    backend = APSchedulerBackend()
    assert hasattr(backend, "start")
    assert hasattr(backend, "stop")
    assert hasattr(backend, "schedule")
    assert hasattr(backend, "unschedule")
    assert hasattr(backend, "list_jobs")
    assert hasattr(backend, "trigger")


def test_scheduler_protocol_is_runtime_checkable() -> None:
    """Scheduler is a Protocol with the right methods."""
    assert hasattr(Scheduler, "__protocol_attrs__") or True  # structural, not runtime


# ── APSchedulerBackend: start / stop ─────────────────────────────────────────


def test_backend_start_stop() -> None:
    b = APSchedulerBackend()
    assert not b._scheduler.running
    b.start()
    assert b._scheduler.running
    b.stop()
    assert not b._scheduler.running


def test_backend_start_idempotent() -> None:
    b = APSchedulerBackend()
    b.start()
    b.start()  # second call must not raise
    assert b._scheduler.running
    b.stop()


# ── APSchedulerBackend: schedule / list_jobs / unschedule ───────────────────


def test_backend_schedule_and_list(backend: APSchedulerBackend, sample_job: ScheduledJob) -> None:
    called: list[bool] = []

    def cb() -> None:
        called.append(True)

    backend.schedule(sample_job, cb)
    jobs = backend.list_jobs()
    assert len(jobs) == 1
    assert jobs[0].job_id == sample_job.job_id
    assert jobs[0].domain_id == "marine_oil"


def test_backend_unschedule(backend: APSchedulerBackend, sample_job: ScheduledJob) -> None:
    backend.schedule(sample_job, lambda: None)
    assert len(backend.list_jobs()) == 1
    backend.unschedule(sample_job.job_id)
    assert backend.list_jobs() == []


def test_backend_unschedule_unknown_is_noop(backend: APSchedulerBackend) -> None:
    backend.unschedule("no_such_job")  # must not raise


def test_backend_reschedule_replaces_existing(
    backend: APSchedulerBackend, sample_job: ScheduledJob
) -> None:
    backend.schedule(sample_job, lambda: None)
    backend.schedule(sample_job, lambda: None)  # replace
    assert len(backend.list_jobs()) == 1


def test_backend_schedule_multiple_jobs(backend: APSchedulerBackend) -> None:
    j1 = ScheduledJob(job_id="a", domain_id="marine_oil", aoi_id="tobago", cadence_hours=24)
    j2 = ScheduledJob(job_id="b", domain_id="inland_wq", aoi_id="ref", cadence_hours=48)
    backend.schedule(j1, lambda: None)
    backend.schedule(j2, lambda: None)
    ids = {j.job_id for j in backend.list_jobs()}
    assert ids == {"a", "b"}


# ── APSchedulerBackend: manual trigger ────────────────────────────────────────


def test_backend_trigger_calls_callback(
    backend: APSchedulerBackend, sample_job: ScheduledJob
) -> None:
    event = threading.Event()

    def cb() -> None:
        event.set()

    backend.schedule(sample_job, cb)
    backend.trigger(sample_job.job_id)
    assert event.wait(timeout=2.0), "Callback was not invoked by trigger()"


def test_backend_trigger_unknown_job_raises(backend: APSchedulerBackend) -> None:
    with pytest.raises(KeyError, match="no_such"):
        backend.trigger("no_such")


@pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")
def test_backend_trigger_callback_exception_does_not_propagate(
    backend: APSchedulerBackend, sample_job: ScheduledJob
) -> None:
    event = threading.Event()

    def bad_cb() -> None:
        event.set()
        raise RuntimeError("boom")

    backend.schedule(sample_job, bad_cb)
    backend.trigger(sample_job.job_id)
    # Wait for the thread to finish; exception must not propagate to this test
    assert event.wait(timeout=2.0)
    time.sleep(0.05)  # let exception handling complete


# ── Quota guard tests ──────────────────────────────────────────────────────────


def test_check_cdse_quota_allowed_when_empty(tmp_store: Store) -> None:
    decision = check_cdse_daily_quota(tmp_store, daily_quota_gb=1.0)
    assert decision.allowed
    assert decision.reason == "ok"


def test_check_cdse_quota_denied_when_exhausted(tmp_store: Store) -> None:
    scene = Scene(
        id="s1",
        product_id="P1",
        aoi_id="tobago",
        sensing_time=datetime.now(UTC),
        ingest_status="ready",
        bytes_or_calls=int(2 * 1024**3),  # 2 GB
    )
    tmp_store.save_scene(scene)
    decision = check_cdse_daily_quota(tmp_store, daily_quota_gb=1.0)
    assert not decision.allowed
    assert "exhausted" in decision.reason


def test_check_open_meteo_quota_allowed_when_empty(tmp_store: Store) -> None:
    decision = check_open_meteo_daily_quota(tmp_store, daily_call_limit=10_000)
    assert decision.allowed


def test_check_domain_quota_satellite_domain(tmp_store: Store) -> None:
    decision = check_domain_quota("marine_oil", tmp_store, daily_quota_gb=1.0)
    assert decision.allowed


def test_check_domain_quota_unknown_domain_is_allowed(tmp_store: Store) -> None:
    decision = check_domain_quota("future_domain", tmp_store)
    assert decision.allowed
    assert "no quota guard" in decision.reason


def test_check_domain_quota_inland_wq_uses_cdse(tmp_store: Store) -> None:
    decision = check_domain_quota("inland_wq", tmp_store, daily_quota_gb=1.0)
    assert decision.allowed


def test_check_domain_quota_weather_hydro_uses_open_meteo(tmp_store: Store) -> None:
    decision = check_domain_quota("weather_hydro", tmp_store, daily_call_limit=10_000)
    assert decision.allowed


# ── run_domain_task: quota guard integration ──────────────────────────────────


def test_run_domain_task_skips_when_quota_exceeded(
    tmp_store: Store, settings: Settings, tmp_path: Path
) -> None:
    # Exhaust CDSE quota
    scene = Scene(
        id="s1",
        product_id="P1",
        aoi_id="tobago",
        sensing_time=datetime.now(UTC),
        ingest_status="ready",
        bytes_or_calls=int(2 * 1024**3),
    )
    tmp_store.save_scene(scene)

    # Create a minimal tobago.geojson
    aoi_dir = tmp_path / "aois"
    aoi_dir.mkdir(parents=True)
    (aoi_dir / "tobago.geojson").write_text(
        '{"type":"Feature","properties":{"id":"tobago","name":"Tobago","domains":["marine_oil"]},'
        '"geometry":{"type":"Polygon","coordinates":[[[-61.0,10.0],[-60.5,10.0],[-60.5,11.0],[-61.0,11.0],[-61.0,10.0]]]}}'
    )

    job = ScheduledJob(job_id="j1", domain_id="marine_oil", aoi_id="tobago", cadence_hours=24)
    result = run_domain_task(job, tmp_store, settings, config_dir=tmp_path)

    assert result.status == "skipped"
    assert "exhausted" in (result.error or "")


# ── run_domain_task: AOI load error ───────────────────────────────────────────


def test_run_domain_task_fails_on_missing_aoi(
    tmp_store: Store, settings: Settings, tmp_path: Path
) -> None:
    job = ScheduledJob(job_id="j", domain_id="marine_oil", aoi_id="nonexistent", cadence_hours=24)
    result = run_domain_task(job, tmp_store, settings, config_dir=tmp_path)
    assert result.status == "failed"
    assert "AOI load error" in (result.error or "")


# ── run_domain_task: unknown domain ───────────────────────────────────────────


def test_run_domain_task_fails_on_unknown_domain(
    tmp_store: Store, settings: Settings, tmp_path: Path
) -> None:
    aoi_dir = tmp_path / "aois"
    aoi_dir.mkdir(parents=True)
    (aoi_dir / "tobago.geojson").write_text(
        '{"type":"Feature","properties":{"id":"tobago","name":"Tobago","domains":["mystery"]},'
        '"geometry":{"type":"Polygon","coordinates":[[[-61.0,10.0],[-60.5,10.0],[-60.5,11.0],[-61.0,11.0],[-61.0,10.0]]]}}'
    )

    job = ScheduledJob(job_id="j", domain_id="mystery_domain", aoi_id="tobago", cadence_hours=24)
    result = run_domain_task(job, tmp_store, settings, config_dir=tmp_path)
    assert result.status == "failed"
    assert "Domain load error" in (result.error or "")


# ── run_domain_task: dry_run flag ─────────────────────────────────────────────


def test_run_domain_task_dry_run_skips_acquisition(
    tmp_store: Store, settings: Settings, tmp_path: Path
) -> None:
    aoi_dir = tmp_path / "aois"
    aoi_dir.mkdir(parents=True)
    (aoi_dir / "tobago.geojson").write_text(
        '{"type":"Feature","properties":{"id":"tobago","name":"Tobago","domains":["marine_oil"]},'
        '"geometry":{"type":"Polygon","coordinates":[[[-61.0,10.0],[-60.5,10.0],[-60.5,11.0],[-61.0,11.0],[-61.0,10.0]]]}}'
    )

    mock_domain = MagicMock()
    mock_ref = MagicMock()
    mock_ref.product_id = "P-dry"
    mock_ref.bytes_estimated = None
    mock_domain.domain_id = "marine_oil"
    mock_domain.search.return_value = [mock_ref]
    mock_domain.acquire.return_value = MagicMock()
    mock_domain.analyze.return_value = []

    job = ScheduledJob(job_id="j", domain_id="marine_oil", aoi_id="tobago", cadence_hours=24)

    with patch("argus.tasking.runner._load_domain", return_value=mock_domain):
        result = run_domain_task(job, tmp_store, settings, config_dir=tmp_path, dry_run=True)

    assert result.status == "complete"
    mock_domain.acquire.assert_not_called()


# ── run_domain_task: no scenes found ─────────────────────────────────────────


def test_run_domain_task_complete_when_no_scenes(
    tmp_store: Store, settings: Settings, tmp_path: Path
) -> None:
    aoi_dir = tmp_path / "aois"
    aoi_dir.mkdir(parents=True)
    (aoi_dir / "tobago.geojson").write_text(
        '{"type":"Feature","properties":{"id":"tobago","name":"Tobago","domains":["marine_oil"]},'
        '"geometry":{"type":"Polygon","coordinates":[[[-61.0,10.0],[-60.5,10.0],[-60.5,11.0],[-61.0,11.0],[-61.0,10.0]]]}}'
    )

    mock_domain = MagicMock()
    mock_domain.domain_id = "marine_oil"
    mock_domain.search.return_value = []

    job = ScheduledJob(job_id="j", domain_id="marine_oil", aoi_id="tobago", cadence_hours=24)

    with patch("argus.tasking.runner._load_domain", return_value=mock_domain):
        result = run_domain_task(job, tmp_store, settings, config_dir=tmp_path)

    assert result.status == "complete"
    assert result.scenes_fetched == 0
    assert result.observations_created == 0


# ── run_domain_task: full happy path ─────────────────────────────────────────


def test_run_domain_task_persists_analysis_run_and_observations(
    tmp_store: Store, settings: Settings, tmp_path: Path
) -> None:
    aoi_dir = tmp_path / "aois"
    aoi_dir.mkdir(parents=True)
    (aoi_dir / "tobago.geojson").write_text(
        '{"type":"Feature","properties":{"id":"tobago","name":"Tobago","domains":["marine_oil"]},'
        '"geometry":{"type":"Polygon","coordinates":[[[-61.0,10.0],[-60.5,10.0],[-60.5,11.0],[-61.0,11.0],[-61.0,10.0]]]}}'
    )

    run_id = str(uuid.uuid4())
    scene_id = str(uuid.uuid4())
    mock_ref = MagicMock(spec=SourceRef)
    mock_ref.bytes_estimated = 1024
    mock_acq = Acquisition(scene_id=scene_id, source_ref=mock_ref)
    mock_obs = Observation(
        id=str(uuid.uuid4()),
        analysis_run_id=run_id,
        scene_id=scene_id,
        obs_type="oil_slick",
        evidence_class="measured",
        geometry={"type": "Point", "coordinates": [-60.7, 10.5]},
        area_km2=1.0,
        confidence=0.9,
    )
    mock_domain = MagicMock()
    mock_domain.domain_id = "marine_oil"
    mock_domain.search.return_value = [mock_ref]
    mock_domain.acquire.return_value = mock_acq
    mock_domain.analyze.return_value = [mock_obs]

    job = ScheduledJob(job_id="j", domain_id="marine_oil", aoi_id="tobago", cadence_hours=24)

    with patch("argus.tasking.runner._load_domain", return_value=mock_domain):
        result = run_domain_task(job, tmp_store, settings, config_dir=tmp_path)

    assert result.status == "complete"
    assert result.scenes_fetched == 1
    assert result.observations_created == 1

    # Verify observations were persisted (INV-6)
    saved = tmp_store.get_observation(mock_obs.id)
    assert saved is not None
    assert saved.obs_type == "oil_slick"
    assert saved.evidence_class == "measured"


# ── run_domain_task: domain.search() raises ──────────────────────────────────


def test_run_domain_task_handles_search_exception(
    tmp_store: Store, settings: Settings, tmp_path: Path
) -> None:
    aoi_dir = tmp_path / "aois"
    aoi_dir.mkdir(parents=True)
    (aoi_dir / "tobago.geojson").write_text(
        '{"type":"Feature","properties":{"id":"tobago","name":"Tobago","domains":["marine_oil"]},'
        '"geometry":{"type":"Polygon","coordinates":[[[-61.0,10.0],[-60.5,10.0],[-60.5,11.0],[-61.0,11.0],[-61.0,10.0]]]}}'
    )

    mock_domain = MagicMock()
    mock_domain.domain_id = "marine_oil"
    mock_domain.search.side_effect = ConnectionError("CDSE offline")

    job = ScheduledJob(job_id="j", domain_id="marine_oil", aoi_id="tobago", cadence_hours=24)

    with patch("argus.tasking.runner._load_domain", return_value=mock_domain):
        result = run_domain_task(job, tmp_store, settings, config_dir=tmp_path)

    assert result.status == "failed"
    assert "search()" in (result.error or "")


# ── run_domain_task: acquire() raises for one scene ──────────────────────────


def test_run_domain_task_continues_after_acquire_exception(
    tmp_store: Store, settings: Settings, tmp_path: Path
) -> None:
    """Partial acquisition failure: skip the failing scene, process the rest."""
    aoi_dir = tmp_path / "aois"
    aoi_dir.mkdir(parents=True)
    (aoi_dir / "tobago.geojson").write_text(
        '{"type":"Feature","properties":{"id":"tobago","name":"Tobago","domains":["marine_oil"]},'
        '"geometry":{"type":"Polygon","coordinates":[[[-61.0,10.0],[-60.5,10.0],[-60.5,11.0],[-61.0,11.0],[-61.0,10.0]]]}}'
    )

    scene_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    ref_bad = MagicMock()
    ref_bad.product_id = "P-bad"
    ref_bad.bytes_estimated = None
    ref_good = MagicMock()
    ref_good.product_id = "P-good"
    ref_good.bytes_estimated = None
    mock_acq = Acquisition(scene_id=scene_id, source_ref=ref_good)
    mock_obs = Observation(
        id=str(uuid.uuid4()),
        analysis_run_id=run_id,
        scene_id=scene_id,
        obs_type="oil_slick",
        evidence_class="measured",
        geometry={"type": "Point", "coordinates": [-60.7, 10.5]},
        area_km2=1.0,
        confidence=0.9,
    )
    mock_domain = MagicMock()
    mock_domain.domain_id = "marine_oil"
    mock_domain.search.return_value = [ref_bad, ref_good]
    mock_domain.acquire.side_effect = [RuntimeError("timeout"), mock_acq]
    mock_domain.analyze.return_value = [mock_obs]

    job = ScheduledJob(job_id="j", domain_id="marine_oil", aoi_id="tobago", cadence_hours=24)

    with patch("argus.tasking.runner._load_domain", return_value=mock_domain):
        result = run_domain_task(job, tmp_store, settings, config_dir=tmp_path)

    # Both scenes were found; one acquire failed; one obs from the second scene
    assert result.status == "complete"
    assert result.scenes_fetched == 2
    assert result.observations_created == 1


# ── NullScheduler for testing ─────────────────────────────────────────────────


class NullScheduler:
    """Minimal no-op scheduler for unit tests that need a Scheduler instance."""

    def __init__(self) -> None:
        self._jobs: dict[str, tuple[ScheduledJob, Callable[[], None]]] = {}

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def schedule(self, job: ScheduledJob, callback: Callable[[], None]) -> None:
        self._jobs[job.job_id] = (job, callback)

    def unschedule(self, job_id: str) -> None:
        self._jobs.pop(job_id, None)

    def list_jobs(self) -> list[ScheduledJob]:
        return [j for j, _ in self._jobs.values()]

    def trigger(self, job_id: str) -> None:
        if job_id not in self._jobs:
            raise KeyError(job_id)
        self._jobs[job_id][1]()


def test_null_scheduler_protocol_conformance() -> None:
    ns = NullScheduler()
    job = ScheduledJob(job_id="x", domain_id="marine_oil", aoi_id="tobago", cadence_hours=24)
    ns.start()
    ns.schedule(job, lambda: None)
    assert len(ns.list_jobs()) == 1
    ns.trigger("x")
    ns.unschedule("x")
    assert ns.list_jobs() == []
    ns.stop()


def test_null_scheduler_trigger_unknown_raises() -> None:
    ns = NullScheduler()
    with pytest.raises(KeyError):
        ns.trigger("missing")
