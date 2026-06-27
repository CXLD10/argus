"""F-011 tests: oil trajectory runner, oil type registry, GPL isolation."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from argus.predict.oil_trajectory.oil_types import (
    OilType,
    OilTypeNotFoundError,
    OilTypeRegistry,
    OilTypeRequiredError,
    load_oil_types,
)
from argus.predict.oil_trajectory.runner import SimInput, run_simulation

_REPO_ROOT = Path(__file__).parent.parent
_OIL_TYPES_YAML = _REPO_ROOT / "config" / "oil_types.yaml"

_SEED_GEOM = {"type": "Point", "coordinates": [-61.0, 11.0]}

_MOCK_FRAMES: list[dict[str, Any]] = [
    {
        "valid_at": "2024-02-07T01:00:00",
        "particle_count": 1000,
        "footprint": {
            "type": "Polygon",
            "coordinates": [
                [[-61.1, 11.0], [-60.9, 11.0], [-60.9, 11.2], [-61.1, 11.2], [-61.1, 11.0]]
            ],
        },
        "stats": {"mean_lon": -61.0, "mean_lat": 11.1},
    },
    {
        "valid_at": "2024-02-07T02:00:00",
        "particle_count": 990,
        "footprint": {
            "type": "Polygon",
            "coordinates": [
                [[-61.2, 11.1], [-61.0, 11.1], [-61.0, 11.3], [-61.2, 11.3], [-61.2, 11.1]]
            ],
        },
        "stats": {"mean_lon": -61.1, "mean_lat": 11.2},
    },
]


# ── OilTypeRegistry ────────────────────────────────────────────────────────────


def test_registry_get_valid_type() -> None:
    reg = OilTypeRegistry([OilType(id="crude_medium", name="Crude", openoil_name="GENERIC CRUDE")])
    ot = reg.get("crude_medium")
    assert ot.id == "crude_medium"


def test_registry_missing_raises_not_found() -> None:
    reg = OilTypeRegistry([OilType(id="crude_medium", name="Crude", openoil_name="GENERIC CRUDE")])
    with pytest.raises(OilTypeNotFoundError, match="not in registry"):
        reg.get("mystery_oil")


def test_registry_not_found_lists_available() -> None:
    reg = OilTypeRegistry([OilType(id="crude_medium", name="Crude", openoil_name="GENERIC CRUDE")])
    with pytest.raises(OilTypeNotFoundError, match="crude_medium"):
        reg.get("unknown")


def test_registry_empty_oil_type_raises_required_error() -> None:
    reg = OilTypeRegistry([OilType(id="crude_medium", name="Crude", openoil_name="GENERIC CRUDE")])
    with pytest.raises(OilTypeRequiredError):
        reg.get("")


def test_registry_available_ids_sorted() -> None:
    reg = OilTypeRegistry(
        [
            OilType(id="diesel", name="Diesel", openoil_name="DIESEL"),
            OilType(id="crude_medium", name="Crude", openoil_name="GENERIC CRUDE"),
        ]
    )
    assert reg.available_ids == ["crude_medium", "diesel"]


# ── load_oil_types() ──────────────────────────────────────────────────────────


def test_load_oil_types_from_yaml() -> None:
    reg = load_oil_types(_OIL_TYPES_YAML)
    assert "crude_medium" in reg.available_ids


def test_load_oil_types_at_least_three_types() -> None:
    reg = load_oil_types(_OIL_TYPES_YAML)
    assert len(reg.available_ids) >= 3


def test_load_oil_types_crude_medium_has_openoil_name() -> None:
    reg = load_oil_types(_OIL_TYPES_YAML)
    ot = reg.get("crude_medium")
    assert ot.openoil_name


def test_load_oil_types_all_required_ids_present() -> None:
    reg = load_oil_types(_OIL_TYPES_YAML)
    for expected in ("crude_medium", "diesel", "bunker_c"):
        assert expected in reg.available_ids, f"{expected} missing from oil_types.yaml"


# ── run_simulation() — subprocess mocked ─────────────────────────────────────


def _make_sim_input(oil_type: str = "crude_medium") -> SimInput:
    return SimInput(
        oil_type=oil_type,
        seed_geometry=_SEED_GEOM,
        t0="2024-02-07T00:00:00Z",
        duration_hours=24,
        rng_seed=42,
    )


def _mock_subprocess(output_json: str) -> MagicMock:
    """Build a mock for subprocess.run that writes output_json to the --output path."""

    def _side_effect(cmd: list[str], **_: Any) -> subprocess.CompletedProcess:
        out_idx = cmd.index("--output") + 1
        Path(cmd[out_idx]).write_text(output_json)
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

    mock = MagicMock(side_effect=_side_effect)
    return mock


def test_run_simulation_returns_frames() -> None:
    reg = load_oil_types(_OIL_TYPES_YAML)
    with patch("subprocess.run", _mock_subprocess(json.dumps(_MOCK_FRAMES))):
        frames = run_simulation(_make_sim_input(), registry=reg)
    assert len(frames) == 2


def test_run_simulation_frame_has_footprint() -> None:
    reg = load_oil_types(_OIL_TYPES_YAML)
    with patch("subprocess.run", _mock_subprocess(json.dumps(_MOCK_FRAMES))):
        frames = run_simulation(_make_sim_input(), registry=reg)
    assert frames[0]["footprint"]["type"] == "Polygon"


def test_run_simulation_frame_has_valid_at() -> None:
    reg = load_oil_types(_OIL_TYPES_YAML)
    with patch("subprocess.run", _mock_subprocess(json.dumps(_MOCK_FRAMES))):
        frames = run_simulation(_make_sim_input(), registry=reg)
    assert "valid_at" in frames[0]


def test_run_simulation_missing_oil_type_raises() -> None:
    reg = load_oil_types(_OIL_TYPES_YAML)
    with pytest.raises(OilTypeRequiredError):
        run_simulation(_make_sim_input(oil_type=""), registry=reg)


def test_run_simulation_unknown_oil_type_raises() -> None:
    reg = load_oil_types(_OIL_TYPES_YAML)
    with pytest.raises(OilTypeNotFoundError):
        run_simulation(_make_sim_input(oil_type="mystery_slick"), registry=reg)


def test_run_simulation_unknown_lists_available_types() -> None:
    reg = load_oil_types(_OIL_TYPES_YAML)
    with pytest.raises(OilTypeNotFoundError, match="crude_medium"):
        run_simulation(_make_sim_input(oil_type="unknown_type"), registry=reg)


def test_run_simulation_subprocess_failure_raises() -> None:
    reg = load_oil_types(_OIL_TYPES_YAML)

    def _fail(cmd: list[str], **_: Any) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            cmd, returncode=1, stdout="", stderr="opendrift not found"
        )

    with patch("subprocess.run", _fail), pytest.raises(RuntimeError, match="sim_worker exited"):
        run_simulation(_make_sim_input(), registry=reg)


# ── GPL isolation check ───────────────────────────────────────────────────────


def test_gpl_isolation_opendrift_only_in_sim_worker() -> None:
    """grep -r 'import opendrift' argus/ must match only sim_worker.py."""
    argus_dir = _REPO_ROOT / "argus"
    violators = []
    for py_file in argus_dir.rglob("*.py"):
        if "sim_worker" in py_file.name:
            continue
        content = py_file.read_text()
        if "import opendrift" in content:
            violators.append(str(py_file.relative_to(_REPO_ROOT)))
    assert violators == [], f"opendrift imported outside sim_worker: {violators}"


# ── Prediction + ForecastFrame store scaffold ─────────────────────────────────


def test_prediction_store_round_trip(tmp_path: Path) -> None:
    import uuid

    from argus.core.models import Prediction
    from argus.core.store import Store

    store = Store(tmp_path / "argus.db")
    pred = Prediction(
        id=str(uuid.uuid4()),
        predictor_id="oil_trajectory_v1",
        source_obs_ids=["obs-001"],
        kind="trajectory",
        evidence_class="modeled",
        uncertainty={"particle_spread_km": 15.0, "confidence_level": 0.8},
        rng_seed=42,
    )
    store.save_prediction(pred)
    retrieved = store.get_prediction(pred.id)
    assert retrieved is not None
    assert retrieved.predictor_id == "oil_trajectory_v1"
    assert retrieved.uncertainty["particle_spread_km"] == pytest.approx(15.0)
    assert retrieved.rng_seed == 42


def test_forecast_frame_store_round_trip(tmp_path: Path) -> None:
    import uuid
    from datetime import UTC, datetime

    from argus.core.models import ForecastFrame, Prediction
    from argus.core.store import Store

    store = Store(tmp_path / "argus.db")
    pred = Prediction(
        id="pred-001",
        predictor_id="oil_trajectory_v1",
        kind="trajectory",
        uncertainty={"spread_km": 10.0},
        rng_seed=42,
    )
    store.save_prediction(pred)

    frame = ForecastFrame(
        id=str(uuid.uuid4()),
        prediction_id="pred-001",
        valid_at=datetime(2024, 2, 7, 1, 0, tzinfo=UTC),
        footprint=_MOCK_FRAMES[0]["footprint"],
        particle_count=1000,
        stats={"mean_lon": -61.0, "mean_lat": 11.1},
    )
    store.save_forecast_frame(frame)
    frames = store.get_forecast_frames_for_prediction("pred-001")
    assert len(frames) == 1
    assert frames[0].particle_count == 1000
    assert frames[0].footprint["type"] == "Polygon"
