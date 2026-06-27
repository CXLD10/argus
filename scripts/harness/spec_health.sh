#!/usr/bin/env bash
# spec_health.sh — Specification health checks: VAL-001, VAL-002, VAL-013
#
# Usage: ./spec_health.sh [REPO_ROOT]
# Exit:  0 if all checks pass, non-zero if any violations found.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${1:-$(cd "$SCRIPT_DIR/../.." && pwd)}"

python3 "$SCRIPT_DIR/check_spec_health.py" "$REPO_ROOT"
