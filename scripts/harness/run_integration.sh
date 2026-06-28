#!/usr/bin/env bash
# Argus integration test harness — F-052
#
# Usage:
#   ./scripts/harness/run_integration.sh           # offline (default)
#   ./scripts/harness/run_integration.sh --live    # live network tests
#   ./scripts/harness/run_integration.sh --suite oil   # single suite
#   ./scripts/harness/run_integration.sh --suite wq
#   ./scripts/harness/run_integration.sh --suite ai
#   ./scripts/harness/run_integration.sh --suite full
#
# Exit codes:
#   0  All tests passed
#   1  One or more tests failed
#   2  Setup error (missing venv, missing deps)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV="${REPO_ROOT}/.venv"
LIVE_FLAG=""
SUITE="all"

# ── Parse args ────────────────────────────────────────────────────────────────

while [[ $# -gt 0 ]]; do
  case "$1" in
    --live)
      LIVE_FLAG="--live"
      shift
      ;;
    --suite)
      SUITE="$2"
      shift 2
      ;;
    -h|--help)
      head -20 "$0" | grep "^#" | sed 's/^# //'
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

# ── Environment check ─────────────────────────────────────────────────────────

if [[ ! -d "${VENV}" ]]; then
  echo "ERROR: Virtual environment not found at ${VENV}" >&2
  echo "Run: uv venv && source .venv/bin/activate && uv pip install -e '.[dev]'" >&2
  exit 2
fi

PYTHON="${VENV}/bin/python"
PYTEST="${VENV}/bin/pytest"

if [[ ! -x "${PYTEST}" ]]; then
  echo "ERROR: pytest not found in venv. Run: uv pip install -e '.[dev]'" >&2
  exit 2
fi

# ── Set offline mode unless --live ────────────────────────────────────────────

if [[ -z "${LIVE_FLAG}" ]]; then
  export ARGUS_AI_OFFLINE=true
fi

# ── Select test suite ─────────────────────────────────────────────────────────

case "${SUITE}" in
  oil)
    TEST_PATHS="${REPO_ROOT}/tests/integration/test_e2e_oil.py"
    SUITE_LABEL="D1 Oil"
    ;;
  wq)
    TEST_PATHS="${REPO_ROOT}/tests/integration/test_e2e_wq.py"
    SUITE_LABEL="D2 Water Quality"
    ;;
  ai)
    TEST_PATHS="${REPO_ROOT}/tests/integration/test_e2e_ai.py"
    SUITE_LABEL="AI Layer"
    ;;
  full)
    TEST_PATHS="${REPO_ROOT}/tests/integration/test_e2e_full.py"
    SUITE_LABEL="Full Platform (all validators)"
    ;;
  all)
    TEST_PATHS="${REPO_ROOT}/tests/integration/"
    SUITE_LABEL="All Integration Suites"
    ;;
  *)
    echo "Unknown suite: ${SUITE}. Valid: oil|wq|ai|full|all" >&2
    exit 2
    ;;
esac

# ── Header ────────────────────────────────────────────────────────────────────

echo "═══════════════════════════════════════════════════════════════"
echo "  Argus Integration Test Harness — F-052"
echo "  Suite:   ${SUITE_LABEL}"
echo "  Mode:    $([ -z "${LIVE_FLAG}" ] && echo 'offline' || echo 'LIVE (network)')"
echo "  Python:  ${PYTHON}"
echo "  Root:    ${REPO_ROOT}"
echo "═══════════════════════════════════════════════════════════════"
echo ""

START_TIME=$(date +%s)

# ── Run architecture validators first ────────────────────────────────────────

echo "── Architecture validators (VAL-008, VAL-010, VAL-017) ────────"
"${PYTHON}" "${REPO_ROOT}/scripts/harness/check_architecture.py" "${REPO_ROOT}"
echo ""

# ── Run spec health checks ────────────────────────────────────────────────────

echo "── Spec health checks (VAL-001, VAL-002, VAL-013) ─────────────"
"${PYTHON}" "${REPO_ROOT}/scripts/harness/check_spec_health.py" "${REPO_ROOT}"
echo ""

# ── Run integration tests ────────────────────────────────────────────────────

echo "── pytest integration suite ────────────────────────────────────"
PYTEST_ARGS=(
  "${TEST_PATHS}"
  -v
  --tb=short
  --no-header
  -p no:warnings
)

if [[ -n "${LIVE_FLAG}" ]]; then
  PYTEST_ARGS+=("${LIVE_FLAG}")
fi

"${PYTEST}" "${PYTEST_ARGS[@]}"
PYTEST_EXIT=$?

# ── Summary ───────────────────────────────────────────────────────────────────

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Total elapsed: ${ELAPSED}s"
if [[ ${PYTEST_EXIT} -eq 0 ]]; then
  echo "  Result:  ✓ ALL CHECKS PASSED"
else
  echo "  Result:  ✗ FAILURES — see output above"
fi
echo "═══════════════════════════════════════════════════════════════"

exit ${PYTEST_EXIT}
