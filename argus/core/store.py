"""SQLite-backed store for Argus entities (INV-6: sole DB access point).

All database access in the application must go through this module.
No other module may import sqlite3 directly.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from argus.core.models import Scene


class Store:
    """Manages the Argus SQLite database: schema bootstrap and entity CRUD."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._bootstrap()

    # ── Schema ────────────────────────────────────────────────────────────────

    def _bootstrap(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scenes (
                    id            TEXT PRIMARY KEY,
                    product_id    TEXT NOT NULL,
                    aoi_id        TEXT NOT NULL,
                    sensing_time  TEXT NOT NULL,
                    ingest_status TEXT NOT NULL,
                    artifact_path TEXT,
                    bytes_or_calls INTEGER NOT NULL DEFAULT 0,
                    created_at    TEXT NOT NULL,
                    attrs         TEXT NOT NULL DEFAULT '{}'
                )
            """)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ── Scene CRUD ────────────────────────────────────────────────────────────

    def save_scene(self, scene: Scene) -> None:
        """Insert or replace a Scene record."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO scenes
                    (id, product_id, aoi_id, sensing_time, ingest_status,
                     artifact_path, bytes_or_calls, created_at, attrs)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    scene.id,
                    scene.product_id,
                    scene.aoi_id,
                    scene.sensing_time.isoformat(),
                    scene.ingest_status,
                    scene.artifact_path,
                    scene.bytes_or_calls,
                    scene.created_at.isoformat(),
                    json.dumps(scene.attrs),
                ),
            )

    def get_scene(self, scene_id: str) -> Scene | None:
        """Return the Scene with the given id, or None if not found."""
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM scenes WHERE id = ?", (scene_id,)).fetchone()
        if row is None:
            return None
        return _row_to_scene(row)

    # ── Quota helpers ─────────────────────────────────────────────────────────

    def daily_bytes_total(self, on: datetime) -> int:
        """Sum of bytes_or_calls for all scenes created on the same UTC date as *on*."""
        date_prefix = on.astimezone(UTC).strftime("%Y-%m-%d")
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(bytes_or_calls), 0) FROM scenes "
                "WHERE SUBSTR(created_at, 1, 10) = ?",
                (date_prefix,),
            ).fetchone()
        return int(row[0]) if row else 0


def _row_to_scene(row: sqlite3.Row) -> Scene:
    return Scene(
        id=row["id"],
        product_id=row["product_id"],
        aoi_id=row["aoi_id"],
        sensing_time=datetime.fromisoformat(row["sensing_time"]),
        ingest_status=row["ingest_status"],
        artifact_path=row["artifact_path"],
        bytes_or_calls=row["bytes_or_calls"],
        created_at=datetime.fromisoformat(row["created_at"]),
        attrs=json.loads(row["attrs"]),
    )
