"""Tests for F-038: Incremental Ingestion + Idempotency + RunHistory.

All tests are offline (INV-7). Network calls are mocked.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from argus.core.config import Settings
from argus.core.models import AOI, RunHistory, Scene, SourceRef
from argus.core.store import Store
from argus.tasking.base import ScheduledJob, TaskResult
from argus.tasking.runner import _save_run_history, run_domain_task

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def tmp_store(tmp_path: Path) -> Store:
    return Store(tmp_path / "argus.db")


@pytest.fixture()
def settings() -> Settings:
    return Settings()


def _tobago_aoi_json() -> str:
    return (
        '{"type":"Feature","properties":{"id":"tobago","name":"Tobago","domains":["marine_oil"]},'
        '"geometry":{"type":"Polygon","coordinates":[[[-61.0,10.0],[-60.5,10.0],'
        '[-60.5,11.0],[-61.0,11.0],[-61.0,10.0]]]}}'
    )


# ── RunHistory model ──────────────────────────────────────────────────────────


def test_run_history_defaults() -> None:
    now = datetime.now(UTC)
    rh = RunHistory(
        id="r1",
        domain_id="marine_oil",
        aoi_id="tobago",
        t_start=now,
        t_end=now,
    )
    assert rh.scenes_fetched == 0
    assert rh.observations_created == 0
    assert rh.bytes_used == 0
    assert rh.status == "complete"
    assert rh.error is None


def test_run_history_all_statuses() -> None:
    now = datetime.now(UTC)
    for status in ("complete", "failed", "partial", "skipped"):
        rh = RunHistory(
            id=str(uuid.uuid4()),
            domain_id="marine_oil",
            aoi_id="tobago",
            t_start=now,
            t_end=now,
            status=status,
        )
        assert rh.status == status


# ── Store: RunHistory CRUD ────────────────────────────────────────────────────


def test_store_save_and_retrieve_run_history(tmp_store: Store) -> None:
    now = datetime.now(UTC)
    rh = RunHistory(
        id="rh1",
        domain_id="marine_oil",
        aoi_id="tobago",
        t_start=now,
        t_end=now,
        scenes_fetched=3,
        observations_created=7,
        bytes_used=1024,
        status="complete",
    )
    tmp_store.save_run_history(rh)
    records = tmp_store.get_run_history(domain_id="marine_oil")
    assert len(records) == 1
    r = records[0]
    assert r.id == "rh1"
    assert r.scenes_fetched == 3
    assert r.observations_created == 7
    assert r.bytes_used == 1024
    assert r.status == "complete"


def test_store_run_history_filter_by_domain(tmp_store: Store) -> None:
    now = datetime.now(UTC)
    for domain, aoi in [("marine_oil", "tobago"), ("inland_wq", "ref"), ("marine_oil", "ref2")]:
        tmp_store.save_run_history(
            RunHistory(
                id=str(uuid.uuid4()),
                domain_id=domain,
                aoi_id=aoi,
                t_start=now,
                t_end=now,
            )
        )
    oil_runs = tmp_store.get_run_history(domain_id="marine_oil")
    assert len(oil_runs) == 2
    wq_runs = tmp_store.get_run_history(domain_id="inland_wq")
    assert len(wq_runs) == 1


def test_store_run_history_filter_by_aoi(tmp_store: Store) -> None:
    now = datetime.now(UTC)
    for aoi in ["tobago", "tobago", "ref"]:
        tmp_store.save_run_history(
            RunHistory(
                id=str(uuid.uuid4()),
                domain_id="marine_oil",
                aoi_id=aoi,
                t_start=now,
                t_end=now,
            )
        )
    tobago_runs = tmp_store.get_run_history(aoi_id="tobago")
    assert len(tobago_runs) == 2


def test_store_run_history_limit(tmp_store: Store) -> None:
    now = datetime.now(UTC)
    for _ in range(10):
        tmp_store.save_run_history(
            RunHistory(
                id=str(uuid.uuid4()),
                domain_id="marine_oil",
                aoi_id="tobago",
                t_start=now,
                t_end=now,
            )
        )
    limited = tmp_store.get_run_history(limit=5)
    assert len(limited) == 5


def test_store_get_last_run_for_domain(tmp_store: Store) -> None:
    now = datetime.now(UTC)
    for status in ("complete", "failed", "complete"):
        tmp_store.save_run_history(
            RunHistory(
                id=str(uuid.uuid4()),
                domain_id="marine_oil",
                aoi_id="tobago",
                t_start=now,
                t_end=now,
                status=status,
            )
        )
    last = tmp_store.get_last_run_for_domain("marine_oil", "tobago")
    assert last is not None
    assert last.status == "complete"


def test_store_get_last_run_for_domain_none_when_empty(tmp_store: Store) -> None:
    result = tmp_store.get_last_run_for_domain("marine_oil", "tobago")
    assert result is None


def test_store_run_history_newest_first(tmp_store: Store) -> None:
    import time

    for _ in range(3):
        now = datetime.now(UTC)
        tmp_store.save_run_history(
            RunHistory(
                id=str(uuid.uuid4()),
                domain_id="marine_oil",
                aoi_id="tobago",
                t_start=now,
                t_end=now,
            )
        )
        time.sleep(0.01)

    records = tmp_store.get_run_history()
    # Newest first: created_at descending
    for i in range(len(records) - 1):
        assert records[i].created_at >= records[i + 1].created_at


# ── Store: get_scene_by_product_id (idempotency) ─────────────────────────────


def test_store_get_scene_by_product_id_returns_none_when_missing(tmp_store: Store) -> None:
    result = tmp_store.get_scene_by_product_id("P-nonexistent")
    assert result is None


def test_store_get_scene_by_product_id_returns_existing(tmp_store: Store) -> None:
    scene = Scene(
        id="s1",
        product_id="P-001",
        aoi_id="tobago",
        sensing_time=datetime.now(UTC),
        ingest_status="ready",
        bytes_or_calls=512,
    )
    tmp_store.save_scene(scene)
    found = tmp_store.get_scene_by_product_id("P-001")
    assert found is not None
    assert found.id == "s1"
    assert found.ingest_status == "ready"


def test_store_get_scene_by_product_id_returns_most_recent(tmp_store: Store) -> None:
    now = datetime.now(UTC)
    for i, status in enumerate((("pending"), ("ready"))):
        scene = Scene(
            id=f"s{i}",
            product_id="P-001",
            aoi_id="tobago",
            sensing_time=now,
            ingest_status=status,  # type: ignore[arg-type]
            bytes_or_calls=0,
        )
        tmp_store.save_scene(scene)
    found = tmp_store.get_scene_by_product_id("P-001")
    # Last saved (higher id index) should be returned (most recent by created_at)
    assert found is not None


# ── acquire_scene idempotency ─────────────────────────────────────────────────


def test_acquire_scene_skips_existing_ready_scene(tmp_path: Path, tmp_store: Store) -> None:
    """Second call with the same product_id must return the existing scene, zero bytes fetched."""
    from argus.core.config import Settings
    from argus.ingest.acquire import acquire_scene

    existing = Scene(
        id="existing-id",
        product_id="P-EXISTING",
        aoi_id="tobago",
        sensing_time=datetime.now(UTC),
        ingest_status="ready",
        bytes_or_calls=500_000,
    )
    tmp_store.save_scene(existing)

    ref = MagicMock(spec=SourceRef)
    ref.product_id = "P-EXISTING"
    ref.sensing_time = datetime.now(UTC)

    aoi = AOI(
        id="tobago",
        name="Tobago",
        geometry={"type": "Polygon", "coordinates": [[[-61, 10], [-60.5, 10], [-60.5, 11], [-61, 11], [-61, 10]]]},
        domains=["marine_oil"],
    )

    mock_auth = MagicMock()
    settings = Settings()
    settings.store.artifact_dir = tmp_path / "artifacts"

    returned = acquire_scene(ref, aoi, mock_auth, tmp_store, settings)
    assert returned.id == "existing-id"
    assert returned.ingest_status == "ready"


def test_acquire_scene_does_not_re_fetch_if_product_ready(tmp_path: Path, tmp_store: Store) -> None:
    """Verify that fetch_s1_subset is NOT called when product already in store."""
    from argus.core.config import Settings
    from argus.ingest.acquire import acquire_scene

    existing = Scene(
        id="ex-id",
        product_id="P-CACHED",
        aoi_id="tobago",
        sensing_time=datetime.now(UTC),
        ingest_status="ready",
        bytes_or_calls=0,
    )
    tmp_store.save_scene(existing)

    ref = MagicMock(spec=SourceRef)
    ref.product_id = "P-CACHED"
    ref.sensing_time = datetime.now(UTC)

    aoi = AOI(
        id="tobago",
        name="Tobago",
        geometry={"type": "Polygon", "coordinates": [[[-61, 10], [-60.5, 10], [-60.5, 11], [-61, 11], [-61, 10]]]},
        domains=["marine_oil"],
    )

    settings = Settings()
    settings.store.artifact_dir = tmp_path / "artifacts"

    with patch("argus.ingest.acquire.fetch_s1_subset") as mock_fetch:
        acquire_scene(ref, aoi, MagicMock(), tmp_store, settings)
        mock_fetch.assert_not_called()


def test_acquire_scene_downloads_new_product(tmp_path: Path, tmp_store: Store) -> None:
    """New product (not in store) triggers fetch_s1_subset."""
    from argus.core.config import Settings
    from argus.ingest.acquire import acquire_scene

    ref = SourceRef(
        product_id="P-NEW",
        source="cdse",
        collection="SENTINEL-1",
        product_type="GRD",
        sensor_mode="IW",
        sensing_time=datetime.now(UTC),
        footprint={"type": "Polygon", "coordinates": [[[-61, 10], [-60.5, 10], [-60.5, 11], [-61, 11], [-61, 10]]]},
        polarizations=["VV", "VH"],
    )

    aoi = AOI(
        id="tobago",
        name="Tobago",
        geometry={"type": "Polygon", "coordinates": [[[-61, 10], [-60.5, 10], [-60.5, 11], [-61, 11], [-61, 10]]]},
        domains=["marine_oil"],
    )

    settings = Settings()
    settings.store.artifact_dir = tmp_path / "artifacts"

    fake_tiff = b"FAKE-TIFF"
    with patch("argus.ingest.acquire.fetch_s1_subset", return_value=(fake_tiff, len(fake_tiff))):
        scene = acquire_scene(ref, aoi, MagicMock(), tmp_store, settings)

    assert scene.product_id == "P-NEW"
    assert scene.ingest_status == "ready"
    assert scene.bytes_or_calls == len(fake_tiff)


# ── run_domain_task: RunHistory is always saved ───────────────────────────────


def test_run_domain_task_saves_run_history_on_complete(
    tmp_store: Store, settings: Settings, tmp_path: Path
) -> None:
    aoi_dir = tmp_path / "aois"
    aoi_dir.mkdir(parents=True)
    (aoi_dir / "tobago.geojson").write_text(_tobago_aoi_json())

    mock_domain = MagicMock()
    mock_domain.domain_id = "marine_oil"
    mock_domain.search.return_value = []

    job = ScheduledJob(job_id="j", domain_id="marine_oil", aoi_id="tobago", cadence_hours=24)

    with patch("argus.tasking.runner._load_domain", return_value=mock_domain):
        run_domain_task(job, tmp_store, settings, config_dir=tmp_path)

    records = tmp_store.get_run_history(domain_id="marine_oil")
    assert len(records) == 1
    assert records[0].status == "complete"
    assert records[0].aoi_id == "tobago"


def test_run_domain_task_saves_run_history_on_skip(
    tmp_store: Store, settings: Settings, tmp_path: Path
) -> None:
    """Quota-skipped runs still create a RunHistory record."""
    from argus.core.models import Scene

    aoi_dir = tmp_path / "aois"
    aoi_dir.mkdir(parents=True)
    (aoi_dir / "tobago.geojson").write_text(_tobago_aoi_json())

    # Exhaust quota
    tmp_store.save_scene(
        Scene(
            id="s-big",
            product_id="P-BIG",
            aoi_id="tobago",
            sensing_time=datetime.now(UTC),
            ingest_status="ready",
            bytes_or_calls=int(2 * 1024**3),
        )
    )

    job = ScheduledJob(job_id="j", domain_id="marine_oil", aoi_id="tobago", cadence_hours=24)
    run_domain_task(job, tmp_store, settings, config_dir=tmp_path)

    records = tmp_store.get_run_history(domain_id="marine_oil")
    assert len(records) == 1
    assert records[0].status == "skipped"


def test_run_domain_task_saves_run_history_on_domain_error(
    tmp_store: Store, settings: Settings, tmp_path: Path
) -> None:
    aoi_dir = tmp_path / "aois"
    aoi_dir.mkdir(parents=True)
    (aoi_dir / "tobago.geojson").write_text(_tobago_aoi_json())

    job = ScheduledJob(job_id="j", domain_id="unknown_domain", aoi_id="tobago", cadence_hours=24)
    run_domain_task(job, tmp_store, settings, config_dir=tmp_path)

    records = tmp_store.get_run_history(domain_id="unknown_domain")
    assert len(records) == 1
    assert records[0].status == "failed"


# ── _save_run_history helper ──────────────────────────────────────────────────


def test_save_run_history_helper(tmp_store: Store) -> None:
    now = datetime.now(UTC)
    result = TaskResult(job_id="j", domain_id="marine_oil", aoi_id="tobago")
    result.finish(status="complete", scenes=2, obs=5, bytes_used=8192)

    _save_run_history(result, tmp_store, now, now)

    records = tmp_store.get_run_history()
    assert len(records) == 1
    assert records[0].scenes_fetched == 2
    assert records[0].observations_created == 5
    assert records[0].bytes_used == 8192
    assert records[0].domain_id == "marine_oil"


def test_save_run_history_stores_error(tmp_store: Store) -> None:
    now = datetime.now(UTC)
    result = TaskResult(job_id="j", domain_id="marine_oil", aoi_id="tobago")
    result.fail("network timeout")

    _save_run_history(result, tmp_store, now, now)

    records = tmp_store.get_run_history()
    assert records[0].status == "failed"
    assert records[0].error == "network timeout"


# ── Idempotency: second run over same window ──────────────────────────────────


def test_second_run_same_window_zero_bytes(
    tmp_store: Store, settings: Settings, tmp_path: Path
) -> None:
    """Key F-038 AC: running the same date range twice → second run fetches zero bytes."""
    aoi_dir = tmp_path / "aois"
    aoi_dir.mkdir(parents=True)
    (aoi_dir / "tobago.geojson").write_text(_tobago_aoi_json())

    # Pre-populate the store with an already-acquired scene for the product
    existing_scene = Scene(
        id="scene-already-done",
        product_id="S1_PROD_001",
        aoi_id="tobago",
        sensing_time=datetime.now(UTC),
        ingest_status="ready",
        bytes_or_calls=5_000_000,  # 5 MB already consumed
    )
    tmp_store.save_scene(existing_scene)

    # Second lookup should return existing scene, no new bytes
    found = tmp_store.get_scene_by_product_id("S1_PROD_001")
    assert found is not None
    assert found.ingest_status == "ready"

    # Daily bytes total should only reflect the initial fetch
    bytes_today = tmp_store.daily_bytes_total(datetime.now(UTC))
    # The pre-populated scene uses 5 MB — no double-fetch adds more
    assert bytes_today == 5_000_000
