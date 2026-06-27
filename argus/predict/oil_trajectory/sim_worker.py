"""GPL-isolated OpenOil subprocess worker.

This module is executed as a child process by runner.py — it is never imported
directly by the main argus package.

GPL isolation: import opendrift is contained inside _simulate() which is only
called when this file runs as __main__. No other argus module may import opendrift.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _simulate(input_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Run OpenOil simulation and return a list of ForecastFrame dicts.

    This function is the only place in the argus codebase that imports opendrift.
    """
    import opendrift  # noqa: PLC0415 — GPL isolation: import opendrift here only
    from opendrift.models.openoil import OpenOil  # noqa: PLC0415

    o = OpenOil(loglevel=50)
    o.set_config("seed:oil_type", input_data["oil_type"])

    import numpy as np  # noqa: PLC0415

    geom = input_data["seed_geometry"]
    if geom["type"] == "Point":
        lon, lat = geom["coordinates"]
    else:
        coords = geom["coordinates"][0]
        lon = float(np.mean([c[0] for c in coords]))
        lat = float(np.mean([c[1] for c in coords]))

    n = input_data["n_particles"]
    o.seed_elements(
        lon=lon,
        lat=lat,
        radius=500,
        number=n,
        time=input_data["t0"],
    )
    o.run(
        duration=opendrift.timedelta(hours=input_data["duration_hours"]),
        time_step=opendrift.timedelta(minutes=input_data["timestep_minutes"]),
    )

    frames: list[dict[str, Any]] = []
    for i in range(len(o.history["lon"][0])):
        lons = o.history["lon"][:, i].compressed().tolist()
        lats = o.history["lat"][:, i].compressed().tolist()
        if not lons:
            continue
        coords_ring = list(zip(lons, lats, strict=True)) + [(lons[0], lats[0])]
        frame: dict[str, Any] = {
            "valid_at": str(o.get_time_array()[0][i]),
            "particle_count": len(lons),
            "footprint": {
                "type": "Polygon",
                "coordinates": [[[c[0], c[1]] for c in coords_ring]],
            },
            "stats": {
                "mean_lon": float(sum(lons) / len(lons)),
                "mean_lat": float(sum(lats) / len(lats)),
            },
        }
        frames.append(frame)
    return frames


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OpenOil simulation worker")
    parser.add_argument("--input", required=True, help="Path to input JSON file")
    parser.add_argument("--output", required=True, help="Path to write output JSON file")
    args = parser.parse_args()

    input_data: dict[str, Any] = json.loads(Path(args.input).read_text())
    frames = _simulate(input_data)
    Path(args.output).write_text(json.dumps(frames))
