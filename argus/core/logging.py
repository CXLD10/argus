"""Structured logging for Argus.

Provides a factory function that returns a stdlib Logger pre-configured for
either structured JSON output (LOG_FORMAT=json) or plain text (default).

Usage:
    from argus.core.logging import get_logger
    log = get_logger(__name__)
    log.info("scene_acquired", extra={"scene_id": "S1A_...", "bytes": 12345})

JSON format (set LOG_FORMAT=json):
    {"ts":"2024-02-07T12:00:00.000Z","level":"INFO","module":"argus.ingest",
     "run_id":"abc123","event":"scene_acquired","scene_id":"S1A_...","bytes":12345}

Correlation IDs:
    Thread-local run_id is set via bind_run_id(). All loggers read it
    automatically. Call bind_run_id(None) to clear.

Text format (default):
    2024-02-07 12:00:00 INFO argus.ingest: scene_acquired scene_id=S1A_...
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import UTC, datetime

# ── Thread-local run_id store ─────────────────────────────────────────────────

_local = threading.local()


def bind_run_id(run_id: str | None) -> None:
    """Set the correlation run_id for all subsequent log calls in this thread."""
    _local.run_id = run_id


def current_run_id() -> str | None:
    """Return the current thread-local run_id, or None if not set."""
    return getattr(_local, "run_id", None)


# ── JSON formatter ────────────────────────────────────────────────────────────


class _JsonFormatter(logging.Formatter):
    """Emit one JSON object per log record."""

    def format(self, record: logging.LogRecord) -> str:
        # Base fields
        payload: dict = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).strftime(
                "%Y-%m-%dT%H:%M:%S.%f"
            )[:-3]
            + "Z",
            "level": record.levelname,
            "module": record.name,
        }

        # Correlation ID
        run_id = current_run_id()
        if run_id is not None:
            payload["run_id"] = run_id

        # Event: use the log message as the event name
        payload["event"] = record.getMessage()

        # Extra fields passed via extra={}
        _SKIP = {
            "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
            "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
            "created", "msecs", "relativeCreated", "thread", "threadName",
            "processName", "process", "taskName", "message",
        }
        for key, value in record.__dict__.items():
            if key not in _SKIP and not key.startswith("_"):
                payload[key] = value

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


# ── Text formatter ────────────────────────────────────────────────────────────


class _TextFormatter(logging.Formatter):
    """Compact human-readable format for development."""

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, tz=UTC).strftime("%Y-%m-%d %H:%M:%S")
        parts = [f"{ts} {record.levelname} {record.name}: {record.getMessage()}"]

        # Extra fields
        _SKIP = {
            "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
            "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
            "created", "msecs", "relativeCreated", "thread", "threadName",
            "processName", "process", "taskName", "message",
        }
        extras = {
            k: v for k, v in record.__dict__.items() if k not in _SKIP and not k.startswith("_")
        }
        if extras:
            parts.append(" ".join(f"{k}={v}" for k, v in extras.items()))

        run_id = current_run_id()
        if run_id:
            parts.append(f"run_id={run_id}")

        return " ".join(parts)


# ── Logger factory ────────────────────────────────────────────────────────────

_LOG_FORMAT = os.environ.get("LOG_FORMAT", "text").lower()
_configured: set[str] = set()


def get_logger(name: str) -> logging.Logger:
    """Return a Logger for *name*, configured for structured or text output.

    The format is controlled by the LOG_FORMAT environment variable:
    - ``LOG_FORMAT=json`` → one JSON object per line
    - anything else → human-readable text (default)

    Call this once at module level:
        log = get_logger(__name__)
    """
    logger = logging.getLogger(name)

    if name not in _configured:
        _configured.add(name)
        handler = logging.StreamHandler()
        if _LOG_FORMAT == "json":
            handler.setFormatter(_JsonFormatter())
        else:
            handler.setFormatter(_TextFormatter())
        # Avoid adding duplicate handlers if the root logger already has one
        if not logger.handlers:
            logger.addHandler(handler)
        logger.propagate = False
        if not logger.level:
            logger.setLevel(logging.INFO)

    return logger
