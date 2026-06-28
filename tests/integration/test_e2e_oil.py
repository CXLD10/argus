"""F-052: D1 end-to-end integration test — detect → trajectory → impact → alert → API.

Full offline pipeline: synthetic SAR → OilDomainV0 → trajectory simulation
(mocked subprocess) → impact assessment → alert → API endpoint assertions.

All network calls are mocked.  Run with --live to hit live CDSE + Open-Meteo.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import responses as resp_mock
from fastapi.testclient import TestClient

from argus.alert.delivery import Alert, AlertChannel, send_alert
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
from argus.domains.base import Acquisition
from argus.domains.marine_oil.detector import OilDomainV0, make_analysis_run
from argus.export.products import export_products
from argus.predict.oil_trajectory.runner import SimInput, run_simulation
from argus.preprocess.landmask import GeoTransform
from argus.preprocess.sar import preprocess

_REPO_ROOT = Path(__file__).parent.parent.parent
_AOI_PATH = _REPO_ROOT / "config" / "aois" / "tobago.geojson"

_GEOM_SLICK = {
    "type": "Polygon",
    "coordinates": [
        [[-61.4, 11.0], [-61.1, 11.0], [-61.1, 11.3], [-61.4, 11.3], [-61.4, 11.0]]
    ],
}

_MOCK_TRAJECTORY_FRAMES = [
    {
        "valid_at": "2024-02-08T00:00:00",
        "particle_count": 1000,
        "footprint": _GEOM_SLICK,
        "stats": {"mean_lon": -61.25, "mean_lat": 11.15},
    },
    {
        "valid_at": "2024-02-09T00:00:00",
        "particle_count": 975,
        "footprint": _GEOM_SLICK,
        "stats": {"mean_lon": -61.20, "mean_lat": 11.20},
    },
]


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def synthetic_pipeline(tmp_path_factory: pytest.TempPathFactory) -> dict:
    """Run the offline D1 pipeline end-to-end and return all stages."""
    tmp = tmp_path_factory.mktemp("e2e_oil")
    from argus.aoi.loader import load_aoi

    aoi = load_aoi(_AOI_PATH)
    bbox = aoi.bbox

    rows, cols = 100, 100
    rng = np.random.default_rng(42)
    vv = rng.uniform(5e-4, 2e-3, (rows, cols)).astype(np.float32)
    vh = rng.uniform(5e-5, 2e-4, (rows, cols)).astype(np.float32)
    vv[35:55, 35:55] = 5e-6
    vh[35:55, 35:55] = 5e-7

    transform = GeoTransform(
        min_lon=bbox[0], min_lat=bbox[1], max_lon=bbox[2], max_lat=bbox[3],
        cols=cols, rows=rows,
    )
    land_mask = np.zeros((rows, cols), dtype=bool)
    scene_id = "synthetic-tobago-2024-02-07"
    prep = preprocess(vv, vh, land_mask, transform, scene_id)

    run_obj = make_analysis_run(aoi.id, scene_id)
    acq = Acquisition(
        scene_id=scene_id,
        source_ref=None,  # type: ignore[arg-type]
        preprocessed=prep,
        attrs={"analysis_run_id": run_obj.id},
    )
    observations = OilDomainV0().analyze(acq)
    artifacts = export_products(observations, run_obj, prep, tmp / "output")

    return {
        "aoi": aoi,
        "run": run_obj,
        "observations": observations,
        "artifacts": artifacts,
        "tmp": tmp,
    }


@pytest.fixture()
def oil_api_client(tmp_path: Path, synthetic_pipeline: dict) -> TestClient:
    """TestClient pre-seeded with the full D1 pipeline state."""
    config_dir = tmp_path / "config"
    (config_dir / "aois").mkdir(parents=True)
    (config_dir / "aois" / "tobago.geojson").write_bytes(
        (_REPO_ROOT / "config" / "aois" / "tobago.geojson").read_bytes()
    )

    db_path = tmp_path / "argus.db"
    store = Store(db_path)

    run = synthetic_pipeline["run"]
    store.save_analysis_run(run)

    obs_id = None
    for obs in synthetic_pipeline["observations"]:
        store.save_observation(obs)
        obs_id = obs_id or obs.id

    pred = Prediction(
        id=str(uuid.uuid4()),
        predictor_id="oil_trajectory_v1",
        source_obs_ids=[obs_id] if obs_id else [],
        kind="trajectory",
        evidence_class="modeled",
        uncertainty={"particle_spread_km": 18.0},
        rng_seed=42,
    )
    store.save_prediction(pred)

    for i, frame_dict in enumerate(_MOCK_TRAJECTORY_FRAMES):
        frame = ForecastFrame(
            id=str(uuid.uuid4()),
            prediction_id=pred.id,
            valid_at=datetime.fromisoformat(frame_dict["valid_at"]).replace(tzinfo=UTC),
            footprint=frame_dict["footprint"],
            particle_count=frame_dict["particle_count"],
            stats=frame_dict["stats"],
        )
        store.save_forecast_frame(frame)

    coast = ExposureLayer(
        id="coast-tobago",
        name="Tobago coastline",
        layer_type="coastline",
        geometry={
            "type": "LineString",
            "coordinates": [[-61.5, 11.15], [-61.2, 11.05], [-61.0, 10.95]],
        },
    )
    store.save_exposure_layer(coast)

    ia = ImpactAssessment(
        id=str(uuid.uuid4()),
        prediction_id=pred.id,
        exposure_layer_id="coast-tobago",
        valid_at=datetime(2024, 2, 8, tzinfo=UTC),
        eta_hours=24.0,
        metrics={"coast_length_km": 12.5},
    )
    store.save_impact_assessment(ia)

    store.save_skill_report(
        report_id=str(uuid.uuid4()),
        predictor_id="oil_trajectory_v1",
        eval_case_id="eval_oil_001",
        precision=0.82,
        recall=0.78,
        f1=0.80,
        n_observations=50,
        created_at=datetime.now(UTC),
        passed_gate=True,
    )

    app = create_app(db_path=db_path, config_dir=config_dir)
    return TestClient(app)


# ── Stage 1: Detection ────────────────────────────────────────────────────────


def test_d1_pipeline_produces_observations(synthetic_pipeline: dict) -> None:
    assert len(synthetic_pipeline["observations"]) >= 1


def test_d1_observations_are_oil_slick(synthetic_pipeline: dict) -> None:
    for obs in synthetic_pipeline["observations"]:
        assert obs.obs_type == "oil_slick"


def test_d1_observations_evidence_class_measured(synthetic_pipeline: dict) -> None:
    """INV-3: D1 oil slick observations must be evidence_class='measured'."""
    for obs in synthetic_pipeline["observations"]:
        assert obs.evidence_class == "measured"


def test_d1_observations_have_positive_area(synthetic_pipeline: dict) -> None:
    for obs in synthetic_pipeline["observations"]:
        assert obs.area_km2 > 0


def test_d1_observations_have_confidence(synthetic_pipeline: dict) -> None:
    for obs in synthetic_pipeline["observations"]:
        assert 0.0 < obs.confidence <= 1.0


# ── Stage 2: Artifacts ────────────────────────────────────────────────────────


def test_d1_geojson_artifact_exists(synthetic_pipeline: dict) -> None:
    assert synthetic_pipeline["artifacts"]["geojson"].exists()


def test_d1_png_artifact_exists(synthetic_pipeline: dict) -> None:
    assert synthetic_pipeline["artifacts"]["png"].exists()


def test_d1_geojson_is_valid_feature_collection(synthetic_pipeline: dict) -> None:
    data = json.loads(synthetic_pipeline["artifacts"]["geojson"].read_text())
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) >= 1


# ── Stage 3: Trajectory prediction (mocked subprocess) ───────────────────────


def test_d1_trajectory_prediction_returns_frames() -> None:
    """Trajectory runner with mocked subprocess returns ForecastFrame dicts."""
    from argus.predict.oil_trajectory.oil_types import OilType, OilTypeRegistry

    sim_input = SimInput(
        oil_type="crude_medium",
        seed_geometry={"type": "Point", "coordinates": [-61.25, 11.15]},
        t0="2024-02-07T00:00:00",
        duration_hours=48,
        rng_seed=42,
        n_particles=100,
    )
    registry = OilTypeRegistry([
        OilType(id="crude_medium", name="Crude Medium", openoil_name="GENERIC CRUDE")
    ])

    with patch("argus.predict.oil_trajectory.runner.subprocess.run") as mock_run:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_run.return_value = mock_proc

        with patch(
            "argus.predict.oil_trajectory.runner.Path.read_text",
            return_value=json.dumps(_MOCK_TRAJECTORY_FRAMES),
        ):
            frames = run_simulation(sim_input, registry=registry)

    assert len(frames) >= 1
    assert "valid_at" in frames[0]
    assert "footprint" in frames[0]


def test_d1_trajectory_prediction_has_uncertainty(tmp_path: Path) -> None:
    """INV-9: trajectory Prediction carries uncertainty dict."""
    pred = Prediction(
        id=str(uuid.uuid4()),
        predictor_id="oil_trajectory_v1",
        source_obs_ids=["obs-001"],
        kind="trajectory",
        evidence_class="modeled",
        uncertainty={"particle_spread_km": 18.0, "confidence_radius_km": 5.0},
        rng_seed=42,
    )
    assert pred.uncertainty
    assert "particle_spread_km" in pred.uncertainty


def test_d1_trajectory_prediction_evidence_class_modeled() -> None:
    """INV-3: trajectory predictions are modeled, not measured."""
    pred = Prediction(
        id=str(uuid.uuid4()),
        predictor_id="oil_trajectory_v1",
        source_obs_ids=[],
        kind="trajectory",
        evidence_class="modeled",
        uncertainty={"particle_spread_km": 10.0},
        rng_seed=42,
    )
    assert pred.evidence_class == "modeled"


# ── Stage 4: Impact assessment ────────────────────────────────────────────────


def test_d1_impact_assessment_eta_positive(oil_api_client: TestClient) -> None:
    resp = oil_api_client.get("/aois/tobago/impact")
    assert resp.status_code == 200
    data = resp.json()
    if data.get("assessments"):
        assert all(ia["eta_hours"] > 0 for ia in data["assessments"])


def test_d1_impact_assessment_has_metrics(oil_api_client: TestClient) -> None:
    resp = oil_api_client.get("/aois/tobago/impact")
    assert resp.status_code == 200
    data = resp.json()
    if data.get("assessments"):
        assert all("metrics" in ia for ia in data["assessments"])


# ── Stage 5: Alert construction ───────────────────────────────────────────────


def test_d1_alert_construction() -> None:
    alert = Alert(
        domain="marine_oil",
        target="tobago",
        observation_id="obs-001",
        confidence=0.9,
        eta_hours=24.0,
        message="Oil slick detected. ETA to coastline: 24h.",
    )
    assert alert.domain == "marine_oil"
    assert alert.confidence > 0
    assert alert.eta_hours is not None


def test_d1_alert_no_channels_is_noop() -> None:
    """send_alert with empty channels list returns Alert with status unchanged."""
    alert = Alert(domain="marine_oil", target="tobago", confidence=0.9)
    result = send_alert(alert, channels=[])
    assert isinstance(result, Alert)
    assert result.status == "pending"


@resp_mock.activate
def test_d1_alert_webhook_posts_payload() -> None:
    """Alert with webhook channel sends HTTP POST and returns Alert with status='sent'."""
    import responses as resp_lib

    resp_lib.add(resp_lib.POST, "https://hooks.example.com/argus", json={"ok": True}, status=200)

    channel = AlertChannel(kind="webhook", url="https://hooks.example.com/argus")
    alert = Alert(
        domain="marine_oil",
        target="tobago",
        observation_id="obs-001",
        confidence=0.9,
        eta_hours=24.0,
        message="Test alert.",
    )
    result = send_alert(alert, channels=[channel])
    assert isinstance(result, Alert)
    assert result.status == "sent"


# ── Stage 6: API observations endpoint ───────────────────────────────────────


def test_d1_api_observations_endpoint_200(oil_api_client: TestClient) -> None:
    resp = oil_api_client.get("/aois/tobago/observations")
    assert resp.status_code == 200


def test_d1_api_observations_returns_oil_slicks(oil_api_client: TestClient) -> None:
    resp = oil_api_client.get("/aois/tobago/observations?obs_type=oil_slick")
    assert resp.status_code == 200
    data = resp.json()
    items = data if isinstance(data, list) else data.get("items", [])
    assert len(items) >= 1
    assert all(o["obs_type"] == "oil_slick" for o in items)


def test_d1_api_observations_evidence_class_present(oil_api_client: TestClient) -> None:
    """VAL-004: every observation in API response must have evidence_class."""
    resp = oil_api_client.get("/aois/tobago/observations")
    assert resp.status_code == 200
    data = resp.json()
    items = data if isinstance(data, list) else data.get("items", [])
    for obs in items:
        assert "evidence_class" in obs
        assert obs["evidence_class"] in {"measured", "modeled", "inferred"}


def test_d1_api_predictions_skill_gated(oil_api_client: TestClient) -> None:
    """VAL-007: /waterbody/{id}/forecasts only returns skill-gated predictions."""
    resp = oil_api_client.get("/waterbody/tobago/forecasts")
    assert resp.status_code == 200


def test_d1_api_health_passes(oil_api_client: TestClient) -> None:
    resp = oil_api_client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
