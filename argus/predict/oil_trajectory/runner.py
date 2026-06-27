"""Oil trajectory runner — main-process interface for the GPL-isolated sim worker.

Pattern:
    runner.py (this file, main process)
      └─ subprocess → sim_worker.py  ← opendrift loaded there only (ADR-0002 D2)

GPL isolation: this module must never load opendrift. Only sim_worker.py may do so.
"""

from __future__ import annotations

import dataclasses
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from argus.core.errors import SimulationError
from argus.predict.oil_trajectory.oil_types import (
    OilTypeNotFoundError,  # re-exported for callers
    OilTypeRegistry,
    OilTypeRequiredError,  # re-exported for callers
    load_oil_types,
)

__all__ = [
    "SimInput",
    "OilTypeRequiredError",
    "OilTypeNotFoundError",
    "run_simulation",
]

_DEFAULT_REGISTRY_PATH = Path("config") / "oil_types.yaml"


@dataclass
class SimInput:
    """Serialisable input for one oil trajectory simulation."""

    oil_type: str  # must be in registry (INV-5)
    seed_geometry: dict[str, Any]  # GeoJSON starting slick polygon / point
    t0: str  # ISO-8601 UTC start time
    duration_hours: int  # simulation length
    rng_seed: int  # INV-8: must be provided; no random default
    n_particles: int = 1000
    timestep_minutes: int = 60
    forcing: dict[str, Any] = field(default_factory=dict)  # pre-fetched metocean (F-012)


def run_simulation(
    sim_input: SimInput,
    *,
    registry: OilTypeRegistry | None = None,
    worker_module: str = "argus.predict.oil_trajectory.sim_worker",
) -> list[dict[str, Any]]:
    """Run the oil trajectory simulation in an isolated subprocess.

    Validates *sim_input.oil_type* against *registry* before spawning the worker.
    Returns a list of ForecastFrame dicts (one per output timestep).

    Raises:
        OilTypeRequiredError: if oil_type is absent/empty.
        OilTypeNotFoundError: if oil_type is not in the registry.
        RuntimeError: if the worker subprocess exits with a non-zero code.
    """
    if registry is None:
        registry = load_oil_types()
    registry.get(sim_input.oil_type)  # raises OilTypeRequired/NotFoundError on bad input

    with tempfile.TemporaryDirectory() as tmpdir:
        in_path = Path(tmpdir) / "input.json"
        out_path = Path(tmpdir) / "output.json"
        in_path.write_text(json.dumps(dataclasses.asdict(sim_input)))

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                worker_module,
                "--input",
                str(in_path),
                "--output",
                str(out_path),
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise SimulationError(
                f"sim_worker exited with code {result.returncode}:\n{result.stderr}\n"
                "Ensure opendrift is installed in the simulation environment."
            )
        return json.loads(out_path.read_text())  # type: ignore[no-any-return]
