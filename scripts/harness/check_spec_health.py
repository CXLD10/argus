#!/usr/bin/env python3
"""Specification health checker: VAL-001, VAL-002, VAL-013.

Can be imported as a module or run as a CLI.

Usage:
    python scripts/harness/check_spec_health.py [REPO_ROOT]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# ── Validator implementations ─────────────────────────────────────────────────


def check_val001_fr_coverage(root: Path) -> list[str]:
    """VAL-001: Every FR-n in PRD.md maps to at least one feature in docs/features/.

    Simplified check: every FR-n mentioned in PRD.md §7 must be mentioned in
    at least one phase spec file in docs/features/.
    """
    prd = root / "docs" / "product" / "PRD.md"
    features_dir = root / "docs" / "features"
    if not prd.exists():
        return ["VAL-001 FAIL: docs/product/PRD.md not found"]
    if not features_dir.exists():
        return ["VAL-001 FAIL: docs/features/ directory not found"]

    # Find all FR-n IDs in PRD.md
    prd_text = prd.read_text()
    frs = set(re.findall(r"\bFR-\d+\b", prd_text))
    if not frs:
        return ["VAL-001 FAIL: No FR-n entries found in PRD.md"]

    # Build combined text of all phase spec files
    spec_text = ""
    for spec_file in sorted(features_dir.glob("phase-*.md")):
        spec_text += spec_file.read_text()

    violations = []
    for fr in sorted(frs):
        # Phase specs reference FRs via prose; also check ROADMAP.md and BOARD.md
        roadmap = root / "ROADMAP.md"
        board = root / "BOARD.md"
        search_corpus = spec_text
        if roadmap.exists():
            search_corpus += roadmap.read_text()
        if board.exists():
            search_corpus += board.read_text()
        if fr not in search_corpus:
            violations.append(f"VAL-001 FAIL: {fr} from PRD.md has no reference in docs/features/")
    return violations


def check_val002_feature_has_tasks(root: Path) -> list[str]:
    """VAL-002: Every F-XXX feature in phase specs has at least one task with acceptance criteria.

    Checks that each `## F-XXX` section is followed (within the same section) by an
    `**Acceptance criteria:**` block.
    """
    features_dir = root / "docs" / "features"
    if not features_dir.exists():
        return ["VAL-002 FAIL: docs/features/ directory not found"]

    violations: list[str] = []
    for spec_file in sorted(features_dir.glob("phase-*.md")):
        # Prepend newline so the pattern matches feature sections at file start too.
        text = "\n" + spec_file.read_text()
        sections = re.split(r"\n## (F-\d+)", text)
        # sections[0] = preamble, then pairs of (feature_id, content)
        i = 1
        while i < len(sections) - 1:
            feature_id = sections[i]
            content = sections[i + 1]
            next_section_match = re.search(r"\n##\s", content)
            if next_section_match:
                content = content[: next_section_match.start()]
            if "Acceptance criteria" not in content and "acceptance criteria" not in content:
                violations.append(
                    f"VAL-002 FAIL: {feature_id} in {spec_file.name} has no acceptance criteria"
                )
            i += 2
    return violations


def check_val013_acceptance_criteria_non_empty(root: Path) -> list[str]:
    """VAL-013: Every F-XXX acceptance criteria section has at least one criterion.

    Checks that `**Acceptance criteria:**` blocks are followed by at least one
    `- ` bullet point.
    """
    features_dir = root / "docs" / "features"
    if not features_dir.exists():
        return ["VAL-013 FAIL: docs/features/ directory not found"]

    violations: list[str] = []

    for spec_file in sorted(features_dir.glob("phase-*.md")):
        # Prepend newline so the pattern matches feature sections at file start too.
        text = "\n" + spec_file.read_text()
        feature_sections = re.finditer(r"\n## (F-\d+)[^\n]*\n", text)
        for match in feature_sections:
            feature_id = match.group(1)
            start = match.end()
            # Find next ## section or EOF
            next_section = re.search(r"\n## ", text[start:])
            end = start + next_section.start() if next_section else len(text)
            section_content = text[start:end]

            # Check if there's an acceptance criteria block with at least one bullet
            ac_match = re.search(r"\*\*Acceptance criteria:\*\*", section_content)
            if ac_match:
                after_ac = section_content[ac_match.end() :]
                # Find next blank-line-separated block
                has_bullet = bool(re.search(r"^\s*[-*]\s+\S", after_ac, re.MULTILINE))
                if not has_bullet:
                    violations.append(
                        f"VAL-013 FAIL: {feature_id} in {spec_file.name} has empty"
                        " acceptance criteria"
                    )
    return violations


# ── CLI entry point ───────────────────────────────────────────────────────────


def run_all(root: Path) -> int:
    """Run all spec health validators. Returns total violation count."""
    checkers = [
        ("VAL-001", check_val001_fr_coverage),
        ("VAL-002", check_val002_feature_has_tasks),
        ("VAL-013", check_val013_acceptance_criteria_non_empty),
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
    print("\nAll spec health checks passed.")


if __name__ == "__main__":
    main()
