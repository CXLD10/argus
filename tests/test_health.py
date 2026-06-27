"""F-023 tests: health checks and readiness probes."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from argus.api.app import create_app
from argus.core.models import AnalysisRun
from argus.core.store import Store


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "argus.db"
    app = create_app(db_path=db_path, config_dir=tmp_path / "config")
    return TestClient(app)


@pytest.fixture()
def seeded_client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "argus.db"
    store = Store(db_path)
    run = AnalysisRun(
        id="run-001",
        aoi_id="tobago",
        domain_id="marine_oil",
        scene_id="scene-001",
        started_at=datetime(2024, 2, 7, 12, 0, tzinfo=UTC),
        status="complete",
        n_observations=2,
    )
    store.save_analysis_run(run)
    app = create_app(db_path=db_path, config_dir=tmp_path / "config")
    return TestClient(app)


# ── /health ───────────────────────────────────────────────────────────────────


def test_health_returns_200(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200


def test_health_body_has_status_ok(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.json()["status"] == "ok"


def test_health_body_has_version(client: TestClient) -> None:
    from argus import __version__

    resp = client.get("/health")
    assert resp.json()["version"] == __version__


# ── /ready ────────────────────────────────────────────────────────────────────


def test_ready_returns_200_when_accessible(client: TestClient) -> None:
    resp = client.get("/ready")
    assert resp.status_code == 200


def test_ready_body_status_is_ready(client: TestClient) -> None:
    resp = client.get("/ready")
    assert resp.json()["status"] == "ready"


def test_ready_returns_503_when_db_inaccessible(tmp_path: Path) -> None:
    # Block DB creation by placing a file where the parent dir would be
    blocker = tmp_path / "blocked"
    blocker.write_text("I am a file, not a directory")
    db_path = blocker / "argus.db"
    app = create_app(db_path=db_path, config_dir=tmp_path / "config")
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/ready")
    assert resp.status_code == 503


def test_ready_503_has_detail(tmp_path: Path) -> None:
    blocker = tmp_path / "blocked"
    blocker.write_text("I am a file, not a directory")
    db_path = blocker / "argus.db"
    app = create_app(db_path=db_path, config_dir=tmp_path / "config")
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/ready")
    body = resp.json()
    assert "detail" in body


# ── /status ───────────────────────────────────────────────────────────────────


def test_status_returns_200(client: TestClient) -> None:
    resp = client.get("/status")
    assert resp.status_code == 200


def test_status_has_version(client: TestClient) -> None:
    from argus import __version__

    resp = client.get("/status")
    assert resp.json()["version"] == __version__


def test_status_store_accessible_true(client: TestClient) -> None:
    resp = client.get("/status")
    assert resp.json()["store_accessible"] is True


def test_status_last_run_null_when_no_runs(client: TestClient) -> None:
    resp = client.get("/status")
    assert resp.json()["last_analysis_run_at"] is None


def test_status_last_run_populated_after_run(seeded_client: TestClient) -> None:
    resp = seeded_client.get("/status")
    data = resp.json()
    assert data["last_analysis_run_at"] is not None
    assert "2024" in data["last_analysis_run_at"]


def test_status_quota_has_cdse_fields(client: TestClient) -> None:
    resp = client.get("/status")
    quota = resp.json()["quota"]
    assert "cdse_bytes_today" in quota
    assert "cdse_daily_limit_gb" in quota
    assert "cdse_remaining_bytes" in quota


def test_status_quota_bytes_today_is_zero_with_no_scenes(client: TestClient) -> None:
    resp = client.get("/status")
    assert resp.json()["quota"]["cdse_bytes_today"] == 0


def test_status_quota_remaining_equals_limit_when_no_usage(client: TestClient) -> None:
    resp = client.get("/status")
    quota = resp.json()["quota"]
    limit_bytes = int(quota["cdse_daily_limit_gb"] * 1024**3)
    assert quota["cdse_remaining_bytes"] == limit_bytes


# ── Store.ping() ──────────────────────────────────────────────────────────────


def test_store_ping_returns_true(tmp_path: Path) -> None:
    store = Store(tmp_path / "argus.db")
    assert store.ping() is True


# ── Store.get_last_analysis_run_at() ──────────────────────────────────────────


def test_get_last_analysis_run_at_none_when_empty(tmp_path: Path) -> None:
    store = Store(tmp_path / "argus.db")
    assert store.get_last_analysis_run_at() is None


def test_get_last_analysis_run_at_returns_datetime(tmp_path: Path) -> None:
    store = Store(tmp_path / "argus.db")
    run = AnalysisRun(
        id="run-001",
        aoi_id="tobago",
        domain_id="marine_oil",
        scene_id="scene-001",
        started_at=datetime(2024, 2, 7, 6, 0, tzinfo=UTC),
        status="complete",
        n_observations=0,
    )
    store.save_analysis_run(run)
    last = store.get_last_analysis_run_at()
    assert last is not None
    assert last.year == 2024
