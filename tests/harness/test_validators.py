"""F-019 validator tests: confirm harness checks pass on this codebase and catch violations."""

from __future__ import annotations

import sys
from pathlib import Path

# Import validator modules from scripts/harness/
_HARNESS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts" / "harness"
sys.path.insert(0, str(_HARNESS_DIR))

from check_architecture import (  # noqa: E402
    check_val008_copyleft,
    check_val010_live_network,
    check_val017_hardcoded_oil_type,
)
from check_spec_health import (  # noqa: E402
    check_val001_fr_coverage,
    check_val002_feature_has_tasks,
    check_val013_acceptance_criteria_non_empty,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


# ── VAL-008: No copyleft in spine modules ─────────────────────────────────────


def test_val008_passes_on_codebase() -> None:
    """Current codebase has no opendrift import outside sim_worker.py."""
    assert check_val008_copyleft(_REPO_ROOT) == []


def test_val008_catches_violation_in_spine(tmp_path: Path) -> None:
    core_dir = tmp_path / "argus" / "core"
    core_dir.mkdir(parents=True)
    (core_dir / "bad.py").write_text("import opendrift\n")
    violations = check_val008_copyleft(tmp_path)
    assert violations
    assert "VAL-008" in violations[0]


def test_val008_permits_opendrift_in_sim_worker(tmp_path: Path) -> None:
    sim_dir = tmp_path / "argus" / "predict" / "oil_trajectory"
    sim_dir.mkdir(parents=True)
    (sim_dir / "sim_worker.py").write_text("import opendrift\n")
    violations = check_val008_copyleft(tmp_path)
    assert violations == []


def test_val008_catches_opendrift_in_predict_non_worker(tmp_path: Path) -> None:
    predict_dir = tmp_path / "argus" / "predict"
    predict_dir.mkdir(parents=True)
    (predict_dir / "runner.py").write_text("import opendrift\n")
    violations = check_val008_copyleft(tmp_path)
    assert violations
    assert "VAL-008" in violations[0]


# ── VAL-010: No live network in unit tests ────────────────────────────────────


def test_val010_passes_on_codebase() -> None:
    """No direct HTTP calls in non-integration test files."""
    assert check_val010_live_network(_REPO_ROOT) == []


def test_val010_catches_requests_get_in_test(tmp_path: Path) -> None:
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    # Split the string to prevent this file from being flagged by the validator itself.
    bad_code = "import requests\n\ndef test_live():\n    requests." + "get('http://example.com')\n"
    (tests_dir / "test_bad.py").write_text(bad_code)
    violations = check_val010_live_network(tmp_path)
    assert violations
    assert "VAL-010" in violations[0]


def test_val010_permits_live_in_integration(tmp_path: Path) -> None:
    integration_dir = tmp_path / "tests" / "integration"
    integration_dir.mkdir(parents=True)
    # Split the string to prevent this file from being flagged by the validator itself.
    live_code = "import requests\n\ndef test_live():\n    requests." + "get('http://example.com')\n"
    (integration_dir / "test_live.py").write_text(live_code)
    violations = check_val010_live_network(tmp_path)
    assert violations == []


def test_val010_permits_mock_spec_usage(tmp_path: Path) -> None:
    """MagicMock(spec=requests.Session) is not a live HTTP call."""
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_mock.py").write_text(
        "from unittest.mock import MagicMock\nimport requests\n"
        "mock = MagicMock(spec=requests.Session)\n"
    )
    violations = check_val010_live_network(tmp_path)
    assert violations == []


# ── VAL-017: No hardcoded oil types ──────────────────────────────────────────


def test_val017_passes_on_codebase() -> None:
    """Current argus/ source has no forbidden hardcoded oil type strings."""
    assert check_val017_hardcoded_oil_type(_REPO_ROOT) == []


def test_val017_catches_crude_oil(tmp_path: Path) -> None:
    argus_dir = tmp_path / "argus"
    argus_dir.mkdir()
    (argus_dir / "bad.py").write_text('oil_type = "crude_oil"\n')
    violations = check_val017_hardcoded_oil_type(tmp_path)
    assert violations
    assert "VAL-017" in violations[0]


def test_val017_catches_generic_oil(tmp_path: Path) -> None:
    argus_dir = tmp_path / "argus"
    argus_dir.mkdir()
    (argus_dir / "bad.py").write_text("OIL = 'generic_oil'\n")
    violations = check_val017_hardcoded_oil_type(tmp_path)
    assert violations
    assert "crude_oil" not in violations[0] or "generic_oil" in violations[0]


def test_val017_catches_diesel(tmp_path: Path) -> None:
    argus_dir = tmp_path / "argus"
    argus_dir.mkdir()
    (argus_dir / "bad.py").write_text("TYPE = 'diesel'\n")
    violations = check_val017_hardcoded_oil_type(tmp_path)
    assert violations


def test_val017_ignores_comments(tmp_path: Path) -> None:
    argus_dir = tmp_path / "argus"
    argus_dir.mkdir()
    (argus_dir / "ok.py").write_text("# never use crude_oil directly\npass\n")
    violations = check_val017_hardcoded_oil_type(tmp_path)
    assert violations == []


def test_val017_ignores_config_dir(tmp_path: Path) -> None:
    """config/ and data/ directories are exempt — they ARE the registry."""
    argus_dir = tmp_path / "argus"
    argus_dir.mkdir()
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "oil_types.yaml").write_text("- crude_oil\n- diesel\n")
    violations = check_val017_hardcoded_oil_type(tmp_path)
    assert violations == []


# ── VAL-001: FR coverage ──────────────────────────────────────────────────────


def test_val001_passes_on_codebase() -> None:
    """Every FR-n in PRD.md §7 is referenced in at least one phase spec."""
    assert check_val001_fr_coverage(_REPO_ROOT) == []


def test_val001_fails_when_prd_missing(tmp_path: Path) -> None:
    (tmp_path / "docs" / "features").mkdir(parents=True)
    violations = check_val001_fr_coverage(tmp_path)
    assert violations
    assert "VAL-001" in violations[0]


# ── VAL-002: Feature has tasks ────────────────────────────────────────────────


def test_val002_passes_on_codebase() -> None:
    """All F-XXX sections in phase specs have acceptance criteria."""
    assert check_val002_feature_has_tasks(_REPO_ROOT) == []


def test_val002_catches_missing_ac(tmp_path: Path) -> None:
    features_dir = tmp_path / "docs" / "features"
    features_dir.mkdir(parents=True)
    (features_dir / "phase-0.md").write_text(
        "## F-000 — Test Feature\n\n**Why:** test.\n\nOwns: nothing.\n"
    )
    violations = check_val002_feature_has_tasks(tmp_path)
    assert violations
    assert "VAL-002" in violations[0]
    assert "F-000" in violations[0]


# ── VAL-013: Acceptance criteria non-empty ───────────────────────────────────


def test_val013_passes_on_codebase() -> None:
    """All acceptance criteria sections in phase specs are non-empty."""
    assert check_val013_acceptance_criteria_non_empty(_REPO_ROOT) == []


def test_val013_catches_empty_ac(tmp_path: Path) -> None:
    features_dir = tmp_path / "docs" / "features"
    features_dir.mkdir(parents=True)
    (features_dir / "phase-0.md").write_text(
        "## F-000 — Test Feature\n\n**Acceptance criteria:**\n\n(none yet)\n"
    )
    violations = check_val013_acceptance_criteria_non_empty(tmp_path)
    assert violations
    assert "VAL-013" in violations[0]


def test_val013_passes_with_bullet_ac(tmp_path: Path) -> None:
    features_dir = tmp_path / "docs" / "features"
    features_dir.mkdir(parents=True)
    (features_dir / "phase-0.md").write_text(
        "## F-000 — Test Feature\n\n**Acceptance criteria:**\n- Test passes\n"
    )
    violations = check_val013_acceptance_criteria_non_empty(tmp_path)
    assert violations == []
