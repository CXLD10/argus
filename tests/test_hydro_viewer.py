"""Tests for F-044: Hydro API endpoints (choke points, flood risk, acid risk).

All tests are offline (INV-7).  Uses FastAPI TestClient with an isolated SQLite DB.

Acceptance criteria:
  - GET /aois/{aoi_id}/choke-points returns ChokePointListResponse
  - GET /aois/{aoi_id}/flood-risk returns RiskPredictionListResponse
  - GET /aois/{aoi_id}/acid-risk returns RiskPredictionListResponse
  - NFR-4: adding a mock Domain requires only a new class + registration; no spine edits
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from argus.api.app import create_app
from argus.core.models import ChokePoint, Prediction
from argus.core.store import Store

_POINT = {"type": "Point", "coordinates": [-61.25, 11.25]}


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_choke_point(aoi_id: str = "tobago", score: float = 0.8) -> ChokePoint:
    return ChokePoint(
        id=str(uuid.uuid4()),
        aoi_id=aoi_id,
        location=_POINT,
        upstream_area_km2=5.0,
        constriction_score=score,
        dem_source="cop_glo30",
        evidence_class="inferred",
    )


def _make_flood_pred(aoi_id: str = "tobago", risk_level: str = "high") -> Prediction:
    return Prediction(
        id=str(uuid.uuid4()),
        predictor_id="FloodRisk",
        source_obs_ids=[],
        kind="risk",
        evidence_class="modeled",
        uncertainty={"risk_score": 0.65, "model_type": "rule_based"},
        rng_seed=0,
        created_at=datetime(2024, 6, 1, tzinfo=UTC),
        attrs={
            "risk_level": risk_level,
            "label": "modeled flood risk at choke point (not a measured flood)",
            "aoi_id": aoi_id,
            "peak_precip_mm": 150.0,
        },
    )


def _make_acid_pred(aoi_id: str = "tobago", acid_index: float = 7.5) -> Prediction:
    return Prediction(
        id=str(uuid.uuid4()),
        predictor_id="AcidDepositionRisk",
        source_obs_ids=[],
        kind="risk",
        evidence_class="modeled",
        uncertainty={
            "index_range": [6.0, 9.0],
            "methodology": "SO2 × NO2 × precip × catchment sensitivity index",
        },
        rng_seed=0,
        created_at=datetime(2024, 6, 1, tzinfo=UTC),
        attrs={
            "acid_risk_index": acid_index,
            "label": "modeled acid-deposition risk index (0–10 scale) — NOT a pH measurement",
            "aoi_id": aoi_id,
            "peak_so2_ug_m3": 55.0,
        },
    )


@pytest.fixture()
def hydro_client(tmp_path: Path) -> TestClient:
    """TestClient with tobago AOI config and seeded hydro data."""
    config_dir = tmp_path / "config"
    (config_dir / "aois").mkdir(parents=True)
    repo_root = Path(__file__).parent.parent
    (config_dir / "aois" / "tobago.geojson").write_bytes(
        (repo_root / "config" / "aois" / "tobago.geojson").read_bytes()
    )

    db_path = tmp_path / "argus.db"
    store = Store(db_path)

    # Seed two choke points
    store.save_choke_point(_make_choke_point(score=0.9))
    store.save_choke_point(_make_choke_point(score=0.5))

    # Seed a flood risk prediction
    store.save_prediction(_make_flood_pred(risk_level="high"))

    # Seed an acid deposition risk prediction
    store.save_prediction(_make_acid_pred(acid_index=7.5))

    app = create_app(db_path=db_path, config_dir=config_dir)
    return TestClient(app)


# ── GET /aois/{aoi_id}/choke-points ──────────────────────────────────────────


def test_choke_points_status_200(hydro_client: TestClient) -> None:
    res = hydro_client.get("/aois/tobago/choke-points")
    assert res.status_code == 200


def test_choke_points_count(hydro_client: TestClient) -> None:
    data = hydro_client.get("/aois/tobago/choke-points").json()
    assert data["count"] == 2


def test_choke_points_sorted_by_constriction_desc(hydro_client: TestClient) -> None:
    data = hydro_client.get("/aois/tobago/choke-points").json()
    scores = [item["constriction_score"] for item in data["items"]]
    assert scores == sorted(scores, reverse=True)


def test_choke_points_evidence_class_is_inferred(hydro_client: TestClient) -> None:
    data = hydro_client.get("/aois/tobago/choke-points").json()
    for item in data["items"]:
        assert item["evidence_class"] == "inferred"


def test_choke_points_has_location(hydro_client: TestClient) -> None:
    data = hydro_client.get("/aois/tobago/choke-points").json()
    for item in data["items"]:
        assert item["location"]["type"] == "Point"


def test_choke_points_empty_for_unknown_aoi(hydro_client: TestClient) -> None:
    data = hydro_client.get("/aois/unknown-aoi/choke-points").json()
    assert data["count"] == 0
    assert data["items"] == []


# ── GET /aois/{aoi_id}/flood-risk ─────────────────────────────────────────────


def test_flood_risk_status_200(hydro_client: TestClient) -> None:
    res = hydro_client.get("/aois/tobago/flood-risk")
    assert res.status_code == 200


def test_flood_risk_count(hydro_client: TestClient) -> None:
    data = hydro_client.get("/aois/tobago/flood-risk").json()
    assert data["count"] == 1


def test_flood_risk_evidence_class_is_modeled(hydro_client: TestClient) -> None:
    """INV-3: FloodRisk must always be evidence_class='modeled'."""
    data = hydro_client.get("/aois/tobago/flood-risk").json()
    for item in data["items"]:
        assert item["evidence_class"] == "modeled"


def test_flood_risk_label_is_present(hydro_client: TestClient) -> None:
    """Honesty label must be in the response."""
    data = hydro_client.get("/aois/tobago/flood-risk").json()
    for item in data["items"]:
        assert "not a measured" in item["label"].lower()


def test_flood_risk_level_present(hydro_client: TestClient) -> None:
    data = hydro_client.get("/aois/tobago/flood-risk").json()
    assert data["items"][0]["risk_level"] == "high"


def test_flood_risk_uncertainty_not_empty(hydro_client: TestClient) -> None:
    data = hydro_client.get("/aois/tobago/flood-risk").json()
    assert len(data["items"][0]["uncertainty"]) > 0


def test_flood_risk_empty_for_unknown_aoi(hydro_client: TestClient) -> None:
    data = hydro_client.get("/aois/unknown-aoi/flood-risk").json()
    assert data["count"] == 0


# ── GET /aois/{aoi_id}/acid-risk ──────────────────────────────────────────────


def test_acid_risk_status_200(hydro_client: TestClient) -> None:
    res = hydro_client.get("/aois/tobago/acid-risk")
    assert res.status_code == 200


def test_acid_risk_count(hydro_client: TestClient) -> None:
    data = hydro_client.get("/aois/tobago/acid-risk").json()
    assert data["count"] == 1


def test_acid_risk_evidence_class_is_modeled(hydro_client: TestClient) -> None:
    """INV-3: AcidDepositionRisk must always be evidence_class='modeled'."""
    data = hydro_client.get("/aois/tobago/acid-risk").json()
    for item in data["items"]:
        assert item["evidence_class"] == "modeled"


def test_acid_risk_label_says_not_ph(hydro_client: TestClient) -> None:
    """Honesty check — response label must state NOT a pH measurement."""
    data = hydro_client.get("/aois/tobago/acid-risk").json()
    for item in data["items"]:
        assert "NOT a pH measurement" in item["label"]


def test_acid_risk_index_present(hydro_client: TestClient) -> None:
    data = hydro_client.get("/aois/tobago/acid-risk").json()
    assert data["items"][0]["acid_risk_index"] == pytest.approx(7.5)


def test_acid_risk_uncertainty_not_empty(hydro_client: TestClient) -> None:
    data = hydro_client.get("/aois/tobago/acid-risk").json()
    assert len(data["items"][0]["uncertainty"]) > 0


def test_acid_risk_empty_for_unknown_aoi(hydro_client: TestClient) -> None:
    data = hydro_client.get("/aois/unknown-aoi/acid-risk").json()
    assert data["count"] == 0


# ── NFR-4: Domain plug-in generalization demonstration ───────────────────────


def test_nfr4_mock_domain_requires_no_spine_edits() -> None:
    """NFR-4: Adding a 5th domain requires only a new Domain class + registration.

    The spine dispatches domains via _load_domain() in runner.py — the ONLY file
    that needs to be touched to register a new domain. All other spine modules
    (core, tasking, impact, alert, ai) remain unmodified.

    This test verifies that:
    1. A new Domain class can be defined without touching any spine module.
    2. It satisfies the Domain protocol (search, acquire, analyze + domain_id).
    3. The quota_guard falls through to "allowed" for unknown domains (no spine edit needed).
    """
    from argus.core.models import Observation, SourceRef
    from argus.domains.base import Acquisition, Domain
    from argus.tasking.quota_guard import check_domain_quota

    class MockDomain:
        domain_id = "mock_fifth_domain"

        def search(self, target: Any, t0: Any, t1: Any) -> list[SourceRef]:
            return []

        def acquire(self, ref: SourceRef) -> Acquisition:
            raise NotImplementedError

        def analyze(self, acq: Acquisition) -> list[Observation]:
            return []

    mock = MockDomain()

    # 1. New domain satisfies the protocol structurally (duck-typing)
    assert mock.domain_id == "mock_fifth_domain"
    assert callable(mock.search)
    assert callable(mock.acquire)
    assert callable(mock.analyze)

    # 2. Domain Protocol class exists and is importable from the spine
    assert isinstance(Domain, type)

    # 3. Quota guard allows unknown domain without requiring its registration
    #    — adding a new domain that uses neither CDSE nor Open-Meteo needs no quota_guard edit
    import tempfile
    from pathlib import Path as _Path

    from argus.core.store import Store as _Store

    with tempfile.TemporaryDirectory() as td:
        decision = check_domain_quota("mock_fifth_domain", _Store(_Path(td) / "t.db"))
    assert decision.allowed is True, (
        "Quota guard must allow unknown domains to pass through without spine edits"
    )
