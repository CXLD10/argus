"""F-018 API contract tests.

These tests lock the D1 API schema. Any breaking change — dropped required field, type
change, removed endpoint — will cause a test here to fail before it reaches consumers.
Uses Pydantic model_validate() as the schema assertion mechanism: if the API response
no longer satisfies the declared schema, ValidationError is raised and the test fails.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from argus import __version__
from argus.api.app import create_app
from argus.api.schemas import (
    AOIListResponse,
    AOISchema,
    ImpactListResponse,
    ObservationListResponse,
    PredictionListResponse,
)
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
def client(tmp_path: Path) -> TestClient:
    config_dir = tmp_path / "config"
    (config_dir / "aois").mkdir(parents=True)
    repo_root = Path(__file__).parent.parent
    (config_dir / "aois" / "tobago.geojson").write_bytes(
        (repo_root / "config" / "aois" / "tobago.geojson").read_bytes()
    )
    db_path = tmp_path / "argus.db"
    store = Store(db_path)

    run = AnalysisRun(
        id="run-c1",
        aoi_id="tobago",
        domain_id="marine_oil",
        scene_id="scene-c1",
        started_at=datetime.now(UTC),
        status="complete",
        n_observations=1,
    )
    store.save_analysis_run(run)

    obs = Observation(
        id="obs-c1",
        analysis_run_id="run-c1",
        scene_id="scene-c1",
        obs_type="oil_slick",
        evidence_class="measured",
        geometry=_GEOM,
        area_km2=5.0,
        confidence=0.85,
        status="confirmed",
    )
    store.save_observation(obs)

    pred = Prediction(
        id="pred-c1",
        predictor_id="oil_trajectory_v1",
        source_obs_ids=["obs-c1"],
        kind="trajectory",
        uncertainty={"particle_spread_km": 18.0},
        rng_seed=42,
    )
    store.save_prediction(pred)

    frame = ForecastFrame(
        id="frame-c1",
        prediction_id="pred-c1",
        valid_at=datetime(2024, 2, 8, 0, 0, tzinfo=UTC),
        footprint=_GEOM,
        particle_count=1000,
        stats={"mean_lon": -61.25, "mean_lat": 11.15},
    )
    store.save_forecast_frame(frame)

    layer = ExposureLayer(
        id="coast-c1",
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
        prediction_id="pred-c1",
        exposure_layer_id="coast-c1",
        valid_at=datetime(2024, 2, 8, 0, 0, tzinfo=UTC),
        eta_hours=24.0,
        metrics={"coast_length_km": 12.5},
    )
    store.save_impact_assessment(ia)

    return TestClient(create_app(db_path=db_path, config_dir=config_dir))


# ── OpenAPI spec endpoint ──────────────────────────────────────────────────────


def test_openapi_json_returns_200(client: TestClient) -> None:
    assert client.get("/openapi.json").status_code == 200


def test_openapi_json_has_info_title(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    assert spec["info"]["title"] == "Argus Environmental Intelligence API"


def test_openapi_json_version_matches_package(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    assert spec["info"]["version"] == __version__


def test_openapi_json_has_observations_path(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    assert any("/observations" in p for p in spec["paths"])


def test_openapi_json_has_predictions_path(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    assert any("/predictions" in p for p in spec["paths"])


def test_openapi_json_has_impact_path(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    assert any("/impact" in p for p in spec["paths"])


def test_openapi_json_has_health_path(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    assert "/health" in spec["paths"]


# ── Contract: GET /aois → AOIListResponse ─────────────────────────────────────


def test_aoi_list_validates_against_schema(client: TestClient) -> None:
    resp = client.get("/aois")
    AOIListResponse.model_validate(resp.json())


def test_aoi_list_required_fields(client: TestClient) -> None:
    item = client.get("/aois").json()["items"][0]
    for field in ("id", "name", "geometry", "domains", "active"):
        assert field in item, f"required field '{field}' missing from AOI response"


def test_aoi_get_validates_against_schema(client: TestClient) -> None:
    resp = client.get("/aois/tobago")
    AOISchema.model_validate(resp.json())


def test_aoi_get_required_fields(client: TestClient) -> None:
    data = client.get("/aois/tobago").json()
    for field in ("id", "name", "geometry", "domains", "active"):
        assert field in data, f"required field '{field}' missing from GET /aois/tobago"


# ── Contract: GET /aois/{id}/observations → ObservationListResponse ───────────


def test_observations_validates_against_schema(client: TestClient) -> None:
    resp = client.get("/aois/tobago/observations")
    ObservationListResponse.model_validate(resp.json())


def test_observations_required_envelope_fields(client: TestClient) -> None:
    data = client.get("/aois/tobago/observations").json()
    assert "items" in data, "envelope field 'items' missing"
    assert "count" in data, "envelope field 'count' missing"


def test_observations_required_item_fields(client: TestClient) -> None:
    item = client.get("/aois/tobago/observations").json()["items"][0]
    for field in (
        "id",
        "analysis_run_id",
        "scene_id",
        "obs_type",
        "evidence_class",
        "geometry",
        "area_km2",
        "confidence",
        "status",
        "created_at",
    ):
        assert field in item, f"required field '{field}' missing from ObservationSchema"


def test_observations_evidence_class_is_valid(client: TestClient) -> None:
    items = client.get("/aois/tobago/observations").json()["items"]
    for item in items:
        assert item["evidence_class"] in ("measured", "modeled", "inferred")


def test_observations_confidence_in_range(client: TestClient) -> None:
    items = client.get("/aois/tobago/observations").json()["items"]
    for item in items:
        assert 0.0 <= item["confidence"] <= 1.0


# ── Contract: GET /aois/{id}/predictions → PredictionListResponse ─────────────


def test_predictions_validates_against_schema(client: TestClient) -> None:
    resp = client.get("/aois/tobago/predictions")
    PredictionListResponse.model_validate(resp.json(), by_alias=True)


def test_predictions_required_envelope_fields(client: TestClient) -> None:
    data = client.get("/aois/tobago/predictions").json()
    assert "items" in data
    assert "count" in data


def test_predictions_attribution_present(client: TestClient) -> None:
    data = client.get("/aois/tobago/predictions").json()
    assert "_attribution" in data, "_attribution field missing from predictions response"


def test_predictions_attribution_mentions_open_meteo(client: TestClient) -> None:
    data = client.get("/aois/tobago/predictions").json()
    assert "Open-Meteo" in data["_attribution"]


def test_predictions_required_item_fields(client: TestClient) -> None:
    item = client.get("/aois/tobago/predictions").json()["items"][0]
    for field in ("id", "predictor_id", "kind", "evidence_class", "uncertainty", "frames"):
        assert field in item, f"required field '{field}' missing from PredictionSchema"


def test_predictions_frames_is_list(client: TestClient) -> None:
    item = client.get("/aois/tobago/predictions").json()["items"][0]
    assert isinstance(item["frames"], list)


def test_predictions_frame_required_fields(client: TestClient) -> None:
    frame = client.get("/aois/tobago/predictions").json()["items"][0]["frames"][0]
    for field in ("id", "prediction_id", "valid_at", "footprint", "particle_count", "stats"):
        assert field in frame, f"required field '{field}' missing from ForecastFrameSchema"


def test_predictions_uncertainty_non_empty(client: TestClient) -> None:
    item = client.get("/aois/tobago/predictions").json()["items"][0]
    assert item["uncertainty"], "uncertainty must be non-empty (INV-9)"


# ── Contract: GET /aois/{id}/impact → ImpactListResponse ──────────────────────


def test_impact_validates_against_schema(client: TestClient) -> None:
    resp = client.get("/aois/tobago/impact")
    ImpactListResponse.model_validate(resp.json(), by_alias=True)


def test_impact_required_envelope_fields(client: TestClient) -> None:
    data = client.get("/aois/tobago/impact").json()
    assert "items" in data
    assert "count" in data


def test_impact_attribution_present(client: TestClient) -> None:
    data = client.get("/aois/tobago/impact").json()
    assert "_attribution" in data, "_attribution field missing from impact response"


def test_impact_attribution_mentions_open_meteo(client: TestClient) -> None:
    data = client.get("/aois/tobago/impact").json()
    assert "Open-Meteo" in data["_attribution"]


def test_impact_required_item_fields(client: TestClient) -> None:
    item = client.get("/aois/tobago/impact").json()["items"][0]
    for field in (
        "id",
        "prediction_id",
        "exposure_layer_id",
        "valid_at",
        "eta_hours",
        "metrics",
    ):
        assert field in item, f"required field '{field}' missing from ImpactAssessmentSchema"


def test_impact_eta_hours_is_float(client: TestClient) -> None:
    item = client.get("/aois/tobago/impact").json()["items"][0]
    assert isinstance(item["eta_hours"], float | int)


# ── Breaking-change sentinels ─────────────────────────────────────────────────
# If any of these fields are removed from the schema, the Pydantic validation above
# will raise ValidationError. These explicit tests double-lock the contract: they
# will fail even if Pydantic's strict mode ever relaxes on extras.


def test_sentinel_observation_has_evidence_class(client: TestClient) -> None:
    """Removing evidence_class breaks INV-3 compliance — must always be present."""
    resp = client.get("/aois/tobago/observations")
    ObservationListResponse.model_validate(resp.json())
    assert resp.json()["items"][0]["evidence_class"] in ("measured", "modeled", "inferred")


def test_sentinel_prediction_has_uncertainty(client: TestClient) -> None:
    """Removing uncertainty breaks INV-9 — must always be present and non-empty."""
    resp = client.get("/aois/tobago/predictions")
    data = resp.json()
    PredictionListResponse.model_validate(data, by_alias=True)
    assert data["items"][0]["uncertainty"]


def test_sentinel_prediction_has_attribution(client: TestClient) -> None:
    """Removing _attribution breaks CC-BY-4.0 Open-Meteo licence requirement."""
    data = client.get("/aois/tobago/predictions").json()
    assert "_attribution" in data
    assert data["_attribution"]


def test_sentinel_impact_has_attribution(client: TestClient) -> None:
    """Impact forecasts use Open-Meteo forcing; _attribution is required."""
    data = client.get("/aois/tobago/impact").json()
    assert "_attribution" in data
    assert data["_attribution"]


def test_sentinel_schema_validation_catches_missing_required_field() -> None:
    """Verify that model_validate() raises ValidationError on a broken response."""
    broken = {"items": [{"id": "x"}], "count": 1}  # missing required fields
    with pytest.raises(ValidationError):
        ObservationListResponse.model_validate(broken)


def test_sentinel_aoi_schema_rejects_missing_geometry() -> None:
    """AOI geometry is load-bearing — its absence must be a schema violation."""
    broken = {"id": "x", "name": "X", "domains": [], "active": True}  # no geometry
    with pytest.raises(ValidationError):
        AOISchema.model_validate(broken)
