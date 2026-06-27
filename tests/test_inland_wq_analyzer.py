"""F-026 tests: InlandWqDomain spectral analysis and resolution gate."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest

from argus.aoi.loader import BelowResolutionError
from argus.core.models import MonitorTarget
from argus.domains.base import Acquisition
from argus.domains.inland_wq.analyzer import InlandWqDomain
from argus.preprocess.landmask import GeoTransform
from argus.preprocess.optical import OpticalScene

_FIXTURE_DIR = Path(__file__).parent / "fixtures"
_S2_NPY = _FIXTURE_DIR / "s2_water_body_100x100.npy"

_LAKE_GEOMETRY = {
    "type": "Polygon",
    "coordinates": [
        [[-60.503, 10.497], [-60.5, 10.497], [-60.5, 10.5], [-60.503, 10.5], [-60.503, 10.497]]
    ],
}

_ELIGIBLE_TARGET = MonitorTarget(
    id="reference_lake",
    aoi_id="reference_region",
    kind="water_body",
    name="Reference Lake",
    geometry=_LAKE_GEOMETRY,
    domains=["inland_wq"],
    resolution_status="eligible",
    calibration_state="uncalibrated",
)

_BELOW_RES_TARGET = MonitorTarget(
    id="tiny_pond",
    aoi_id="reference_region",
    kind="water_body",
    name="Tiny Pond",
    geometry=_LAKE_GEOMETRY,
    domains=["inland_wq"],
    resolution_status="below_resolution",
    calibration_state=None,
)

_T0 = datetime(2024, 2, 7, tzinfo=UTC)
_T1 = datetime(2024, 2, 9, tzinfo=UTC)


def _make_acquisition(target: MonitorTarget) -> Acquisition:
    """Build an offline Acquisition from the S2 fixture for the given target."""
    raw = np.load(_S2_NPY)
    band_names = ["B2", "B3", "B4", "B5", "B8A", "B11"]
    bands = {name: raw[i] for i, name in enumerate(band_names)}
    scene = OpticalScene(
        bands=bands,
        transform=GeoTransform(min_lon=-60.503, min_lat=10.497, max_lon=-60.5, max_lat=10.5, cols=100, rows=100),
        source="s2",
    )
    return Acquisition(
        scene_id="test_scene_001",
        source_ref=None,  # type: ignore[arg-type]  # not needed in offline tests
        preprocessed=scene,
        attrs={"target": target, "analysis_run_id": "run_abc"},
    )


# ── Resolution gate (AC4) ─────────────────────────────────────────────────────


def test_search_below_resolution_raises_before_cdse() -> None:
    domain = InlandWqDomain()  # no auth — offline mode
    with pytest.raises(BelowResolutionError):
        domain.search(_BELOW_RES_TARGET, _T0, _T1)


def test_search_eligible_offline_returns_empty() -> None:
    domain = InlandWqDomain()  # no auth
    refs = domain.search(_ELIGIBLE_TARGET, _T0, _T1)
    assert refs == []


# ── Spectral index values (AC1) ───────────────────────────────────────────────


def test_analyze_ndci_mean_within_tolerance() -> None:
    """Fixture NDCI mean should be ≈ 0.128 (pre-computed from fixture)."""
    domain = InlandWqDomain()
    obs = domain.analyze(_make_acquisition(_ELIGIBLE_TARGET))
    chl_obs = next(o for o in obs if o.obs_type == "chlorophyll_a")
    assert chl_obs.value == pytest.approx(0.1279, abs=0.01)


def test_analyze_ndti_mean_within_tolerance() -> None:
    """Fixture NDTI mean should be ≈ −0.200."""
    domain = InlandWqDomain()
    obs = domain.analyze(_make_acquisition(_ELIGIBLE_TARGET))
    turb_obs = next(o for o in obs if o.obs_type == "turbidity")
    assert turb_obs.value == pytest.approx(-0.2004, abs=0.01)


def test_analyze_ndci_algae_patch_is_elevated() -> None:
    """The algae patch at rows 20:40, cols 20:40 should have NDCI ≈ 0.53."""
    raw = np.load(_S2_NPY)
    b5_patch = raw[3, 20:40, 20:40]
    b4_patch = raw[2, 20:40, 20:40]
    ndci_patch = (b5_patch - b4_patch) / (b5_patch + b4_patch)
    assert float(ndci_patch.mean()) == pytest.approx(0.529, abs=0.01)


# ── Evidence class (AC2) ─────────────────────────────────────────────────────


def test_analyze_measured_obs_types_have_evidence_class_measured() -> None:
    domain = InlandWqDomain()
    obs = domain.analyze(_make_acquisition(_ELIGIBLE_TARGET))
    measured_types = {"chlorophyll_a", "turbidity", "cdom"}
    for o in obs:
        if o.obs_type in measured_types:
            assert o.evidence_class == "measured", f"{o.obs_type} should be measured"


def test_analyze_bloom_presence_has_evidence_class_inferred() -> None:
    domain = InlandWqDomain()
    obs = domain.analyze(_make_acquisition(_ELIGIBLE_TARGET))
    bloom_obs = [o for o in obs if o.obs_type == "bloom_presence"]
    assert len(bloom_obs) == 1
    assert bloom_obs[0].evidence_class == "inferred"


def test_analyze_fixture_produces_bloom_presence() -> None:
    """Fixture with elevated algae patch must trigger bloom_presence."""
    domain = InlandWqDomain()
    obs = domain.analyze(_make_acquisition(_ELIGIBLE_TARGET))
    types = {o.obs_type for o in obs}
    assert "bloom_presence" in types


# ── Calibration state (AC3) ───────────────────────────────────────────────────


def test_analyze_calibration_state_matches_target() -> None:
    domain = InlandWqDomain()
    obs = domain.analyze(_make_acquisition(_ELIGIBLE_TARGET))
    for o in obs:
        assert o.attrs["calibration_state"] == _ELIGIBLE_TARGET.calibration_state


def test_analyze_calibration_state_none_when_no_target() -> None:
    """Without a MonitorTarget in attrs, calibration_state should be None."""
    raw = np.load(_S2_NPY)
    bands = {n: raw[i] for i, n in enumerate(["B2", "B3", "B4", "B5", "B8A", "B11"])}
    scene = OpticalScene(
        bands=bands,
        transform=GeoTransform(min_lon=0.0, min_lat=0.0, max_lon=1.0, max_lat=1.0, cols=100, rows=100),
        source="s2",
    )
    acq = Acquisition(scene_id="s", source_ref=None, preprocessed=scene, attrs={})  # type: ignore[arg-type]
    domain = InlandWqDomain()
    obs = domain.analyze(acq)
    for o in obs:
        assert o.attrs["calibration_state"] is None


# ── Domain identity ───────────────────────────────────────────────────────────


def test_domain_id_is_inland_wq() -> None:
    domain = InlandWqDomain()
    assert domain.domain_id == "inland_wq"


def test_analyze_all_obs_have_domain_set() -> None:
    domain = InlandWqDomain()
    obs = domain.analyze(_make_acquisition(_ELIGIBLE_TARGET))
    assert all(o.domain == "inland_wq" for o in obs)


def test_analyze_all_obs_have_scene_id() -> None:
    domain = InlandWqDomain()
    obs = domain.analyze(_make_acquisition(_ELIGIBLE_TARGET))
    assert all(o.scene_id == "test_scene_001" for o in obs)


def test_analyze_produces_three_measured_observations() -> None:
    """Fixture with all 6 S2 bands should yield chlorophyll_a, turbidity, cdom."""
    domain = InlandWqDomain()
    obs = domain.analyze(_make_acquisition(_ELIGIBLE_TARGET))
    measured = [o for o in obs if o.evidence_class == "measured"]
    types = {o.obs_type for o in measured}
    assert types == {"chlorophyll_a", "turbidity", "cdom"}


def test_analyze_no_bloom_for_low_ndci_scene() -> None:
    """A scene with uniformly low NDCI must not produce bloom_presence."""
    bands = {
        "B2": np.full((50, 50), 0.05, dtype=np.float32),
        "B3": np.full((50, 50), 0.06, dtype=np.float32),
        "B4": np.full((50, 50), 0.04, dtype=np.float32),
        "B5": np.full((50, 50), 0.045, dtype=np.float32),  # NDCI ≈ 0.06
    }
    scene = OpticalScene(
        bands=bands,
        transform=GeoTransform(min_lon=0.0, min_lat=0.0, max_lon=1.0, max_lat=1.0, cols=50, rows=50),
        source="s2",
    )
    acq = Acquisition(
        scene_id="low_ndci",
        source_ref=None,  # type: ignore[arg-type]
        preprocessed=scene,
        attrs={"target": _ELIGIBLE_TARGET},
    )
    domain = InlandWqDomain()
    obs = domain.analyze(acq)
    types = {o.obs_type for o in obs}
    assert "bloom_presence" not in types


def test_analyze_none_preprocessed_returns_empty() -> None:
    acq = Acquisition(scene_id="s", source_ref=None, preprocessed=None, attrs={})  # type: ignore[arg-type]
    domain = InlandWqDomain()
    assert domain.analyze(acq) == []


def test_acquire_raises_not_implemented() -> None:
    domain = InlandWqDomain()
    with pytest.raises(NotImplementedError):
        domain.acquire(None)  # type: ignore[arg-type]
