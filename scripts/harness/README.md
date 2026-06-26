# Argus Validation Harness

Scripts in this directory implement the 7-component harness defined in
[`docs/governance/HARNESS.md`](../../docs/governance/HARNESS.md).

These scripts are run by agents at the start of every session (pre-session checklist)
and by CI on every commit. See [`CLAUDE.md`](../../CLAUDE.md) §Pre-session checklist.

## Scripts

| Script | Harness component | Description |
|---|---|---|
| `check_repo_health.py` | H1 Repo Health | Checks for untracked files, merge conflicts, lock files |
| `check_spec_health.py` | H2 Spec Health | Validates that all ADRs, feature specs, and open questions are internally consistent |
| `check_architecture.py` | H3 Architecture Consistency | Runs all 22 validators (VAL-001–VAL-022) |
| `check_progress.py` | H4 Progress Tracker | Reconciles BOARD.md task statuses against git reality |
| `check_deps.py` | H5 Dependency Graph | Verifies feature dependency graph is acyclic and all deps exist |
| `check_cost.py` | H6 Cost Compliance | Checks that no new recurring-cost dependencies have been added |
| `check_docs.py` | H7 Documentation Coverage | Checks that every feature spec has a corresponding BOARD.md row |

## Usage

```bash
# Run all checks (pre-session)
python scripts/harness/check_architecture.py

# Run a specific check
python scripts/harness/check_architecture.py --validator VAL-017

# Run all harness components
python scripts/harness/run_all.py
```

## Status

All scripts are stubs — implemented in Phase 3.5 (F-019).
