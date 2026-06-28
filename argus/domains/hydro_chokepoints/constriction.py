"""Constriction scoring and ChokePoint extraction from flow accumulation data.

A choke point candidate is any cell whose flow accumulation exceeds a configurable
threshold (minimum upstream area) and whose constriction score is high enough to
represent meaningful flow concentration.

Constriction score = normalised flow accumulation in [0, 1].
Normalisation is against the maximum accumulation value in the raster so the score
is dimensionless and AOI-independent.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from argus.core.models import ChokePoint
from argus.domains.hydro_chokepoints.dem_processor import upstream_area_km2


@dataclass(frozen=True)
class ChokePointCandidate:
    """Raw extraction result before ChokePoint model construction."""

    row: int
    col: int
    facc_value: int
    constriction_score: float
    upstream_area_km2: float


def score_constriction(facc: NDArray[np.int64]) -> NDArray[np.float64]:
    """Normalise flow accumulation to a [0, 1] constriction score.

    Cells with zero upstream area score 0.0.  The cell with the maximum
    flow accumulation scores 1.0.  NaN is returned for empty rasters.
    """
    max_val = float(np.max(facc))
    if max_val == 0:
        return np.zeros_like(facc, dtype=np.float64)
    return (facc / max_val).astype(np.float64)


def extract_choke_points(
    facc: NDArray[np.int64],
    scores: NDArray[np.float64],
    cell_size_m: float,
    *,
    min_upstream_area_km2: float,
    min_constriction_score: float,
    max_candidates: int,
) -> list[ChokePointCandidate]:
    """Return the top-N ChokePoint candidates ranked by constriction score.

    Parameters
    ----------
    facc:
        Flow accumulation raster.
    scores:
        Constriction score raster (same shape).
    cell_size_m:
        Ground sampling distance in metres (used to convert cell counts to km²).
    min_upstream_area_km2:
        Minimum upstream drainage area threshold — cells below are excluded.
    min_constriction_score:
        Minimum normalised score to include a candidate.
    max_candidates:
        Maximum number of candidates to return.
    """
    rows, cols = facc.shape
    candidates: list[ChokePointCandidate] = []

    for r in range(rows):
        for c in range(cols):
            score = float(scores[r, c])
            area = upstream_area_km2(int(facc[r, c]), cell_size_m)
            if area < min_upstream_area_km2:
                continue
            if score < min_constriction_score:
                continue
            candidates.append(
                ChokePointCandidate(
                    row=r,
                    col=c,
                    facc_value=int(facc[r, c]),
                    constriction_score=score,
                    upstream_area_km2=area,
                )
            )

    candidates.sort(key=lambda cp: cp.constriction_score, reverse=True)
    return candidates[:max_candidates]


def candidates_to_choke_points(
    candidates: list[ChokePointCandidate],
    aoi_id: str,
    *,
    origin_lon: float,
    origin_lat: float,
    cell_size_deg: float,
    dem_source: str = "cop_glo30",
) -> list[ChokePoint]:
    """Convert ChokePointCandidates to ChokePoint model instances.

    Grid row/col are converted to geographic coordinates using the raster origin
    and cell size (degrees).  Row 0 = northern edge (origin_lat), col 0 = western
    edge (origin_lon), row increases southward.

    INV-3: evidence_class is always "inferred".
    """
    results: list[ChokePoint] = []
    for cand in candidates:
        lon = origin_lon + (cand.col + 0.5) * cell_size_deg
        lat = origin_lat - (cand.row + 0.5) * cell_size_deg
        results.append(
            ChokePoint(
                id=str(uuid.uuid4()),
                aoi_id=aoi_id,
                location={
                    "type": "Point",
                    "coordinates": [round(lon, 6), round(lat, 6)],
                },
                upstream_area_km2=round(cand.upstream_area_km2, 4),
                constriction_score=round(cand.constriction_score, 4),
                dem_source=dem_source,
                evidence_class="inferred",
            )
        )
    return results
