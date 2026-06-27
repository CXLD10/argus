"""F-021 tests: structured logging — JSON format, correlation IDs, no print()."""

from __future__ import annotations

import json
import logging
from io import StringIO
from pathlib import Path

# ── Helpers ───────────────────────────────────────────────────────────────────


def _get_json_logger(name: str) -> tuple[logging.Logger, StringIO]:
    """Return a logger with a JSON formatter writing to a StringIO buffer."""
    from argus.core.logging import _JsonFormatter

    buf = StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(_JsonFormatter())
    logger = logging.getLogger(name)
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    return logger, buf


def _get_text_logger(name: str) -> tuple[logging.Logger, StringIO]:
    """Return a logger with a text formatter writing to a StringIO buffer."""
    from argus.core.logging import _TextFormatter

    buf = StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(_TextFormatter())
    logger = logging.getLogger(name)
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    return logger, buf


# ── get_logger factory ────────────────────────────────────────────────────────


def test_get_logger_returns_logger() -> None:
    from argus.core.logging import get_logger

    log = get_logger("argus.test.factory")
    assert isinstance(log, logging.Logger)


def test_get_logger_name_matches() -> None:
    from argus.core.logging import get_logger

    log = get_logger("argus.test.name")
    assert log.name == "argus.test.name"


# ── JSON format ───────────────────────────────────────────────────────────────


def test_json_output_is_valid_json() -> None:
    logger, buf = _get_json_logger("argus.json.test1")
    logger.info("test_event")
    line = buf.getvalue().strip()
    data = json.loads(line)
    assert isinstance(data, dict)


def test_json_output_has_ts_field() -> None:
    logger, buf = _get_json_logger("argus.json.test2")
    logger.info("test_event")
    data = json.loads(buf.getvalue().strip())
    assert "ts" in data


def test_json_output_has_level_field() -> None:
    logger, buf = _get_json_logger("argus.json.test3")
    logger.info("test_event")
    data = json.loads(buf.getvalue().strip())
    assert data["level"] == "INFO"


def test_json_output_has_module_field() -> None:
    logger, buf = _get_json_logger("argus.json.test4")
    logger.info("test_event")
    data = json.loads(buf.getvalue().strip())
    assert data["module"] == "argus.json.test4"


def test_json_output_has_event_field() -> None:
    logger, buf = _get_json_logger("argus.json.test5")
    logger.info("scene_acquired")
    data = json.loads(buf.getvalue().strip())
    assert data["event"] == "scene_acquired"


def test_json_extra_fields_included() -> None:
    logger, buf = _get_json_logger("argus.json.test6")
    logger.info("scene_acquired", extra={"scene_id": "S1A_123", "bytes": 12345})
    data = json.loads(buf.getvalue().strip())
    assert data.get("scene_id") == "S1A_123"
    assert data.get("bytes") == 12345


def test_json_warning_level() -> None:
    logger, buf = _get_json_logger("argus.json.test7")
    logger.warning("quota_near_limit")
    data = json.loads(buf.getvalue().strip())
    assert data["level"] == "WARNING"


def test_json_ts_format_is_iso8601() -> None:
    logger, buf = _get_json_logger("argus.json.test8")
    logger.info("ts_check")
    data = json.loads(buf.getvalue().strip())
    ts = data["ts"]
    assert ts.endswith("Z"), f"timestamp should end with Z: {ts!r}"
    assert "T" in ts


# ── Correlation IDs ───────────────────────────────────────────────────────────


def test_bind_run_id_appears_in_json_output() -> None:
    from argus.core.logging import bind_run_id

    bind_run_id("run-abc")
    try:
        logger, buf = _get_json_logger("argus.runid.test1")
        logger.info("test_event")
        data = json.loads(buf.getvalue().strip())
        assert data.get("run_id") == "run-abc"
    finally:
        bind_run_id(None)


def test_current_run_id_returns_none_when_unset() -> None:
    from argus.core.logging import bind_run_id, current_run_id

    bind_run_id(None)
    assert current_run_id() is None


def test_bind_run_id_persists_until_cleared() -> None:
    from argus.core.logging import bind_run_id, current_run_id

    bind_run_id("run-xyz")
    try:
        assert current_run_id() == "run-xyz"
        bind_run_id(None)
        assert current_run_id() is None
    finally:
        bind_run_id(None)


def test_no_run_id_field_when_unset() -> None:
    from argus.core.logging import bind_run_id

    bind_run_id(None)
    logger, buf = _get_json_logger("argus.runid.test2")
    logger.info("test_event")
    data = json.loads(buf.getvalue().strip())
    assert "run_id" not in data


# ── Text format ───────────────────────────────────────────────────────────────


def test_text_output_contains_level() -> None:
    logger, buf = _get_text_logger("argus.text.test1")
    logger.info("text_event")
    assert "INFO" in buf.getvalue()


def test_text_output_contains_event() -> None:
    logger, buf = _get_text_logger("argus.text.test2")
    logger.info("scene_acquired")
    assert "scene_acquired" in buf.getvalue()


def test_text_output_contains_module() -> None:
    logger, buf = _get_text_logger("argus.text.test3")
    logger.info("event")
    assert "argus.text.test3" in buf.getvalue()


def test_text_output_contains_extra_fields() -> None:
    logger, buf = _get_text_logger("argus.text.test4")
    logger.info("event", extra={"scene_id": "S1A_abc"})
    assert "scene_id=S1A_abc" in buf.getvalue()


# ── No print() in argus/ ──────────────────────────────────────────────────────


def test_no_print_statements_in_argus_source() -> None:
    """AC: No print() in argus/ production code (structured logging only)."""
    import re

    argus_root = Path(__file__).parent.parent / "argus"
    print_pattern = re.compile(r"(?<!\w)print\s*\(")
    violations = []
    for py_file in argus_root.rglob("*.py"):
        text = py_file.read_text()
        for i, line in enumerate(text.splitlines(), 1):
            if line.strip().startswith("#"):
                continue
            if print_pattern.search(line):
                violations.append(f"{py_file}:{i}: {line.strip()}")
    assert not violations, "print() found in argus/ production code:\n" + "\n".join(violations)
