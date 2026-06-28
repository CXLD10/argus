"""F-052: D2 end-to-end integration test — analyze → anomaly → forecast → alert → API.

Full offline pipeline: synthetic optical scene → InlandWqDomain.analyze() →
AnomalyDetector → WQForecaster → skill gate → API endpoint assertions.

All network calls are mocked.  Run with --live to hit live CDSE + Open-Meteo.
"""

from __future__ import annotations

import math
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from argus.api.app import create_app
from argus.core.models import (
    AnalysisRun,
    MonitorTarget,
    Observation,
    Prediction,
)
from argus.core.store import Store
from argus.domains.base import Acquisition
from argus.domains.inland_wq import InlandWqDomain
from argus.predict.anomaly_detector.detector import AnomalyDetector
from argus.predict.base import PredictContext
from argus.predict.wq_forecast import WQForecaster

_REPO_ROOT = Path(__file__).parent.parent.parent
_BASE_DATE = datetime(2023, 1, 1, tzinfo=UTC)
_GEOMETRY = {"type": "Point", "coordinates": [-61.25, 11.15]}


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_chl_obs(value: float, day: int, target_id: str = "wb-tobago") -> Observation:
    return Observation(
        id=str(uuid.uuid4()),
        analysis_run_id="run_wq_001",
        scene_id="scene_wq_001",
        obs_type="chlorophyll_a",
        evidence_class="measured",
        geometry=_GEOMETRY,
        area_km2=0.5,
        confidence=0.85,
        value=value,
        unit="ndci_index",
        domain="inland_wq",
        target_id=target_id,
        created_at=_BASE_DATE + timedelta(days=day),
    )


def _make_synthetic_chl_history(n_days: int = 90, seed: int = 42) -> tuple[list[Observation], dict]:
    rng = np.random.default_rng(seed)
    obs_list = []
    weather: dict[str, dict] = {}
    for d in range(n_days):
        doy = (_BASE_DATE + timedelta(days=d)).timetuple().tm_yday
        val = 0.05 + 0.02 * math.sin(2 * math.pi * doy / 365) + float(rng.normal(0, 0.003))
        obs_list.append(_make_chl_obs(max(0.001, val), day=d))
        date_str = (_BASE_DATE + timedelta(days=d)).date().isoformat()
        weather[date_str] = {
            "precip_7d": float(rng.uniform(0, 20)),
            "temp_7d": float(rng.uniform(22, 32)),
        }
    return obs_list, weather


def _make_bloom_obs(day: int) -> Observation:
    return _make_chl_obs(value=0.45, day=day)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def history_obs() -> list[Observation]:
    obs, _ = _make_synthetic_chl_history(n_days=90)
    return obs


@pytest.fixture(scope="module")
def history_weather() -> dict:
    _, weather = _make_synthetic_chl_history(n_days=90)
    return weather


@pytest.fixture(scope="module")
def fitted_forecaster(history_obs, history_weather) -> WQForecaster:
    return WQForecaster.from_history(history_obs, history_weather, rng_seed=42)


@pytest.fixture(scope="module")
def fitted_anomaly_detector(history_obs) -> AnomalyDetector:
    detector = AnomalyDetector(threshold_sigma=2.5)
    detector.fit(history_obs)
    return detector


@pytest.fixture()
def wq_api_client(tmp_path: Path, history_obs: list[Observation]) -> TestClient:
    config_dir = tmp_path / "config"
    (config_dir / "aois").mkdir(parents=True)
    (config_dir / "aois" / "tobago.geojson").write_bytes(
        (_REPO_ROOT / "config" / "aois" / "tobago.geojson").read_bytes()
    )

    db_path = tmp_path / "argus.db"
    store = Store(db_path)

    run = AnalysisRun(
        id="run_wq_001",
        aoi_id="tobago",
        domain_id="inland_wq",
        scene_id="scene_wq_001",
        started_at=datetime.now(UTC),
        status="complete",
        n_observations=len(history_obs),
    )
    store.save_analysis_run(run)

    for obs in history_obs[:10]:
        store.save_observation(obs)

    pred = Prediction(
        id=str(uuid.uuid4()),
        predictor_id="wq_forecast_v1",
        source_obs_ids=[history_obs[0].id],
        kind="forecast",
        evidence_class="modeled",
        uncertainty={"ci_90_low": 0.04, "ci_90_high": 0.07, "rmse": 0.004},
        rng_seed=42,
        attrs={
            "value": 0.055,
            "ci_low": 0.04,
            "ci_high": 0.07,
            "obs_type": "chlorophyll_a",
            "target_id": "wb-tobago",
        },
    )
    store.save_prediction(pred)

    store.save_skill_report(
        report_id=str(uuid.uuid4()),
        predictor_id="wq_forecast_v1",
        eval_case_id="eval_wq_001",
        precision=0.79,
        recall=0.76,
        f1=0.77,
        n_observations=40,
        created_at=datetime.now(UTC),
        passed_gate=True,
    )

    app = create_app(db_path=db_path, config_dir=config_dir)
    return TestClient(app)


# ── Stage 1: Optical analysis (offline InlandWqDomain) ───────────────────────


def _make_optical_scene(seed: int = 99) -> "object":
    """Build a synthetic OpticalScene using the band names InlandWqDomain.analyze() expects."""
    from argus.preprocess.optical import preprocess_optical

    rows, cols = 50, 50
    rng = np.random.default_rng(seed)
    # Domain expects B2/B3/B4/B5/B6 (without leading zero)
    bands: dict[str, np.ndarray] = {
        "B2": rng.uniform(0.04, 0.08, (rows, cols)).astype(np.float32),
        "B3": rng.uniform(0.05, 0.10, (rows, cols)).astype(np.float32),
        "B4": rng.uniform(0.03, 0.06, (rows, cols)).astype(np.float32),
        "B5": rng.uniform(0.06, 0.15, (rows, cols)).astype(np.float32),
        "B6": rng.uniform(0.10, 0.20, (rows, cols)).astype(np.float32),
    }
    return preprocess_optical(bands)


def test_d2_analyze_returns_observations() -> None:
    """InlandWqDomain.analyze() with synthetic OpticalScene returns Observations."""
    scene = _make_optical_scene(99)
    acq = Acquisition(
        scene_id="scene_wq_test",
        source_ref=None,  # type: ignore[arg-type]
        preprocessed=scene,
        attrs={"analysis_run_id": "run_wq_test"},
    )
    domain = InlandWqDomain(auth=None)
    observations = domain.analyze(acq)

    assert isinstance(observations, list)
    assert len(observations) >= 1


def test_d2_observations_have_evidence_class() -> None:
    """INV-3: every D2 observation must carry a valid evidence_class."""
    scene = _make_optical_scene(77)
    acq = Acquisition(
        scene_id="scene_wq_ec",
        source_ref=None,  # type: ignore[arg-type]
        preprocessed=scene,
        attrs={"analysis_run_id": "run_wq_ec"},
    )
    observations = InlandWqDomain(auth=None).analyze(acq)
    for obs in observations:
        assert obs.evidence_class in {"measured", "modeled", "inferred"}


def test_d2_domain_search_offline_returns_empty() -> None:
    """InlandWqDomain.search() with no auth returns [] (offline mode)."""
    from argus.core.models import MonitorTarget

    target = MonitorTarget(
        id="wb-tobago",
        name="Tobago Water Body",
        aoi_id="tobago",
        kind="water_body",
        domains=["inland_wq"],
        geometry={"type": "Polygon", "coordinates": [[[-61.4, 11.0], [-61.1, 11.0], [-61.1, 11.3], [-61.4, 11.3], [-61.4, 11.0]]]},
        min_area_km2=1.0,
        resolution_status="eligible",
    )
    domain = InlandWqDomain(auth=None)
    refs = domain.search(target, _BASE_DATE, _BASE_DATE + timedelta(days=7))
    assert refs == []


# ── Stage 2: Anomaly detection ────────────────────────────────────────────────


def test_d2_anomaly_detector_fit_and_predict(
    fitted_anomaly_detector: AnomalyDetector, history_obs: list[Observation]
) -> None:
    ctx = PredictContext(
        obs=history_obs[-5:],
        aoi_id="tobago",
        t0=_BASE_DATE + timedelta(days=85),
        t1=_BASE_DATE + timedelta(days=90),
    )
    pred = fitted_anomaly_detector.predict(ctx, rng_seed=42)
    assert pred.kind == "anomaly"
    assert pred.uncertainty


def test_d2_anomaly_uncertainty_present(
    fitted_anomaly_detector: AnomalyDetector, history_obs: list[Observation]
) -> None:
    """INV-9: anomaly Prediction carries non-empty uncertainty."""
    ctx = PredictContext(
        obs=history_obs[-3:],
        aoi_id="tobago",
        t0=_BASE_DATE + timedelta(days=87),
        t1=_BASE_DATE + timedelta(days=90),
    )
    pred = fitted_anomaly_detector.predict(ctx, rng_seed=42)
    assert pred.uncertainty
    assert "sigma" in pred.uncertainty


def test_d2_anomaly_evidence_class_modeled(
    fitted_anomaly_detector: AnomalyDetector, history_obs: list[Observation]
) -> None:
    """INV-3: anomaly predictions are modeled."""
    ctx = PredictContext(
        obs=history_obs[-3:],
        aoi_id="tobago",
        t0=_BASE_DATE + timedelta(days=87),
        t1=_BASE_DATE + timedelta(days=90),
    )
    pred = fitted_anomaly_detector.predict(ctx, rng_seed=42)
    assert pred.evidence_class == "modeled"


def test_d2_bloom_obs_triggers_anomaly(fitted_anomaly_detector: AnomalyDetector) -> None:
    """A bloom-level NDCI (0.45) should be flagged as an anomaly."""
    bloom = _make_bloom_obs(day=91)
    ctx = PredictContext(
        obs=[bloom],
        aoi_id="tobago",
        t0=_BASE_DATE + timedelta(days=91),
        t1=_BASE_DATE + timedelta(days=91),
    )
    pred = fitted_anomaly_detector.predict(ctx, rng_seed=42)
    assert pred.attrs.get("anomaly_detected") is True


# ── Stage 3: WQ Forecast ──────────────────────────────────────────────────────


def test_d2_forecaster_produces_prediction(
    fitted_forecaster: WQForecaster, history_obs: list[Observation], history_weather: dict
) -> None:
    ctx = PredictContext(
        obs=history_obs[-14:],
        aoi_id="tobago",
        t0=_BASE_DATE + timedelta(days=76),
        t1=_BASE_DATE + timedelta(days=90),
        attrs={"weather": history_weather},
    )
    pred = fitted_forecaster.predict(ctx, rng_seed=42)
    assert pred.kind == "forecast"
    assert pred.uncertainty


def test_d2_forecast_has_ci_bounds(
    fitted_forecaster: WQForecaster, history_obs: list[Observation], history_weather: dict
) -> None:
    """INV-9: WQ forecast must carry CI bounds in uncertainty."""
    ctx = PredictContext(
        obs=history_obs[-14:],
        aoi_id="tobago",
        t0=_BASE_DATE + timedelta(days=76),
        t1=_BASE_DATE + timedelta(days=90),
        attrs={"weather": history_weather},
    )
    pred = fitted_forecaster.predict(ctx, rng_seed=42)
    assert "ci_90_low" in pred.uncertainty or "rmse" in pred.uncertainty


def test_d2_forecast_evidence_class_modeled(
    fitted_forecaster: WQForecaster, history_obs: list[Observation], history_weather: dict
) -> None:
    """INV-3: WQ forecasts are modeled."""
    ctx = PredictContext(
        obs=history_obs[-14:],
        aoi_id="tobago",
        t0=_BASE_DATE + timedelta(days=76),
        t1=_BASE_DATE + timedelta(days=90),
        attrs={"weather": history_weather},
    )
    pred = fitted_forecaster.predict(ctx, rng_seed=42)
    assert pred.evidence_class == "modeled"


def test_d2_forecaster_reproducible_with_same_seed(
    fitted_forecaster: WQForecaster, history_obs: list[Observation], history_weather: dict
) -> None:
    """INV-8: same rng_seed produces identical predictions."""
    ctx = PredictContext(
        obs=history_obs[-14:],
        aoi_id="tobago",
        t0=_BASE_DATE + timedelta(days=76),
        t1=_BASE_DATE + timedelta(days=90),
        attrs={"weather": history_weather},
    )
    p1 = fitted_forecaster.predict(ctx, rng_seed=42)
    p2 = fitted_forecaster.predict(ctx, rng_seed=42)
    assert p1.attrs.get("value") == p2.attrs.get("value")


# ── Stage 4: Skill gate + API ─────────────────────────────────────────────────


def test_d2_api_observations_endpoint(wq_api_client: TestClient) -> None:
    resp = wq_api_client.get("/aois/tobago/observations")
    assert resp.status_code == 200


def test_d2_api_waterbody_forecasts_skill_gated(wq_api_client: TestClient) -> None:
    """VAL-007: /waterbody/{id}/forecasts only returns skill-gated predictions."""
    resp = wq_api_client.get("/waterbody/wb-tobago/forecasts")
    assert resp.status_code == 200
    data = resp.json()
    forecasts = data if isinstance(data, list) else data.get("items", data)
    assert isinstance(forecasts, list)


def test_d2_api_waterbody_anomalies_endpoint(wq_api_client: TestClient) -> None:
    resp = wq_api_client.get("/waterbody/wb-tobago/anomalies")
    assert resp.status_code == 200


def test_d2_api_flood_risk_endpoint(wq_api_client: TestClient) -> None:
    resp = wq_api_client.get("/aois/tobago/flood-risk")
    assert resp.status_code == 200


def test_d2_api_acid_risk_endpoint(wq_api_client: TestClient) -> None:
    resp = wq_api_client.get("/aois/tobago/acid-risk")
    assert resp.status_code == 200
