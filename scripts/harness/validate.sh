#!/usr/bin/env bash
# validate.sh — Architecture consistency checks: VAL-008, VAL-010, VAL-017
#
# Usage: ./validate.sh [REPO_ROOT]
# Exit:  0 if all checks pass, non-zero if any violations found.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${1:-$(cd "$SCRIPT_DIR/../.." && pwd)}"

python3 "$SCRIPT_DIR/check_architecture.py" "$REPO_ROOT"
