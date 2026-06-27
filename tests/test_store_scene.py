"""F-003 tests: SQLite store — Scene CRUD and quota helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from argus.core.models import Scene
from argus.core.store import Store


def _make_scene(**overrides: object) -> Scene:
    defaults: dict[str, object] = {
        "id": "scene-001",
        "product_id": "S1A_IW_GRDH_1SDV_20240207T215408.SAFE",
        "aoi_id": "tobago",
        "sensing_time": datetime(2024, 2, 7, 21, 54, 8, tzinfo=UTC),
        "ingest_status": "ready",
        "artifact_path": "/tmp/scene-001.tif",
        "bytes_or_calls": 52_428_800,
    }
    defaults.update(overrides)
    return Scene(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "argus.db")


def test_store_creates_db_file(tmp_path: Path) -> None:
    db = tmp_path / "sub" / "argus.db"
    Store(db)
    assert db.exists()


def test_save_and_get_scene(store: Store) -> None:
    scene = _make_scene()
    store.save_scene(scene)
    retrieved = store.get_scene(scene.id)
    assert retrieved is not None
    assert retrieved.id == scene.id


def test_get_nonexistent_scene_returns_none(store: Store) -> None:
    assert store.get_scene("no-such-id") is None


def test_round_trip_preserves_product_id(store: Store) -> None:
    scene = _make_scene()
    store.save_scene(scene)
    retrieved = store.get_scene(scene.id)
    assert retrieved is not None
    assert retrieved.product_id == scene.product_id


def test_round_trip_preserves_aoi_id(store: Store) -> None:
    scene = _make_scene()
    store.save_scene(scene)
    retrieved = store.get_scene(scene.id)
    assert retrieved is not None
    assert retrieved.aoi_id == scene.aoi_id


def test_round_trip_preserves_sensing_time(store: Store) -> None:
    scene = _make_scene()
    store.save_scene(scene)
    retrieved = store.get_scene(scene.id)
    assert retrieved is not None
    assert retrieved.sensing_time == scene.sensing_time


def test_round_trip_preserves_ingest_status(store: Store) -> None:
    scene = _make_scene(ingest_status="ready")
    store.save_scene(scene)
    retrieved = store.get_scene(scene.id)
    assert retrieved is not None
    assert retrieved.ingest_status == "ready"


def test_round_trip_preserves_bytes_or_calls(store: Store) -> None:
    scene = _make_scene(bytes_or_calls=12_345_678)
    store.save_scene(scene)
    retrieved = store.get_scene(scene.id)
    assert retrieved is not None
    assert retrieved.bytes_or_calls == 12_345_678


def test_round_trip_preserves_artifact_path(store: Store) -> None:
    scene = _make_scene(artifact_path="/data/artifacts/abc.tif")
    store.save_scene(scene)
    retrieved = store.get_scene(scene.id)
    assert retrieved is not None
    assert retrieved.artifact_path == "/data/artifacts/abc.tif"


def test_round_trip_null_artifact_path(store: Store) -> None:
    scene = _make_scene(artifact_path=None, ingest_status="pending")
    store.save_scene(scene)
    retrieved = store.get_scene(scene.id)
    assert retrieved is not None
    assert retrieved.artifact_path is None


def test_round_trip_attrs(store: Store) -> None:
    scene = _make_scene(attrs={"orbit_state": "ascending", "pass_number": 42})
    store.save_scene(scene)
    retrieved = store.get_scene(scene.id)
    assert retrieved is not None
    assert retrieved.attrs["orbit_state"] == "ascending"
    assert retrieved.attrs["pass_number"] == 42


def test_save_replaces_existing(store: Store) -> None:
    scene = _make_scene(ingest_status="pending")
    store.save_scene(scene)
    updated = scene.model_copy(update={"ingest_status": "ready", "bytes_or_calls": 1024})
    store.save_scene(updated)
    retrieved = store.get_scene(scene.id)
    assert retrieved is not None
    assert retrieved.ingest_status == "ready"
    assert retrieved.bytes_or_calls == 1024


def test_daily_bytes_total_sums_same_day(store: Store) -> None:
    day = datetime(2024, 2, 7, 12, 0, 0, tzinfo=UTC)
    store.save_scene(_make_scene(id="s1", bytes_or_calls=1000, created_at=day))
    store.save_scene(_make_scene(id="s2", bytes_or_calls=2000, created_at=day))
    assert store.daily_bytes_total(day) == 3000


def test_daily_bytes_total_excludes_different_day(store: Store) -> None:
    day1 = datetime(2024, 2, 7, 12, 0, 0, tzinfo=UTC)
    day2 = datetime(2024, 2, 8, 12, 0, 0, tzinfo=UTC)
    store.save_scene(_make_scene(id="s1", bytes_or_calls=1000, created_at=day1))
    store.save_scene(_make_scene(id="s2", bytes_or_calls=2000, created_at=day2))
    assert store.daily_bytes_total(day1) == 1000
    assert store.daily_bytes_total(day2) == 2000


def test_daily_bytes_total_zero_when_empty(store: Store) -> None:
    assert store.daily_bytes_total(datetime.now(UTC)) == 0
