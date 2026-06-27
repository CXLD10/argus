#!/usr/bin/env bash
# run_all.sh — Run all harness validation scripts.
#
# Usage: ./run_all.sh [REPO_ROOT]
# Exit:  0 if all checks pass, non-zero if any violations found.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${1:-$(cd "$SCRIPT_DIR/../.." && pwd)}"

FAILURES=0

echo "=== Architecture checks (VAL-008, VAL-010, VAL-017) ==="
if ! "$SCRIPT_DIR/validate.sh" "$REPO_ROOT"; then
    FAILURES=$((FAILURES + 1))
fi

echo ""
echo "=== Specification health checks (VAL-001, VAL-002, VAL-013) ==="
if ! "$SCRIPT_DIR/spec_health.sh" "$REPO_ROOT"; then
    FAILURES=$((FAILURES + 1))
fi

echo ""
if [ "$FAILURES" -gt 0 ]; then
    echo "HARNESS FAILED: $FAILURES check(s) failed." >&2
    exit 1
fi

echo "All harness checks passed."
