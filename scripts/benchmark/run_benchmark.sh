#!/usr/bin/env bash
# Argus performance benchmark — F-053
#
# Measures latency for each major pipeline stage and compares against targets
# defined in docs/features/phase-11.md and docs/status/performance_baseline.md.
#
# Usage:
#   ./scripts/benchmark/run_benchmark.sh [--aoi <slug>]
#
# Targets (from F-053 spec):
#   Scene acquisition (offline)  < 1 s
#   SAR preprocessing            < 30 s
#   Oil detection                < 60 s
#   Trajectory simulation        < 5 min (300 s)
#   WQ analysis                  < 30 s
#   AI report (offline template) < 30 s
#   Full AOI run                 < 10 min (600 s)
#
# Exit codes:
#   0  All stages within target
#   1  One or more stages exceed target (soft warning, not a hard fail)
#   2  Setup error

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV="${REPO_ROOT}/.venv"
PYTHON="${VENV}/bin/python"

AOI_SLUG="tobago"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --aoi) AOI_SLUG="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [[ ! -x "${PYTHON}" ]]; then
  echo "ERROR: Python not found at ${VENV}/bin/python" >&2
  exit 2
fi

# Run the benchmark via Python
exec "${PYTHON}" "${REPO_ROOT}/scripts/benchmark/run_benchmark.py" --aoi "${AOI_SLUG}"
