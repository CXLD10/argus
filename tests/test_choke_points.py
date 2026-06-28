"""Tests for F-040: D4 Hydro Choke Points domain.

All tests are offline (INV-7).  Synthetic DEMs are used — no live Copernicus DEM fetch.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest

from argus.core.models import ChokePoint, MonitorTarget
from argus.core.store import Store
from argus.domains.base import Acquisition
from argus.domains.hydro_chokepoints.analyzer import HydroChokepointsDomain
from argus.domains.hydro_chokepoints.constriction import (
    candidates_to_choke_points,
    extract_choke_points,
    score_constriction,
)
from argus.domains.hydro_chokepoints.dem_processor import (
    compute_flow_accumulation,
    compute_flow_direction,
    upstream_area_km2,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def funnel_dem() -> np.ndarray:
    """5×5 synthetic funnel DEM that drains to the centre-bottom cell (row 4, col 2).

    Row 0 is highest (elevation 9–10), row 4 is lowest (elevation 1).
    All columns slope toward col 2.
    """
    return np.array(
        [
            [10.0, 9.5, 9.0, 9.5, 10.0],
            [8.0,  7.5, 7.0, 7.5,  8.0],
            [6.0,  5.5, 5.0, 5.5,  6.0],
            [4.0,  3.5, 3.0, 3.5,  4.0],
            [2.0,  1.5, 1.0, 1.5,  2.0],
        ],
        dtype=np.float64,
    )


@pytest.fixture()
def flat_dem() -> np.ndarray:
    """3×3 flat DEM — all cells at the same elevation (all sinks)."""
    return np.ones((3, 3), dtype=np.float64)


@pytest.fixture()
def valley_dem() -> np.ndarray:
    """5×5 valley DEM that drains linearly down column 2 (centre column).

    All rows slope inward: high edges, low centre.
    """
    dem = np.array(
        [
            [8.0, 5.0, 2.0, 5.0, 8.0],
            [8.0, 5.0, 2.0, 5.0, 8.0],
            [8.0, 5.0, 2.0, 5.0, 8.0],
            [8.0, 5.0, 1.0, 5.0, 8.0],
            [8.0, 5.0, 0.5, 5.0, 8.0],
        ],
        dtype=np.float64,
    )
    return dem


@pytest.fixture()
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "argus.db")


@pytest.fixture()
def domain() -> HydroChokepointsDomain:
    return HydroChokepointsDomain()


@pytest.fixture()
def simple_target() -> MonitorTarget:
    return MonitorTarget(
        id="test_target",
        aoi_id="test_aoi",
        kind="region",
        name="Test Region",
        geometry={
            "type": "Polygon",
            "coordinates": [
                [
                    [-61.5, 11.0],
                    [-61.0, 11.0],
                    [-61.0, 11.5],
                    [-61.5, 11.5],
                    [-61.5, 11.0],
                ]
            ],
        },
        domains=["hydro_chokepoints"],
    )


# ── dem_processor: flow direction ─────────────────────────────────────────────


def test_flow_direction_shape_matches_dem(funnel_dem: np.ndarray) -> None:
    fdir = compute_flow_direction(funnel_dem)
    assert fdir.shape == funnel_dem.shape


def test_flow_direction_dtype_is_int8(funnel_dem: np.ndarray) -> None:
    fdir = compute_flow_direction(funnel_dem)
    assert fdir.dtype == np.int8


def test_flow_direction_flat_dem_all_sinks(flat_dem: np.ndarray) -> None:
    fdir = compute_flow_direction(flat_dem)
    # All cells on flat surface have no downslope neighbour → all -1
    assert np.all(fdir == -1)


def test_flow_direction_funnel_converges_at_bottom(funnel_dem: np.ndarray) -> None:
    fdir = compute_flow_direction(funnel_dem)
    rows, cols = funnel_dem.shape
    # Bottom-row, centre cell is the global minimum → must be a sink (-1)
    assert fdir[rows - 1, cols // 2] == -1


def test_flow_direction_nan_cells_become_minus_one() -> None:
    dem = np.array([[5.0, np.nan], [3.0, 2.0]], dtype=np.float64)
    fdir = compute_flow_direction(dem)
    assert fdir[0, 1] == -1


def test_flow_direction_valid_range(funnel_dem: np.ndarray) -> None:
    fdir = compute_flow_direction(funnel_dem)
    # Values must be -1 (sink) or 0–7 (D8 direction)
    assert np.all((fdir >= -1) & (fdir <= 7))


# ── dem_processor: flow accumulation ─────────────────────────────────────────


def test_flow_accumulation_shape_matches(funnel_dem: np.ndarray) -> None:
    fdir = compute_flow_direction(funnel_dem)
    facc = compute_flow_accumulation(funnel_dem, fdir)
    assert facc.shape == funnel_dem.shape


def test_flow_accumulation_dtype_is_int64(funnel_dem: np.ndarray) -> None:
    fdir = compute_flow_direction(funnel_dem)
    facc = compute_flow_accumulation(funnel_dem, fdir)
    assert facc.dtype == np.int64


def test_flow_accumulation_non_negative(funnel_dem: np.ndarray) -> None:
    fdir = compute_flow_direction(funnel_dem)
    facc = compute_flow_accumulation(funnel_dem, fdir)
    assert np.all(facc >= 0)


def test_flow_accumulation_funnel_maximum_at_outlet(funnel_dem: np.ndarray) -> None:
    """The global outlet (lowest point) should have the highest accumulation."""
    fdir = compute_flow_direction(funnel_dem)
    facc = compute_flow_accumulation(funnel_dem, fdir)
    rows, cols = funnel_dem.shape
    outlet_row, outlet_col = rows - 1, cols // 2
    assert facc[outlet_row, outlet_col] == np.max(facc)


def test_flow_accumulation_source_cells_are_zero(funnel_dem: np.ndarray) -> None:
    """Corner cells of the funnel have no upstream contributors → accumulation = 0."""
    fdir = compute_flow_direction(funnel_dem)
    facc = compute_flow_accumulation(funnel_dem, fdir)
    # Top-left corner is a peak with no upstream flow
    assert facc[0, 0] == 0


def test_upstream_area_km2_conversion() -> None:
    # 100 cells × (30m)² = 90,000 m² = 0.09 km²
    result = upstream_area_km2(100, cell_size_m=30.0)
    assert abs(result - 0.09) < 1e-9


def test_upstream_area_km2_zero_cells() -> None:
    assert upstream_area_km2(0, cell_size_m=30.0) == 0.0


# ── constriction: score_constriction ─────────────────────────────────────────


def test_score_constriction_range(funnel_dem: np.ndarray) -> None:
    fdir = compute_flow_direction(funnel_dem)
    facc = compute_flow_accumulation(funnel_dem, fdir)
    scores = score_constriction(facc)
    assert np.all(scores >= 0.0)
    assert np.all(scores <= 1.0)


def test_score_constriction_max_is_one(funnel_dem: np.ndarray) -> None:
    fdir = compute_flow_direction(funnel_dem)
    facc = compute_flow_accumulation(funnel_dem, fdir)
    scores = score_constriction(facc)
    assert float(np.max(scores)) == pytest.approx(1.0)


def test_score_constriction_flat_raster_returns_zeros() -> None:
    facc = np.zeros((3, 3), dtype=np.int64)
    scores = score_constriction(facc)
    assert np.all(scores == 0.0)


def test_score_constriction_shape_preserved(funnel_dem: np.ndarray) -> None:
    fdir = compute_flow_direction(funnel_dem)
    facc = compute_flow_accumulation(funnel_dem, fdir)
    scores = score_constriction(facc)
    assert scores.shape == funnel_dem.shape


# ── constriction: extract_choke_points ────────────────────────────────────────


def test_extract_choke_points_returns_list(funnel_dem: np.ndarray) -> None:
    fdir = compute_flow_direction(funnel_dem)
    facc = compute_flow_accumulation(funnel_dem, fdir)
    scores = score_constriction(facc)
    result = extract_choke_points(
        facc, scores, 30.0,
        min_upstream_area_km2=0.0,
        min_constriction_score=0.0,
        max_candidates=100,
    )
    assert isinstance(result, list)


def test_extract_choke_points_respects_max_candidates(funnel_dem: np.ndarray) -> None:
    fdir = compute_flow_direction(funnel_dem)
    facc = compute_flow_accumulation(funnel_dem, fdir)
    scores = score_constriction(facc)
    result = extract_choke_points(
        facc, scores, 30.0,
        min_upstream_area_km2=0.0,
        min_constriction_score=0.0,
        max_candidates=3,
    )
    assert len(result) <= 3


def test_extract_choke_points_sorted_descending(funnel_dem: np.ndarray) -> None:
    fdir = compute_flow_direction(funnel_dem)
    facc = compute_flow_accumulation(funnel_dem, fdir)
    scores = score_constriction(facc)
    result = extract_choke_points(
        facc, scores, 30.0,
        min_upstream_area_km2=0.0,
        min_constriction_score=0.0,
        max_candidates=100,
    )
    for a, b in zip(result, result[1:], strict=False):
        assert a.constriction_score >= b.constriction_score


def test_extract_choke_points_area_threshold_filters(funnel_dem: np.ndarray) -> None:
    """Setting a very high area threshold should return no candidates."""
    fdir = compute_flow_direction(funnel_dem)
    facc = compute_flow_accumulation(funnel_dem, fdir)
    scores = score_constriction(facc)
    result = extract_choke_points(
        facc, scores, 30.0,
        min_upstream_area_km2=9999.0,  # impossible threshold
        min_constriction_score=0.0,
        max_candidates=100,
    )
    assert len(result) == 0


def test_extract_choke_points_score_threshold_filters(funnel_dem: np.ndarray) -> None:
    fdir = compute_flow_direction(funnel_dem)
    facc = compute_flow_accumulation(funnel_dem, fdir)
    scores = score_constriction(facc)
    result = extract_choke_points(
        facc, scores, 30.0,
        min_upstream_area_km2=0.0,
        min_constriction_score=2.0,  # > 1.0 → nothing qualifies
        max_candidates=100,
    )
    assert len(result) == 0


# ── constriction: candidates_to_choke_points ─────────────────────────────────


def test_candidates_to_choke_points_returns_choke_point_models(
    funnel_dem: np.ndarray,
) -> None:
    fdir = compute_flow_direction(funnel_dem)
    facc = compute_flow_accumulation(funnel_dem, fdir)
    scores = score_constriction(facc)
    candidates = extract_choke_points(
        facc, scores, 30.0,
        min_upstream_area_km2=0.0,
        min_constriction_score=0.5,
        max_candidates=5,
    )
    cps = candidates_to_choke_points(
        candidates,
        "test_aoi",
        origin_lon=-61.5,
        origin_lat=11.5,
        cell_size_deg=0.1,
        dem_source="cop_glo30",
    )
    assert all(isinstance(cp, ChokePoint) for cp in cps)


def test_candidates_evidence_class_always_inferred(funnel_dem: np.ndarray) -> None:
    fdir = compute_flow_direction(funnel_dem)
    facc = compute_flow_accumulation(funnel_dem, fdir)
    scores = score_constriction(facc)
    candidates = extract_choke_points(
        facc, scores, 30.0,
        min_upstream_area_km2=0.0,
        min_constriction_score=0.0,
        max_candidates=10,
    )
    cps = candidates_to_choke_points(
        candidates,
        "test_aoi",
        origin_lon=-61.5,
        origin_lat=11.5,
        cell_size_deg=0.1,
    )
    for cp in cps:
        assert cp.evidence_class == "inferred", "INV-3 violated: choke_point must be 'inferred'"


def test_candidates_location_is_geojson_point(funnel_dem: np.ndarray) -> None:
    fdir = compute_flow_direction(funnel_dem)
    facc = compute_flow_accumulation(funnel_dem, fdir)
    scores = score_constriction(facc)
    candidates = extract_choke_points(
        facc, scores, 30.0,
        min_upstream_area_km2=0.0,
        min_constriction_score=0.5,
        max_candidates=3,
    )
    cps = candidates_to_choke_points(
        candidates, "test_aoi", origin_lon=0.0, origin_lat=1.0, cell_size_deg=0.1
    )
    for cp in cps:
        assert cp.location["type"] == "Point"
        assert len(cp.location["coordinates"]) == 2


# ── Domain.search ─────────────────────────────────────────────────────────────


def test_search_returns_one_source_ref(
    domain: HydroChokepointsDomain, simple_target: MonitorTarget
) -> None:
    t0 = datetime(2024, 1, 1, tzinfo=UTC)
    t1 = datetime(2024, 1, 2, tzinfo=UTC)
    refs = domain.search(simple_target, t0, t1)
    assert len(refs) == 1


def test_search_source_ref_product_id_stable(
    domain: HydroChokepointsDomain, simple_target: MonitorTarget
) -> None:
    t0 = datetime(2024, 1, 1, tzinfo=UTC)
    t1 = datetime(2024, 1, 2, tzinfo=UTC)
    ref1 = domain.search(simple_target, t0, t1)[0]
    ref2 = domain.search(simple_target, t0, t1)[0]
    assert ref1.product_id == ref2.product_id


def test_search_source_ref_collection(
    domain: HydroChokepointsDomain, simple_target: MonitorTarget
) -> None:
    t0 = datetime(2024, 1, 1, tzinfo=UTC)
    t1 = datetime(2024, 1, 2, tzinfo=UTC)
    ref = domain.search(simple_target, t0, t1)[0]
    assert ref.collection == "COP-DEM_GLO-30"


def test_search_source_ref_has_bbox_in_attrs(
    domain: HydroChokepointsDomain, simple_target: MonitorTarget
) -> None:
    t0 = datetime(2024, 1, 1, tzinfo=UTC)
    t1 = datetime(2024, 1, 2, tzinfo=UTC)
    ref = domain.search(simple_target, t0, t1)[0]
    assert "bbox" in ref.attrs
    assert len(ref.attrs["bbox"]) == 4


# ── Domain.acquire ────────────────────────────────────────────────────────────


def test_acquire_returns_acquisition(
    domain: HydroChokepointsDomain, simple_target: MonitorTarget, funnel_dem: np.ndarray
) -> None:
    t0 = datetime(2024, 1, 1, tzinfo=UTC)
    t1 = datetime(2024, 1, 2, tzinfo=UTC)
    ref = domain.search(simple_target, t0, t1)[0]
    ref.attrs["dem_array"] = funnel_dem
    acq = domain.acquire(ref)
    assert isinstance(acq, Acquisition)


def test_acquire_preprocessed_is_dem_array(
    domain: HydroChokepointsDomain, simple_target: MonitorTarget, funnel_dem: np.ndarray
) -> None:
    t0 = datetime(2024, 1, 1, tzinfo=UTC)
    t1 = datetime(2024, 1, 2, tzinfo=UTC)
    ref = domain.search(simple_target, t0, t1)[0]
    ref.attrs["dem_array"] = funnel_dem
    acq = domain.acquire(ref)
    assert isinstance(acq.preprocessed, np.ndarray)
    assert acq.preprocessed.shape == funnel_dem.shape


def test_acquire_no_dem_array_preprocessed_is_none(
    domain: HydroChokepointsDomain, simple_target: MonitorTarget
) -> None:
    t0 = datetime(2024, 1, 1, tzinfo=UTC)
    t1 = datetime(2024, 1, 2, tzinfo=UTC)
    ref = domain.search(simple_target, t0, t1)[0]
    acq = domain.acquire(ref)
    assert acq.preprocessed is None


def test_acquire_invalid_type_raises(
    domain: HydroChokepointsDomain, simple_target: MonitorTarget
) -> None:
    t0 = datetime(2024, 1, 1, tzinfo=UTC)
    t1 = datetime(2024, 1, 2, tzinfo=UTC)
    ref = domain.search(simple_target, t0, t1)[0]
    ref.attrs["dem_array"] = [[1, 2], [3, 4]]  # list, not ndarray
    with pytest.raises(TypeError, match="numpy ndarray"):
        domain.acquire(ref)


# ── Domain.analyze ────────────────────────────────────────────────────────────


def test_analyze_returns_list(
    domain: HydroChokepointsDomain, simple_target: MonitorTarget, funnel_dem: np.ndarray
) -> None:
    t0 = datetime(2024, 1, 1, tzinfo=UTC)
    t1 = datetime(2024, 1, 2, tzinfo=UTC)
    ref = domain.search(simple_target, t0, t1)[0]
    ref.attrs["dem_array"] = funnel_dem
    ref.attrs["aoi_id"] = "test_aoi"
    ref.attrs["min_constriction_score"] = 0.5
    acq = domain.acquire(ref)
    observations = domain.analyze(acq)
    assert isinstance(observations, list)


def test_analyze_obs_type_is_choke_point(
    domain: HydroChokepointsDomain, simple_target: MonitorTarget, funnel_dem: np.ndarray
) -> None:
    t0 = datetime(2024, 1, 1, tzinfo=UTC)
    t1 = datetime(2024, 1, 2, tzinfo=UTC)
    ref = domain.search(simple_target, t0, t1)[0]
    ref.attrs["dem_array"] = funnel_dem
    ref.attrs["min_constriction_score"] = 0.0
    ref.attrs["min_upstream_area_km2"] = 0.0
    acq = domain.acquire(ref)
    observations = domain.analyze(acq)
    assert len(observations) > 0
    for obs in observations:
        assert obs.obs_type == "choke_point"


def test_analyze_evidence_class_is_inferred(
    domain: HydroChokepointsDomain, simple_target: MonitorTarget, funnel_dem: np.ndarray
) -> None:
    """INV-3: choke_point observations must be evidence_class='inferred'."""
    t0 = datetime(2024, 1, 1, tzinfo=UTC)
    t1 = datetime(2024, 1, 2, tzinfo=UTC)
    ref = domain.search(simple_target, t0, t1)[0]
    ref.attrs["dem_array"] = funnel_dem
    ref.attrs["min_constriction_score"] = 0.0
    ref.attrs["min_upstream_area_km2"] = 0.0
    acq = domain.acquire(ref)
    for obs in domain.analyze(acq):
        assert obs.evidence_class == "inferred", "INV-3 violated"


def test_analyze_no_dem_raises_value_error(
    domain: HydroChokepointsDomain, simple_target: MonitorTarget
) -> None:
    t0 = datetime(2024, 1, 1, tzinfo=UTC)
    t1 = datetime(2024, 1, 2, tzinfo=UTC)
    ref = domain.search(simple_target, t0, t1)[0]
    acq = domain.acquire(ref)  # no dem_array in attrs
    with pytest.raises(ValueError, match="numpy ndarray"):
        domain.analyze(acq)


def test_analyze_1d_dem_raises(
    domain: HydroChokepointsDomain, simple_target: MonitorTarget
) -> None:
    t0 = datetime(2024, 1, 1, tzinfo=UTC)
    t1 = datetime(2024, 1, 2, tzinfo=UTC)
    ref = domain.search(simple_target, t0, t1)[0]
    ref.attrs["dem_array"] = np.array([1.0, 2.0, 3.0])
    acq = domain.acquire(ref)
    with pytest.raises(ValueError, match="2-D"):
        domain.analyze(acq)


def test_analyze_high_threshold_returns_no_observations(
    domain: HydroChokepointsDomain, simple_target: MonitorTarget, funnel_dem: np.ndarray
) -> None:
    """With threshold set above 1.0, no observations should be produced."""
    t0 = datetime(2024, 1, 1, tzinfo=UTC)
    t1 = datetime(2024, 1, 2, tzinfo=UTC)
    ref = domain.search(simple_target, t0, t1)[0]
    ref.attrs["dem_array"] = funnel_dem
    ref.attrs["min_constriction_score"] = 9999.0
    acq = domain.acquire(ref)
    assert domain.analyze(acq) == []


def test_analyze_observation_geometry_is_geojson_point(
    domain: HydroChokepointsDomain, simple_target: MonitorTarget, funnel_dem: np.ndarray
) -> None:
    t0 = datetime(2024, 1, 1, tzinfo=UTC)
    t1 = datetime(2024, 1, 2, tzinfo=UTC)
    ref = domain.search(simple_target, t0, t1)[0]
    ref.attrs["dem_array"] = funnel_dem
    ref.attrs["min_constriction_score"] = 0.5
    ref.attrs["min_upstream_area_km2"] = 0.0
    acq = domain.acquire(ref)
    for obs in domain.analyze(acq):
        assert obs.geometry["type"] == "Point"
        assert len(obs.geometry["coordinates"]) == 2


def test_analyze_confidence_in_range(
    domain: HydroChokepointsDomain, simple_target: MonitorTarget, funnel_dem: np.ndarray
) -> None:
    t0 = datetime(2024, 1, 1, tzinfo=UTC)
    t1 = datetime(2024, 1, 2, tzinfo=UTC)
    ref = domain.search(simple_target, t0, t1)[0]
    ref.attrs["dem_array"] = funnel_dem
    ref.attrs["min_constriction_score"] = 0.0
    ref.attrs["min_upstream_area_km2"] = 0.0
    acq = domain.acquire(ref)
    for obs in domain.analyze(acq):
        assert 0.0 <= obs.confidence <= 1.0


def test_analyze_domain_field_is_hydro_chokepoints(
    domain: HydroChokepointsDomain, simple_target: MonitorTarget, funnel_dem: np.ndarray
) -> None:
    t0 = datetime(2024, 1, 1, tzinfo=UTC)
    t1 = datetime(2024, 1, 2, tzinfo=UTC)
    ref = domain.search(simple_target, t0, t1)[0]
    ref.attrs["dem_array"] = funnel_dem
    ref.attrs["min_constriction_score"] = 0.5
    ref.attrs["min_upstream_area_km2"] = 0.0
    acq = domain.acquire(ref)
    for obs in domain.analyze(acq):
        assert obs.domain == "hydro_chokepoints"


# ── Store: ChokePoint CRUD ────────────────────────────────────────────────────


def test_store_save_and_get_choke_point(store: Store) -> None:
    cp = ChokePoint(
        id="cp-1",
        aoi_id="test_aoi",
        location={"type": "Point", "coordinates": [-61.25, 11.25]},
        upstream_area_km2=2.5,
        constriction_score=0.8,
        dem_source="cop_glo30",
        evidence_class="inferred",
    )
    store.save_choke_point(cp)
    results = store.get_choke_points("test_aoi")
    assert len(results) == 1
    assert results[0].id == "cp-1"
    assert results[0].upstream_area_km2 == pytest.approx(2.5)
    assert results[0].evidence_class == "inferred"


def test_store_get_choke_points_sorted_by_score(store: Store) -> None:
    for i, score in enumerate([0.3, 0.9, 0.5]):
        store.save_choke_point(
            ChokePoint(
                id=f"cp-{i}",
                aoi_id="test_aoi",
                location={"type": "Point", "coordinates": [float(i), float(i)]},
                upstream_area_km2=1.0,
                constriction_score=score,
                dem_source="cop_glo30",
                evidence_class="inferred",
            )
        )
    results = store.get_choke_points("test_aoi")
    scores = [r.constriction_score for r in results]
    assert scores == sorted(scores, reverse=True)


def test_store_get_choke_points_filters_by_aoi(store: Store) -> None:
    for aoi_id in ("aoi_a", "aoi_b"):
        store.save_choke_point(
            ChokePoint(
                id=f"cp-{aoi_id}",
                aoi_id=aoi_id,
                location={"type": "Point", "coordinates": [0.0, 0.0]},
                upstream_area_km2=1.0,
                constriction_score=0.5,
                dem_source="cop_glo30",
                evidence_class="inferred",
            )
        )
    assert len(store.get_choke_points("aoi_a")) == 1
    assert len(store.get_choke_points("aoi_b")) == 1
    assert len(store.get_choke_points("aoi_c")) == 0


def test_store_choke_point_upsert(store: Store) -> None:
    cp = ChokePoint(
        id="cp-upsert",
        aoi_id="aoi",
        location={"type": "Point", "coordinates": [0.0, 0.0]},
        upstream_area_km2=1.0,
        constriction_score=0.3,
        dem_source="cop_glo30",
        evidence_class="inferred",
    )
    store.save_choke_point(cp)
    cp2 = cp.model_copy(update={"constriction_score": 0.9})
    store.save_choke_point(cp2)
    results = store.get_choke_points("aoi")
    assert len(results) == 1
    assert results[0].constriction_score == pytest.approx(0.9)


def test_store_choke_point_location_roundtrip(store: Store) -> None:
    location = {"type": "Point", "coordinates": [-61.123456, 11.654321]}
    cp = ChokePoint(
        id="cp-loc",
        aoi_id="test_aoi",
        location=location,
        upstream_area_km2=0.5,
        constriction_score=0.75,
        dem_source="cop_glo30",
        evidence_class="inferred",
    )
    store.save_choke_point(cp)
    retrieved = store.get_choke_points("test_aoi")[0]
    assert retrieved.location == location


# ── Full end-to-end pipeline (offline) ────────────────────────────────────────


def test_full_pipeline_funnel_dem_produces_choke_points(
    domain: HydroChokepointsDomain, simple_target: MonitorTarget, funnel_dem: np.ndarray
) -> None:
    """End-to-end: search → acquire → analyze on a funnel DEM yields observations."""
    t0 = datetime(2024, 1, 1, tzinfo=UTC)
    t1 = datetime(2024, 1, 2, tzinfo=UTC)

    refs = domain.search(simple_target, t0, t1)
    assert len(refs) == 1

    ref = refs[0]
    ref.attrs["dem_array"] = funnel_dem
    ref.attrs["aoi_id"] = simple_target.aoi_id
    ref.attrs["min_constriction_score"] = 0.5
    ref.attrs["min_upstream_area_km2"] = 0.0

    acq = domain.acquire(ref)
    obs_list = domain.analyze(acq)

    assert len(obs_list) > 0
    for obs in obs_list:
        assert obs.obs_type == "choke_point"
        assert obs.evidence_class == "inferred"
        assert obs.domain == "hydro_chokepoints"
        assert obs.geometry["type"] == "Point"


def test_full_pipeline_valley_dem_outlet_has_highest_score(
    domain: HydroChokepointsDomain, simple_target: MonitorTarget, valley_dem: np.ndarray
) -> None:
    """Valley DEM: lowest row, centre column should produce top-scoring observation."""
    t0 = datetime(2024, 1, 1, tzinfo=UTC)
    t1 = datetime(2024, 1, 2, tzinfo=UTC)

    ref = domain.search(simple_target, t0, t1)[0]
    ref.attrs["dem_array"] = valley_dem
    ref.attrs["min_constriction_score"] = 0.0
    ref.attrs["min_upstream_area_km2"] = 0.0
    ref.attrs["max_candidates"] = 5

    acq = domain.acquire(ref)
    obs_list = domain.analyze(acq)

    assert len(obs_list) > 0
    # First observation should have highest confidence (results sorted by score)
    confs = [o.confidence for o in obs_list]
    assert confs == sorted(confs, reverse=True)
