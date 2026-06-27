"""F-006 tests: GeoJSON and PNG product export."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest

from argus.core.models import AnalysisRun, Observation
from argus.export.products import export_geojson, export_png, export_products
from argus.preprocess.landmask import GeoTransform
from argus.preprocess.sar import PreprocessedScene

_GEOM = {
    "type": "Polygon",
    "coordinates": [[[-61.0, 11.0], [-60.9, 11.0], [-60.9, 11.1], [-61.0, 11.1], [-61.0, 11.0]]],
}
_TRANSFORM = GeoTransform(
    min_lon=-61.2, min_lat=10.8, max_lon=-60.3, max_lat=11.5, cols=100, rows=100
)


@pytest.fixture
def sample_run() -> AnalysisRun:
    return AnalysisRun(
        id="run-export-001",
        aoi_id="tobago",
        domain_id="marine_oil",
        scene_id="scene-export-001",
        started_at=datetime(2024, 2, 7, 22, 0, 0, tzinfo=UTC),
        status="complete",
        n_observations=1,
    )


@pytest.fixture
def sample_obs() -> Observation:
    return Observation(
        id="obs-export-001",
        analysis_run_id="run-export-001",
        scene_id="scene-export-001",
        obs_type="oil_slick",
        evidence_class="measured",
        geometry=_GEOM,
        area_km2=42.5,
        confidence=0.75,
        status="candidate",
    )


@pytest.fixture
def sample_prep() -> PreprocessedScene:
    rng = np.random.default_rng(1)
    vv = rng.uniform(-25.0, -10.0, (100, 100)).astype(np.float32)
    vh = rng.uniform(-30.0, -15.0, (100, 100)).astype(np.float32)
    return PreprocessedScene(
        scene_id="scene-export-001",
        vv_db=vv,
        vh_db=vh,
        transform=_TRANSFORM,
    )


# ── GeoJSON ───────────────────────────────────────────────────────────────────


def test_export_geojson_creates_file(
    tmp_path: Path, sample_run: AnalysisRun, sample_obs: Observation
) -> None:
    path = tmp_path / "obs.geojson"
    export_geojson([sample_obs], sample_run, path)
    assert path.exists()


def test_export_geojson_valid_feature_collection(
    tmp_path: Path, sample_run: AnalysisRun, sample_obs: Observation
) -> None:
    path = tmp_path / "obs.geojson"
    export_geojson([sample_obs], sample_run, path)
    data = json.loads(path.read_text())
    assert data["type"] == "FeatureCollection"


def test_export_geojson_feature_count(
    tmp_path: Path, sample_run: AnalysisRun, sample_obs: Observation
) -> None:
    path = tmp_path / "obs.geojson"
    export_geojson([sample_obs], sample_run, path)
    data = json.loads(path.read_text())
    assert len(data["features"]) == 1


def test_export_geojson_empty_observations(tmp_path: Path, sample_run: AnalysisRun) -> None:
    path = tmp_path / "obs.geojson"
    export_geojson([], sample_run, path)
    data = json.loads(path.read_text())
    assert data["type"] == "FeatureCollection"
    assert data["features"] == []


def test_export_geojson_feature_obs_type(
    tmp_path: Path, sample_run: AnalysisRun, sample_obs: Observation
) -> None:
    path = tmp_path / "obs.geojson"
    export_geojson([sample_obs], sample_run, path)
    data = json.loads(path.read_text())
    assert data["features"][0]["properties"]["obs_type"] == "oil_slick"


def test_export_geojson_feature_evidence_class(
    tmp_path: Path, sample_run: AnalysisRun, sample_obs: Observation
) -> None:
    """INV-3: evidence_class must round-trip through the exported GeoJSON."""
    path = tmp_path / "obs.geojson"
    export_geojson([sample_obs], sample_run, path)
    data = json.loads(path.read_text())
    assert data["features"][0]["properties"]["evidence_class"] == "measured"


def test_export_geojson_feature_area_km2(
    tmp_path: Path, sample_run: AnalysisRun, sample_obs: Observation
) -> None:
    path = tmp_path / "obs.geojson"
    export_geojson([sample_obs], sample_run, path)
    data = json.loads(path.read_text())
    assert data["features"][0]["properties"]["area_km2"] == pytest.approx(42.5)


def test_export_geojson_collection_properties(
    tmp_path: Path, sample_run: AnalysisRun, sample_obs: Observation
) -> None:
    path = tmp_path / "obs.geojson"
    export_geojson([sample_obs], sample_run, path)
    data = json.loads(path.read_text())
    assert data["properties"]["analysis_run_id"] == "run-export-001"
    assert data["properties"]["domain_id"] == "marine_oil"


# ── PNG ───────────────────────────────────────────────────────────────────────


def test_export_png_creates_file(
    tmp_path: Path, sample_prep: PreprocessedScene, sample_obs: Observation
) -> None:
    path = tmp_path / "raster.png"
    export_png(sample_prep, [sample_obs], path)
    assert path.exists()


def test_export_png_is_nonempty(
    tmp_path: Path, sample_prep: PreprocessedScene, sample_obs: Observation
) -> None:
    path = tmp_path / "raster.png"
    export_png(sample_prep, [sample_obs], path)
    assert path.stat().st_size > 1000  # a real PNG is at least a few KB


def test_export_png_no_observations(tmp_path: Path, sample_prep: PreprocessedScene) -> None:
    path = tmp_path / "raster_empty.png"
    export_png(sample_prep, [], path)
    assert path.exists()
    assert path.stat().st_size > 1000


# ── export_products ────────────────────────────────────────────────────────────


def test_export_products_creates_both_artifacts(
    tmp_path: Path,
    sample_run: AnalysisRun,
    sample_obs: Observation,
    sample_prep: PreprocessedScene,
) -> None:
    artifacts = export_products([sample_obs], sample_run, sample_prep, tmp_path / "out")
    assert artifacts["geojson"].exists()
    assert artifacts["png"].exists()


def test_export_products_returns_geojson_and_png_keys(
    tmp_path: Path,
    sample_run: AnalysisRun,
    sample_obs: Observation,
    sample_prep: PreprocessedScene,
) -> None:
    artifacts = export_products([sample_obs], sample_run, sample_prep, tmp_path / "out")
    assert set(artifacts.keys()) == {"geojson", "png", "metadata"}


def test_export_products_creates_output_dir(
    tmp_path: Path,
    sample_run: AnalysisRun,
    sample_obs: Observation,
    sample_prep: PreprocessedScene,
) -> None:
    nested = tmp_path / "deep" / "nested" / "dir"
    export_products([sample_obs], sample_run, sample_prep, nested)
    assert nested.exists()
