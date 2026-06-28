"""Pure-numpy D8 flow direction and flow accumulation for DEM-derived choke points.

D8 (deterministic 8-direction) algorithm:
  For each cell, flow is directed to the steepest downslope neighbour (8-connected).
  Cells with no downslope neighbour (local minima / sinks) drain to themselves.

No rasterio or GDAL dependency — arrays arrive as numpy ndarrays.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

# D8 direction offsets: index → (row_delta, col_delta)
# Ordered so that index 0 = E, 1 = SE, 2 = S, …, 7 = NE (clockwise from east)
_D8_OFFSETS: tuple[tuple[int, int], ...] = (
    (0, 1),   # E
    (1, 1),   # SE
    (1, 0),   # S
    (1, -1),  # SW
    (0, -1),  # W
    (-1, -1), # NW
    (-1, 0),  # N
    (-1, 1),  # NE
)

# Euclidean distance to diagonal neighbours is √2 × cell_size vs. 1 × cell_size for
# cardinal neighbours.  We store squared distances to avoid a sqrt.
_D8_DIST_FACTOR: tuple[float, ...] = (
    1.0, 1.4142, 1.0, 1.4142,
    1.0, 1.4142, 1.0, 1.4142,
)


def compute_flow_direction(dem: NDArray[np.float64]) -> NDArray[np.int8]:
    """Return a D8 flow direction raster from *dem*.

    Each cell stores the neighbour index (0–7) to which flow is directed.
    Cells with no downslope neighbour store -1 (sink / local minimum).

    Parameters
    ----------
    dem:
        2-D float64 array of elevation values (any consistent unit — metres preferred).
        NaN cells are treated as NoData and set to -1.

    Returns
    -------
    NDArray[np.int8]
        Same shape as *dem*.  Values 0–7 are D8 direction codes; -1 = sink/NoData.
    """
    rows, cols = dem.shape
    fdir: NDArray[np.int8] = np.full((rows, cols), -1, dtype=np.int8)

    for r in range(rows):
        for c in range(cols):
            elev = dem[r, c]
            if np.isnan(elev):
                continue
            best_idx = -1
            best_drop = 0.0  # must beat zero (flat → sink)
            for k, (dr, dc) in enumerate(_D8_OFFSETS):
                nr, nc = r + dr, c + dc
                if nr < 0 or nr >= rows or nc < 0 or nc >= cols:
                    continue
                nb_elev = dem[nr, nc]
                if np.isnan(nb_elev):
                    continue
                # Normalise drop by distance so diagonals are not unfairly preferred
                drop = (elev - nb_elev) / _D8_DIST_FACTOR[k]
                if drop > best_drop:
                    best_drop = drop
                    best_idx = k
            fdir[r, c] = best_idx

    return fdir


def compute_flow_accumulation(
    dem: NDArray[np.float64],
    fdir: NDArray[np.int8],
) -> NDArray[np.int64]:
    """Return a flow accumulation raster.

    Each cell value is the number of upstream cells whose flow routes through it
    (not counting the cell itself).

    Algorithm: process cells in descending elevation order (highest first).
    Each cell propagates its accumulated count + 1 to its downstream neighbour.

    Parameters
    ----------
    dem:
        2-D float64 elevation array (same shape as *fdir*).
    fdir:
        D8 flow direction array from :func:`compute_flow_direction`.

    Returns
    -------
    NDArray[np.int64]
        Flow accumulation counts (≥ 0).  Sinks (-1 fdir) receive upstream flow
        but do not propagate further.
    """
    rows, cols = dem.shape
    facc: NDArray[np.int64] = np.zeros((rows, cols), dtype=np.int64)

    # Flatten indices sorted by descending elevation (NaN cells last / ignored)
    flat_elev = dem.ravel()
    order = np.argsort(-np.where(np.isnan(flat_elev), -np.inf, flat_elev), stable=True)

    for flat_idx in order:
        r, c = divmod(int(flat_idx), cols)
        if np.isnan(dem[r, c]):
            continue
        k = int(fdir[r, c])
        if k < 0:
            continue
        dr, dc = _D8_OFFSETS[k]
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols:
            facc[nr, nc] += facc[r, c] + 1

    return facc


def upstream_area_km2(facc_value: int, cell_size_m: float) -> float:
    """Convert a flow accumulation cell count to upstream area in km²."""
    cell_area_km2 = (cell_size_m / 1000.0) ** 2
    return facc_value * cell_area_km2
