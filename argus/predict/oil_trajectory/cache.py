"""Parquet-based forcing cache for oil trajectory simulations.

Avoids repeated API calls by persisting ForcingGrid data as parquet files
keyed by a hash of the request parameters.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING

import pyarrow as pa
import pyarrow.parquet as pq

if TYPE_CHECKING:
    from argus.predict.oil_trajectory.forcing import ForcingGrid

_DEFAULT_CACHE_DIR = Path(".argus") / "forcing_cache"


def _cache_key(bbox: tuple[float, float, float, float], t0: str, t1: str, source: str) -> str:
    payload = json.dumps({"bbox": bbox, "t0": t0, "t1": t1, "source": source}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


class ForcingCache:
    """Read/write ForcingGrid parquet files keyed by request params."""

    def __init__(self, cache_dir: Path = _DEFAULT_CACHE_DIR) -> None:
        self._dir = cache_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self._dir / f"forcing_{key}.parquet"

    def save(
        self,
        bbox: tuple[float, float, float, float],
        t0: str,
        t1: str,
        source: str,
        grid: ForcingGrid,
    ) -> None:
        key = _cache_key(bbox, t0, t1, source)
        table = pa.table(
            {
                "time": grid.times,
                "wind_u": grid.wind_u,
                "wind_v": grid.wind_v,
                "current_u": grid.current_u,
                "current_v": grid.current_v,
            }
        )
        pq.write_table(table, self._path(key))

    def load(
        self,
        bbox: tuple[float, float, float, float],
        t0: str,
        t1: str,
        source: str,
    ) -> ForcingGrid | None:
        key = _cache_key(bbox, t0, t1, source)
        path = self._path(key)
        if not path.exists():
            return None
        return _parquet_to_grid(path, source)


def _parquet_to_grid(path: Path, source: str) -> ForcingGrid:
    from argus.predict.oil_trajectory.forcing import ForcingGrid  # avoid circular import

    table = pq.read_table(path)
    return ForcingGrid(
        times=table["time"].to_pylist(),
        wind_u=table["wind_u"].to_pylist(),
        wind_v=table["wind_v"].to_pylist(),
        current_u=table["current_u"].to_pylist(),
        current_v=table["current_v"].to_pylist(),
        source=source,
    )
