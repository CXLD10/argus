"""F-015 tests: FastAPI service — health, AOIs, observations, predictions, impact."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from argus.api.app import create_app
from argus.core.models import (
    AnalysisRun,
    ExposureLayer,
    ForecastFrame,
    ImpactAssessment,
    Observation,
    Prediction,
)
from argus.core.store import Store

_GEOM = {
    "type": "Polygon",
    "coordinates": [[[-61.4, 11.0], [-61.1, 11.0], [-61.1, 11.3], [-61.4, 11.3], [-61.4, 11.0]]],
}


@pytest.fixture()
def api_client(tmp_path: Path):
    """TestClient backed by an isolated DB + config dir with tobago AOI."""
    config_dir = tmp_path / "config"
    (config_dir / "aois").mkdir(parents=True)
    repo_root = Path(__file__).parent.parent
    tobago_src = repo_root / "config" / "aois" / "tobago.geojson"
    (config_dir / "aois" / "tobago.geojson").write_bytes(tobago_src.read_bytes())

    db_path = tmp_path / "argus.db"
    app = create_app(db_path=db_path, config_dir=config_dir)
    return TestClient(app)


@pytest.fixture()
def seeded_client(tmp_path: Path):
    """TestClient with pre-seeded observations, prediction, and impact."""
    config_dir = tmp_path / "config"
    (config_dir / "aois").mkdir(parents=True)
    repo_root = Path(__file__).parent.parent
    (config_dir / "aois" / "tobago.geojson").write_bytes(
        (repo_root / "config" / "aois" / "tobago.geojson").read_bytes()
    )

    db_path = tmp_path / "argus.db"
    store = Store(db_path)

    run = AnalysisRun(
        id="run-001",
        aoi_id="tobago",
        domain_id="marine_oil",
        scene_id="scene-001",
        started_at=datetime.now(UTC),
        status="complete",
        n_observations=1,
    )
    store.save_analysis_run(run)

    obs = Observation(
        id="obs-001",
        analysis_run_id="run-001",
        scene_id="scene-001",
        obs_type="oil_slick",
        evidence_class="measured",
        geometry=_GEOM,
        area_km2=5.0,
        confidence=0.85,
        status="confirmed",
    )
    store.save_observation(obs)

    pred = Prediction(
        id="pred-001",
        predictor_id="oil_trajectory_v1",
        source_obs_ids=["obs-001"],
        kind="trajectory",
        uncertainty={"particle_spread_km": 18.0},
        rng_seed=42,
    )
    store.save_prediction(pred)

    frame = ForecastFrame(
        id="frame-001",
        prediction_id="pred-001",
        valid_at=datetime(2024, 2, 8, 0, 0, tzinfo=UTC),
        footprint=_GEOM,
        particle_count=1000,
        stats={"mean_lon": -61.25, "mean_lat": 11.15},
    )
    store.save_forecast_frame(frame)

    layer = ExposureLayer(
        id="coast-tobago",
        name="Tobago coastline",
        layer_type="coastline",
        geometry={
            "type": "LineString",
            "coordinates": [[-61.5, 11.15], [-61.2, 11.05], [-61.0, 10.95]],
        },
    )
    store.save_exposure_layer(layer)

    ia = ImpactAssessment(
        id=str(uuid.uuid4()),
        prediction_id="pred-001",
        exposure_layer_id="coast-tobago",
        valid_at=datetime(2024, 2, 8, 0, 0, tzinfo=UTC),
        eta_hours=24.0,
        metrics={"coast_length_km": 12.5},
    )
    store.save_impact_assessment(ia)

    app = create_app(db_path=db_path, config_dir=config_dir)
    return TestClient(app)


# ── /health ───────────────────────────────────────────────────────────────────


def test_health_returns_200(api_client: TestClient) -> None:
    resp = api_client.get("/health")
    assert resp.status_code == 200


def test_health_status_ok(api_client: TestClient) -> None:
    resp = api_client.get("/health")
    assert resp.json()["status"] == "ok"


def test_health_version_present(api_client: TestClient) -> None:
    resp = api_client.get("/health")
    assert "version" in resp.json()


# ── GET /aois ─────────────────────────────────────────────────────────────────


def test_list_aois_returns_200(api_client: TestClient) -> None:
    resp = api_client.get("/aois")
    assert resp.status_code == 200


def test_list_aois_count_matches_items(api_client: TestClient) -> None:
    resp = api_client.get("/aois")
    data = resp.json()
    assert data["count"] == len(data["items"])


def test_list_aois_contains_tobago(api_client: TestClient) -> None:
    resp = api_client.get("/aois")
    ids = [a["id"] for a in resp.json()["items"]]
    assert "tobago" in ids


def test_get_aoi_tobago_returns_200(api_client: TestClient) -> None:
    resp = api_client.get("/aois/tobago")
    assert resp.status_code == 200


def test_get_aoi_tobago_fields(api_client: TestClient) -> None:
    resp = api_client.get("/aois/tobago")
    data = resp.json()
    assert data["id"] == "tobago"
    assert "geometry" in data
    assert "domains" in data


def test_get_aoi_missing_returns_404(api_client: TestClient) -> None:
    resp = api_client.get("/aois/nonexistent")
    assert resp.status_code == 404


# ── GET /aois/{id}/observations ───────────────────────────────────────────────


def test_observations_returns_200(seeded_client: TestClient) -> None:
    resp = seeded_client.get("/aois/tobago/observations")
    assert resp.status_code == 200


def test_observations_count_nonzero(seeded_client: TestClient) -> None:
    resp = seeded_client.get("/aois/tobago/observations")
    assert resp.json()["count"] >= 1


def test_observations_schema_valid(seeded_client: TestClient) -> None:
    resp = seeded_client.get("/aois/tobago/observations")
    item = resp.json()["items"][0]
    for key in ("id", "obs_type", "evidence_class", "area_km2", "confidence", "status"):
        assert key in item


def test_observations_empty_aoi(api_client: TestClient) -> None:
    resp = api_client.get("/aois/tobago/observations")
    assert resp.status_code == 200
    assert resp.json()["count"] == 0


def test_observations_status_filter(seeded_client: TestClient) -> None:
    resp = seeded_client.get("/aois/tobago/observations?status=confirmed")
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["status"] == "confirmed"


def test_observations_obs_type_filter(seeded_client: TestClient) -> None:
    resp = seeded_client.get("/aois/tobago/observations?obs_type=oil_slick")
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["obs_type"] == "oil_slick"


# ── GET /aois/{id}/predictions ────────────────────────────────────────────────


def test_predictions_returns_200(seeded_client: TestClient) -> None:
    resp = seeded_client.get("/aois/tobago/predictions")
    assert resp.status_code == 200


def test_predictions_count_nonzero(seeded_client: TestClient) -> None:
    resp = seeded_client.get("/aois/tobago/predictions")
    assert resp.json()["count"] >= 1


def test_predictions_schema_valid(seeded_client: TestClient) -> None:
    resp = seeded_client.get("/aois/tobago/predictions")
    item = resp.json()["items"][0]
    for key in ("id", "predictor_id", "kind", "evidence_class", "uncertainty", "frames"):
        assert key in item


def test_predictions_attribution_present(seeded_client: TestClient) -> None:
    resp = seeded_client.get("/aois/tobago/predictions")
    assert "_attribution" in resp.json()


def test_predictions_frames_embedded(seeded_client: TestClient) -> None:
    resp = seeded_client.get("/aois/tobago/predictions")
    pred = resp.json()["items"][0]
    assert isinstance(pred["frames"], list)
    assert len(pred["frames"]) >= 1


def test_predictions_empty_aoi(api_client: TestClient) -> None:
    resp = api_client.get("/aois/tobago/predictions")
    assert resp.status_code == 200


# ── GET /aois/{id}/impact ─────────────────────────────────────────────────────


def test_impact_returns_200(seeded_client: TestClient) -> None:
    resp = seeded_client.get("/aois/tobago/impact")
    assert resp.status_code == 200


def test_impact_count_nonzero(seeded_client: TestClient) -> None:
    resp = seeded_client.get("/aois/tobago/impact")
    assert resp.json()["count"] >= 1


def test_impact_schema_valid(seeded_client: TestClient) -> None:
    resp = seeded_client.get("/aois/tobago/impact")
    item = resp.json()["items"][0]
    for key in ("id", "prediction_id", "exposure_layer_id", "eta_hours", "metrics"):
        assert key in item


def test_impact_attribution_present(seeded_client: TestClient) -> None:
    resp = seeded_client.get("/aois/tobago/impact")
    assert "_attribution" in resp.json()


def test_impact_empty_aoi(api_client: TestClient) -> None:
    resp = api_client.get("/aois/tobago/impact")
    assert resp.status_code == 200
    assert resp.json()["count"] == 0


# ── F-016: Web Viewer ─────────────────────────────────────────────────────────


def test_root_returns_200(api_client: TestClient) -> None:
    resp = api_client.get("/")
    assert resp.status_code == 200


def test_root_returns_html(api_client: TestClient) -> None:
    resp = api_client.get("/")
    assert "text/html" in resp.headers["content-type"]


def test_root_contains_argus_title(api_client: TestClient) -> None:
    resp = api_client.get("/")
    assert "Argus" in resp.text


def test_static_css_served(api_client: TestClient) -> None:
    resp = api_client.get("/static/style.css")
    assert resp.status_code == 200


def test_static_js_served(api_client: TestClient) -> None:
    resp = api_client.get("/static/app.js")
    assert resp.status_code == 200


def test_viewer_loads_from_api_endpoints(api_client: TestClient) -> None:
    # The JS (not the HTML) contains the API calls to /aois.
    js = api_client.get("/static/app.js").text
    assert "/aois" in js


def test_viewer_references_leaflet(api_client: TestClient) -> None:
    html = api_client.get("/").text
    assert "leaflet" in html.lower()
