#!/usr/bin/env python3
"""Architecture consistency checker: VAL-008, VAL-010, VAL-017.

Can be imported as a module (functions return lists of violation strings) or run
as a CLI (prints results, exits with the violation count).

Usage:
    python scripts/harness/check_architecture.py [REPO_ROOT]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# ── Validator implementations ─────────────────────────────────────────────────


def check_val008_copyleft(root: Path) -> list[str]:
    """VAL-008: No GPL-licensed (opendrift) imports in spine modules.

    opendrift may only be imported inside argus/predict/oil_trajectory/sim_worker.py.
    """
    spine_dirs = [
        root / "argus" / "core",
        root / "argus" / "ingest",
        root / "argus" / "impact",
        root / "argus" / "api",
        root / "argus" / "alert",
        root / "argus" / "eval",
        root / "argus" / "export",
        root / "argus" / "aoi",
        root / "argus" / "preprocess",
    ]
    opendrift_import = re.compile(r"^(?:import opendrift|from opendrift)", re.MULTILINE)
    violations: list[str] = []
    for spine_dir in spine_dirs:
        if not spine_dir.exists():
            continue
        for py_file in spine_dir.rglob("*.py"):
            text = py_file.read_text()
            if opendrift_import.search(text):
                violations.append(
                    f"VAL-008 FAIL: GPL import 'opendrift' found in spine module {py_file}"
                )
    # Also check argus/predict/ but exclude sim_worker.py
    predict_dir = root / "argus" / "predict"
    if predict_dir.exists():
        for py_file in predict_dir.rglob("*.py"):
            if py_file.name == "sim_worker.py":
                continue
            text = py_file.read_text()
            if re.search(r"^import opendrift|^from opendrift", text, re.MULTILINE):
                violations.append(
                    f"VAL-008 FAIL: GPL import 'opendrift' outside isolation boundary in {py_file}"
                )
    return violations


def check_val010_live_network(root: Path) -> list[str]:
    """VAL-010: No live network calls in unit tests (outside tests/integration/).

    Checks for direct HTTP invocations: requests.get(), requests.post(),
    httpx.get(), httpx.post(), urllib.request.urlopen() in non-integration test files.
    Mock spec usage (MagicMock(spec=requests.Session)) is allowed.
    """
    tests_dir = root / "tests"
    integration_dir = tests_dir / "integration"
    if not tests_dir.exists():
        return []

    live_call_pattern = re.compile(
        r"\brequests\.(get|post|put|delete|patch|head)\s*\("
        r"|\bhttpx\.(get|post|put|delete|patch|head)\s*\("
        r"|\burllib\.request\.urlopen\s*\("
    )
    violations: list[str] = []
    for py_file in tests_dir.rglob("*.py"):
        if integration_dir in py_file.parents:
            continue
        text = py_file.read_text()
        for i, line in enumerate(text.splitlines(), 1):
            if line.strip().startswith("#"):
                continue
            if live_call_pattern.search(line):
                violations.append(
                    f"VAL-010 FAIL: Live network call in unit test {py_file}:{i}: {line.strip()}"
                )
    return violations


def check_val017_hardcoded_oil_type(root: Path) -> list[str]:
    """VAL-017: No hardcoded oil type strings in argus/ source code.

    The legacy/generic type names 'generic_oil', 'crude_oil', 'diesel', 'bunker'
    must not appear in argus/ code. Oil types must be loaded from the registry.
    config/ and data/ directories are exempt (they ARE the registry/fixtures).
    """
    argus_dir = root / "argus"
    if not argus_dir.exists():
        return []

    # These are the forbidden hardcoded names from ADR-0006
    pattern = re.compile(r"\b(generic_oil|crude_oil|diesel|bunker)\b")
    violations: list[str] = []
    for py_file in argus_dir.rglob("*.py"):
        text = py_file.read_text()
        for i, line in enumerate(text.splitlines(), 1):
            if line.strip().startswith("#"):
                continue
            if pattern.search(line):
                violations.append(
                    f"VAL-017 FAIL: Hardcoded oil type in {py_file}:{i}: {line.strip()}"
                )
    return violations


# ── CLI entry point ───────────────────────────────────────────────────────────


def run_all(root: Path) -> int:
    """Run all architecture validators. Returns total violation count."""
    checkers = [
        ("VAL-008", check_val008_copyleft),
        ("VAL-010", check_val010_live_network),
        ("VAL-017", check_val017_hardcoded_oil_type),
    ]
    total = 0
    for name, checker in checkers:
        violations = checker(root)
        if violations:
            for v in violations:
                print(v, file=sys.stderr)
            total += len(violations)
        else:
            print(f"{name} PASS")
    return total


def main() -> None:
    if len(sys.argv) > 1:
        repo_root = Path(sys.argv[1]).resolve()
    else:
        repo_root = Path(__file__).resolve().parent.parent.parent

    violations = run_all(repo_root)
    if violations:
        print(f"\n{violations} violation(s) found.", file=sys.stderr)
        sys.exit(violations)
    print("\nAll architecture checks passed.")


if __name__ == "__main__":
    main()
