"""D4: HydroChokepointsDomain — Domain protocol implementation.

search() returns a synthetic SourceRef representing the AOI DEM tile.
acquire() wraps the DEM array into an Acquisition (in production this would
         fetch the tile from Copernicus DEM; offline it reads from attrs).
analyze() runs D8 flow direction + accumulation + constriction scoring and
          returns one Observation per ChokePoint candidate.

INV-2: spine never edited. INV-3: evidence_class is always "inferred".
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import numpy as np

from argus.core.models import (
    MonitorTarget,
    Observation,
    SourceRef,
)
from argus.domains.base import Acquisition
from argus.domains.hydro_chokepoints.constriction import (
    candidates_to_choke_points,
    extract_choke_points,
    score_constriction,
)
from argus.domains.hydro_chokepoints.dem_processor import (
    compute_flow_accumulation,
    compute_flow_direction,
)

if TYPE_CHECKING:
    from numpy.typing import NDArray


class HydroChokepointsDomain:
    """D4 Domain: DEM-derived drainage choke-point detection."""

    domain_id: str = "hydro_chokepoints"

    # ── Domain.search ─────────────────────────────────────────────────────────

    def search(
        self,
        target: MonitorTarget,
        t0: datetime,
        t1: datetime,
    ) -> list[SourceRef]:
        """Return a single synthetic SourceRef representing the DEM tile for *target*.

        DEM is static (not time-varying), so t0/t1 are recorded in attrs only.
        The product_id is deterministic from the target id, ensuring idempotency.
        """
        bbox = _bbox_from_geometry(target.geometry)
        return [
            SourceRef(
                product_id=f"dem_cop_glo30_{target.id}",
                source="copernicus_dem",
                collection="COP-DEM_GLO-30",
                product_type="DEM",
                sensor_mode="n/a",
                sensing_time=t0,
                footprint={
                    "type": "Polygon",
                    "coordinates": [_bbox_to_ring(bbox)],
                },
                polarizations=[],
                attrs={
                    "bbox": list(bbox),
                    "t0": t0.isoformat(),
                    "t1": t1.isoformat(),
                },
            )
        ]

    # ── Domain.acquire ────────────────────────────────────────────────────────

    def acquire(self, ref: SourceRef) -> Acquisition:
        """Wrap the DEM array into an Acquisition.

        In test/offline mode the caller pre-populates ref.attrs["dem_array"]
        (a numpy ndarray).  In production this method would fetch the DEM tile
        from Copernicus DEM; that network path is covered by a live test.
        """
        dem: NDArray[np.float64] | None = ref.attrs.get("dem_array")
        if dem is not None and not isinstance(dem, np.ndarray):
            raise TypeError(
                f"ref.attrs['dem_array'] must be a numpy ndarray, got {type(dem)}"
            )
        return Acquisition(
            scene_id=str(uuid.uuid4()),
            source_ref=ref,
            preprocessed=dem,
            attrs=dict(ref.attrs),
        )

    # ── Domain.analyze ────────────────────────────────────────────────────────

    def analyze(self, acq: Acquisition) -> list[Observation]:
        """Run D8 flow accumulation and return one Observation per choke point.

        The DEM array must be in acq.preprocessed (set by acquire() from
        ref.attrs["dem_array"]).  Thresholds are read from acq.attrs or
        fall back to the domain defaults baked into constriction.extract_choke_points.

        INV-3: evidence_class is always "inferred".
        """
        dem: NDArray[np.float64] | None = acq.preprocessed
        if dem is None or not isinstance(dem, np.ndarray):
            raise ValueError(
                "acq.preprocessed must be a numpy ndarray (DEM elevation grid). "
                "Populate ref.attrs['dem_array'] before calling acquire()."
            )
        if dem.ndim != 2:
            raise ValueError(f"DEM must be 2-D, got shape {dem.shape}")

        dem = dem.astype(np.float64)

        # Pull thresholds from acq.attrs (runner passes settings-derived values)
        cell_size_m: float = float(acq.attrs.get("cell_size_m", 30.0))
        min_area_km2: float = float(acq.attrs.get("min_upstream_area_km2", 1.0))
        min_score: float = float(acq.attrs.get("min_constriction_score", 0.05))
        max_cands: int = int(acq.attrs.get("max_candidates", 50))
        dem_source: str = str(acq.attrs.get("dem_source", "cop_glo30"))
        aoi_id: str = str(acq.attrs.get("aoi_id", "unknown"))

        # D8 pipeline
        fdir = compute_flow_direction(dem)
        facc = compute_flow_accumulation(dem, fdir)
        scores = score_constriction(facc)

        # Extract raster origin from bbox stored in attrs (or default to 0,0)
        bbox: list[float] = list(acq.attrs.get("bbox", [0.0, 0.0, 1.0, 1.0]))
        min_lon, min_lat, max_lon, max_lat = bbox
        rows, cols = dem.shape
        cell_size_deg = (max_lat - min_lat) / rows if rows > 0 else 0.01
        origin_lon = min_lon
        origin_lat = max_lat  # row 0 = northern edge

        candidates = extract_choke_points(
            facc,
            scores,
            cell_size_m,
            min_upstream_area_km2=min_area_km2,
            min_constriction_score=min_score,
            max_candidates=max_cands,
        )
        choke_points = candidates_to_choke_points(
            candidates,
            aoi_id,
            origin_lon=origin_lon,
            origin_lat=origin_lat,
            cell_size_deg=cell_size_deg,
            dem_source=dem_source,
        )

        now = datetime.now(UTC)
        observations: list[Observation] = []
        for cp in choke_points:
            observations.append(
                Observation(
                    id=str(uuid.uuid4()),
                    analysis_run_id=acq.attrs.get("analysis_run_id", ""),
                    scene_id=acq.scene_id,
                    obs_type="choke_point",
                    evidence_class="inferred",
                    geometry=cp.location,
                    area_km2=round(cp.upstream_area_km2, 4),
                    confidence=round(cp.constriction_score, 4),
                    domain="hydro_chokepoints",
                    attrs={
                        "constriction_score": cp.constriction_score,
                        "upstream_area_km2": cp.upstream_area_km2,
                        "dem_source": dem_source,
                        "choke_point_id": cp.id,
                    },
                    created_at=now,
                )
            )
        return observations


# ── Geometry helpers ──────────────────────────────────────────────────────────


def _bbox_from_geometry(geometry: dict[str, Any]) -> tuple[float, float, float, float]:
    """Return (min_lon, min_lat, max_lon, max_lat) from a GeoJSON geometry."""
    coords = _flatten_coords(geometry)
    if not coords:
        return (0.0, 0.0, 1.0, 1.0)
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return (min(lons), min(lats), max(lons), max(lats))


def _flatten_coords(
    geometry: dict[str, Any],
) -> list[tuple[float, float]]:
    gtype = geometry.get("type", "")
    coords: Any = geometry.get("coordinates", [])
    if gtype == "Point":
        return [(float(coords[0]), float(coords[1]))]
    if gtype == "LineString":
        return [(float(c[0]), float(c[1])) for c in coords]
    if gtype == "Polygon":
        return [(float(c[0]), float(c[1])) for ring in coords for c in ring]
    if gtype == "MultiPolygon":
        return [(float(c[0]), float(c[1])) for poly in coords for ring in poly for c in ring]
    return []


def _bbox_to_ring(
    bbox: tuple[float, float, float, float],
) -> list[list[float]]:
    min_lon, min_lat, max_lon, max_lat = bbox
    return [
        [min_lon, min_lat],
        [max_lon, min_lat],
        [max_lon, max_lat],
        [min_lon, max_lat],
        [min_lon, min_lat],
    ]
