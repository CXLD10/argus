"""F-006: Phase 0 end-to-end offline test.

Threads the full pipeline (AOI → synthetic SAR → preprocess → detect → export)
without any network access. All data is either derived or fixture-based.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from typer.testing import CliRunner

from argus.aoi.loader import load_aoi
from argus.cli import app
from argus.domains.base import Acquisition
from argus.domains.marine_oil.detector import OilDomainV0, make_analysis_run
from argus.export.products import export_products
from argus.preprocess.landmask import GeoTransform
from argus.preprocess.sar import preprocess

_REPO_ROOT = Path(__file__).parent.parent
_AOI_PATH = _REPO_ROOT / "config" / "aois" / "tobago.geojson"


def _make_synthetic_pipeline(tmp_path: Path) -> dict[str, object]:
    """Run the offline pipeline and return all intermediate artifacts."""
    aoi = load_aoi(_AOI_PATH)
    bbox = aoi.bbox

    # Synthetic SAR: uniform background + planted dark blob
    rows, cols = 100, 100
    rng = np.random.default_rng(42)
    vv_linear = rng.uniform(5e-4, 2e-3, (rows, cols)).astype(np.float32)
    vh_linear = rng.uniform(5e-5, 2e-4, (rows, cols)).astype(np.float32)
    vv_linear[35:55, 35:55] = 5e-6  # dark blob
    vh_linear[35:55, 35:55] = 5e-7

    transform = GeoTransform(
        min_lon=bbox[0],
        min_lat=bbox[1],
        max_lon=bbox[2],
        max_lat=bbox[3],
        cols=cols,
        rows=rows,
    )
    land_mask = np.zeros((rows, cols), dtype=bool)
    scene_id = "synthetic-tobago-2024-02-07"
    prep = preprocess(vv_linear, vh_linear, land_mask, transform, scene_id)

    run_obj = make_analysis_run(aoi.id, scene_id)
    acq = Acquisition(
        scene_id=scene_id,
        source_ref=None,  # type: ignore[arg-type]
        preprocessed=prep,
        attrs={"analysis_run_id": run_obj.id},
    )
    observations = OilDomainV0().analyze(acq)
    artifacts = export_products(observations, run_obj, prep, tmp_path / "output")

    return {
        "aoi": aoi,
        "prep": prep,
        "run": run_obj,
        "observations": observations,
        "artifacts": artifacts,
    }


@pytest.fixture(scope="module")
def pipeline_result(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    tmp = tmp_path_factory.mktemp("e2e")
    return _make_synthetic_pipeline(tmp)


# ── Detection assertions ───────────────────────────────────────────────────────


def test_e2e_detects_at_least_one_observation(pipeline_result: dict[str, object]) -> None:
    observations = pipeline_result["observations"]
    assert isinstance(observations, list)
    assert len(observations) >= 1


def test_e2e_observation_obs_type(pipeline_result: dict[str, object]) -> None:
    observations = pipeline_result["observations"]
    assert all(o.obs_type == "oil_slick" for o in observations)  # type: ignore[union-attr]


def test_e2e_observation_evidence_class_measured(pipeline_result: dict[str, object]) -> None:
    """INV-3: every oil-slick Observation must carry evidence_class='measured'."""
    observations = pipeline_result["observations"]
    assert all(o.evidence_class == "measured" for o in observations)  # type: ignore[union-attr]


def test_e2e_observation_area_positive(pipeline_result: dict[str, object]) -> None:
    observations = pipeline_result["observations"]
    assert all(o.area_km2 > 0 for o in observations)  # type: ignore[union-attr]


# ── Artifact assertions ────────────────────────────────────────────────────────


def test_e2e_geojson_artifact_exists(pipeline_result: dict[str, object]) -> None:
    artifacts = pipeline_result["artifacts"]
    assert artifacts["geojson"].exists()  # type: ignore[union-attr]


def test_e2e_png_artifact_exists(pipeline_result: dict[str, object]) -> None:
    artifacts = pipeline_result["artifacts"]
    assert artifacts["png"].exists()  # type: ignore[union-attr]


def test_e2e_geojson_is_valid_feature_collection(pipeline_result: dict[str, object]) -> None:
    artifacts = pipeline_result["artifacts"]
    data = json.loads(artifacts["geojson"].read_text())  # type: ignore[union-attr]
    assert data["type"] == "FeatureCollection"


def test_e2e_geojson_has_at_least_one_feature(pipeline_result: dict[str, object]) -> None:
    artifacts = pipeline_result["artifacts"]
    data = json.loads(artifacts["geojson"].read_text())  # type: ignore[union-attr]
    assert len(data["features"]) >= 1


def test_e2e_png_is_nonempty(pipeline_result: dict[str, object]) -> None:
    artifacts = pipeline_result["artifacts"]
    assert artifacts["png"].stat().st_size > 1000  # type: ignore[union-attr]


# ── CLI ───────────────────────────────────────────────────────────────────────


def test_e2e_cli_run_offline_exits_zero(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "run",
            "--aoi",
            "tobago",
            "--since",
            "2024-02-07",
            "--output-dir",
            str(tmp_path / "cli_out"),
            "--config-dir",
            str(_REPO_ROOT / "config"),
        ],
    )
    assert result.exit_code == 0, f"CLI failed:\n{result.output}"


def test_e2e_cli_run_reports_detections(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "run",
            "--aoi",
            "tobago",
            "--since",
            "2024-02-07",
            "--output-dir",
            str(tmp_path / "cli_out"),
            "--config-dir",
            str(_REPO_ROOT / "config"),
        ],
    )
    assert "detected:" in result.output


def test_e2e_cli_run_creates_geojson(tmp_path: Path) -> None:
    out_dir = tmp_path / "cli_out"
    runner = CliRunner()
    runner.invoke(
        app,
        [
            "run",
            "--aoi",
            "tobago",
            "--since",
            "2024-02-07",
            "--output-dir",
            str(out_dir),
            "--config-dir",
            str(_REPO_ROOT / "config"),
        ],
    )
    geojsons = list((out_dir / "tobago" / "2024-02-07").glob("*.geojson"))
    assert len(geojsons) == 1


def test_e2e_cli_run_creates_png(tmp_path: Path) -> None:
    out_dir = tmp_path / "cli_out"
    runner = CliRunner()
    runner.invoke(
        app,
        [
            "run",
            "--aoi",
            "tobago",
            "--since",
            "2024-02-07",
            "--output-dir",
            str(out_dir),
            "--config-dir",
            str(_REPO_ROOT / "config"),
        ],
    )
    pngs = list((out_dir / "tobago" / "2024-02-07").glob("*.png"))
    assert len(pngs) == 1


def test_e2e_cli_missing_aoi_exits_nonzero(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "run",
            "--aoi",
            "nonexistent",
            "--since",
            "2024-02-07",
            "--output-dir",
            str(tmp_path),
            "--config-dir",
            str(_REPO_ROOT / "config"),
        ],
    )
    assert result.exit_code != 0
