"""Tests for F-039: Observability — GET /status with RunHistory metrics.

All tests are offline (INV-7).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from argus.api.app import create_app
from argus.api.schemas import QuotaStatus, RunSummary, StatusResponse
from argus.core.models import RunHistory
from argus.core.store import Store


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "argus.db"


@pytest.fixture()
def store(db_path: Path) -> Store:
    return Store(db_path)


@pytest.fixture()
def client(tmp_path: Path, db_path: Path) -> TestClient:
    config_dir = tmp_path / "config"
    (config_dir / "aois").mkdir(parents=True)
    repo_root = Path(__file__).parent.parent
    (config_dir / "aois" / "tobago.geojson").write_bytes(
        (repo_root / "config" / "aois" / "tobago.geojson").read_bytes()
    )
    return TestClient(create_app(db_path=db_path, config_dir=config_dir))


# ── StatusResponse schema ──────────────────────────────────────────────────────


def test_status_response_includes_domain_runs_field() -> None:
    r = StatusResponse(
        store_accessible=True,
        quota=QuotaStatus(cdse_bytes_today=0, cdse_daily_limit_gb=1.0, cdse_remaining_bytes=0),
    )
    assert isinstance(r.domain_runs, list)
    assert r.open_meteo_calls_today == 0


def test_run_summary_schema() -> None:
    rs = RunSummary(domain_id="marine_oil", aoi_id="tobago")
    assert rs.scenes_fetched == 0
    assert rs.observations_created == 0
    assert rs.last_run_at is None
    assert rs.last_run_status is None


def test_run_summary_with_data() -> None:
    now = datetime.now(UTC)
    rs = RunSummary(
        domain_id="marine_oil",
        aoi_id="tobago",
        last_run_at=now,
        last_run_status="complete",
        scenes_fetched=3,
        observations_created=7,
        bytes_used=1024,
    )
    assert rs.last_run_status == "complete"
    assert rs.scenes_fetched == 3


# ── GET /status endpoint ───────────────────────────────────────────────────────


def test_status_endpoint_returns_200(client: TestClient) -> None:
    resp = client.get("/status")
    assert resp.status_code == 200


def test_status_response_validates_schema(client: TestClient) -> None:
    resp = client.get("/status")
    assert resp.status_code == 200
    data = resp.json()
    # Must not raise
    parsed = StatusResponse.model_validate(data)
    assert parsed.store_accessible is True


def test_status_domain_runs_empty_when_no_history(client: TestClient) -> None:
    resp = client.get("/status")
    data = resp.json()
    assert "domain_runs" in data
    assert isinstance(data["domain_runs"], list)
    assert len(data["domain_runs"]) == 0


def test_status_domain_runs_populated_after_run(
    client: TestClient, db_path: Path
) -> None:
    store = Store(db_path)
    now = datetime.now(UTC)
    store.save_run_history(
        RunHistory(
            id="rh1",
            domain_id="marine_oil",
            aoi_id="tobago",
            t_start=now,
            t_end=now,
            scenes_fetched=2,
            observations_created=5,
            status="complete",
        )
    )

    resp = client.get("/status")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["domain_runs"]) == 1
    run = data["domain_runs"][0]
    assert run["domain_id"] == "marine_oil"
    assert run["aoi_id"] == "tobago"
    assert run["last_run_status"] == "complete"
    assert run["scenes_fetched"] == 2
    assert run["observations_created"] == 5


def test_status_domain_runs_deduplicates_by_domain_aoi(
    client: TestClient, db_path: Path
) -> None:
    store = Store(db_path)
    now = datetime.now(UTC)
    for _ in range(3):
        store.save_run_history(
            RunHistory(
                id=f"rh-{_}",
                domain_id="marine_oil",
                aoi_id="tobago",
                t_start=now,
                t_end=now,
                status="complete",
            )
        )

    resp = client.get("/status")
    data = resp.json()
    # Only one entry per domain × AOI even after 3 runs
    marine_oil_tobago = [r for r in data["domain_runs"] if r["domain_id"] == "marine_oil"]
    assert len(marine_oil_tobago) == 1


def test_status_domain_runs_shows_multiple_domains(
    client: TestClient, db_path: Path
) -> None:
    store = Store(db_path)
    now = datetime.now(UTC)
    for domain in ("marine_oil", "inland_wq"):
        store.save_run_history(
            RunHistory(
                id=f"rh-{domain}",
                domain_id=domain,
                aoi_id="tobago",
                t_start=now,
                t_end=now,
                status="complete",
            )
        )

    resp = client.get("/status")
    data = resp.json()
    domain_ids = {r["domain_id"] for r in data["domain_runs"]}
    assert "marine_oil" in domain_ids
    assert "inland_wq" in domain_ids


def test_status_quota_field_present(client: TestClient) -> None:
    data = client.get("/status").json()
    quota = data["quota"]
    assert "cdse_bytes_today" in quota
    assert "cdse_daily_limit_gb" in quota
    assert "cdse_remaining_bytes" in quota


def test_status_open_meteo_calls_today_field(client: TestClient) -> None:
    data = client.get("/status").json()
    assert "open_meteo_calls_today" in data
    assert isinstance(data["open_meteo_calls_today"], int)


def test_status_last_run_shows_domain_run_timestamp(
    client: TestClient, db_path: Path
) -> None:
    store = Store(db_path)
    now = datetime.now(UTC)
    store.save_run_history(
        RunHistory(
            id="rh-ts",
            domain_id="marine_oil",
            aoi_id="tobago",
            t_start=now,
            t_end=now,
            status="complete",
        )
    )

    data = client.get("/status").json()
    run = data["domain_runs"][0]
    assert run["last_run_at"] is not None
    # ISO 8601 parseable
    parsed_ts = datetime.fromisoformat(run["last_run_at"])
    assert parsed_ts.tzinfo is not None or "Z" in run["last_run_at"] or "+" in run["last_run_at"]


def test_status_failed_run_shown_in_domain_runs(
    client: TestClient, db_path: Path
) -> None:
    store = Store(db_path)
    now = datetime.now(UTC)
    store.save_run_history(
        RunHistory(
            id="rh-err",
            domain_id="marine_oil",
            aoi_id="tobago",
            t_start=now,
            t_end=now,
            status="failed",
            error="CDSE timeout",
        )
    )

    data = client.get("/status").json()
    run = data["domain_runs"][0]
    assert run["last_run_status"] == "failed"
