"""SQLite-backed store for Argus entities (INV-6: sole DB access point).

All database access in the application must go through this module.
No other module may import sqlite3 directly.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from argus.core.models import AnalysisRun, Observation, Scene


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
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analysis_runs (
                    id              TEXT PRIMARY KEY,
                    aoi_id          TEXT NOT NULL,
                    domain_id       TEXT NOT NULL,
                    scene_id        TEXT NOT NULL,
                    started_at      TEXT NOT NULL,
                    completed_at    TEXT,
                    status          TEXT NOT NULL DEFAULT 'running',
                    n_observations  INTEGER NOT NULL DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS skill_reports (
                    id              TEXT PRIMARY KEY,
                    predictor_id    TEXT NOT NULL,
                    eval_case_id    TEXT NOT NULL,
                    precision       REAL NOT NULL,
                    recall          REAL NOT NULL,
                    f1              REAL NOT NULL,
                    n_observations  INTEGER NOT NULL,
                    created_at      TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS observations (
                    id               TEXT PRIMARY KEY,
                    analysis_run_id  TEXT NOT NULL,
                    scene_id         TEXT NOT NULL,
                    obs_type         TEXT NOT NULL,
                    evidence_class   TEXT NOT NULL,
                    geometry         TEXT NOT NULL,
                    area_km2         REAL NOT NULL,
                    confidence       REAL NOT NULL,
                    status           TEXT NOT NULL DEFAULT 'candidate',
                    attrs            TEXT NOT NULL DEFAULT '{}',
                    created_at       TEXT NOT NULL
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

    # ── AnalysisRun CRUD ──────────────────────────────────────────────────────

    def save_analysis_run(self, run: AnalysisRun) -> None:
        """Insert or replace an AnalysisRun record."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO analysis_runs
                    (id, aoi_id, domain_id, scene_id, started_at,
                     completed_at, status, n_observations)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.id,
                    run.aoi_id,
                    run.domain_id,
                    run.scene_id,
                    run.started_at.isoformat(),
                    run.completed_at.isoformat() if run.completed_at else None,
                    run.status,
                    run.n_observations,
                ),
            )

    def get_analysis_run(self, run_id: str) -> AnalysisRun | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM analysis_runs WHERE id = ?", (run_id,)).fetchone()
        return _row_to_run(row) if row else None

    # ── Observation CRUD ──────────────────────────────────────────────────────

    def save_observation(self, obs: Observation) -> None:
        """Insert or replace an Observation record."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO observations
                    (id, analysis_run_id, scene_id, obs_type, evidence_class,
                     geometry, area_km2, confidence, status, attrs, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    obs.id,
                    obs.analysis_run_id,
                    obs.scene_id,
                    obs.obs_type,
                    obs.evidence_class,
                    json.dumps(obs.geometry),
                    obs.area_km2,
                    obs.confidence,
                    obs.status,
                    json.dumps(obs.attrs),
                    obs.created_at.isoformat(),
                ),
            )

    def get_observation(self, obs_id: str) -> Observation | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM observations WHERE id = ?", (obs_id,)).fetchone()
        return _row_to_obs(row) if row else None

    def get_observations_for_run(self, run_id: str) -> list[Observation]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM observations WHERE analysis_run_id = ?", (run_id,)
            ).fetchall()
        return [_row_to_obs(r) for r in rows]

    # ── SkillReport CRUD (scaffold — gating UI is F-029) ─────────────────────

    def save_skill_report(
        self,
        report_id: str,
        predictor_id: str,
        eval_case_id: str,
        precision: float,
        recall: float,
        f1: float,
        n_observations: int,
        created_at: datetime,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO skill_reports
                    (id, predictor_id, eval_case_id, precision, recall, f1,
                     n_observations, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report_id,
                    predictor_id,
                    eval_case_id,
                    precision,
                    recall,
                    f1,
                    n_observations,
                    created_at.isoformat(),
                ),
            )

    def get_skill_reports_for_case(self, eval_case_id: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM skill_reports WHERE eval_case_id = ?",
                (eval_case_id,),
            ).fetchall()
        return [dict(r) for r in rows]

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


def _row_to_run(row: sqlite3.Row) -> AnalysisRun:
    return AnalysisRun(
        id=row["id"],
        aoi_id=row["aoi_id"],
        domain_id=row["domain_id"],
        scene_id=row["scene_id"],
        started_at=datetime.fromisoformat(row["started_at"]),
        completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
        status=row["status"],
        n_observations=row["n_observations"],
    )


def _row_to_obs(row: sqlite3.Row) -> Observation:
    return Observation(
        id=row["id"],
        analysis_run_id=row["analysis_run_id"],
        scene_id=row["scene_id"],
        obs_type=row["obs_type"],
        evidence_class=row["evidence_class"],
        geometry=json.loads(row["geometry"]),
        area_km2=row["area_km2"],
        confidence=row["confidence"],
        status=row["status"],
        attrs=json.loads(row["attrs"]),
        created_at=datetime.fromisoformat(row["created_at"]),
    )
