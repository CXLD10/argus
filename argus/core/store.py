"""SQLite-backed store for Argus entities (INV-6: sole DB access point).

All database access in the application must go through this module.
No other module may import sqlite3 directly.
"""

from __future__ import annotations

import contextlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from argus.core.models import (
    AnalysisRun,
    ChokePoint,
    ExposureLayer,
    ForecastFrame,
    ImpactAssessment,
    Observation,
    Prediction,
    RunHistory,
    Scene,
)


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
                    status_updated_at TEXT,
                    features         TEXT,
                    domain           TEXT,
                    target_id        TEXT,
                    value            REAL,
                    unit             TEXT,
                    attrs            TEXT NOT NULL DEFAULT '{}',
                    created_at       TEXT NOT NULL
                )
            """)
            # Idempotent column additions for existing DBs.
            for _stmt in (
                "ALTER TABLE observations ADD COLUMN status_updated_at TEXT",
                "ALTER TABLE observations ADD COLUMN features TEXT",
                "ALTER TABLE observations ADD COLUMN domain TEXT",
                "ALTER TABLE observations ADD COLUMN target_id TEXT",
                "ALTER TABLE observations ADD COLUMN value REAL",
                "ALTER TABLE observations ADD COLUMN unit TEXT",
                # F-029: skill gate column
                "ALTER TABLE skill_reports ADD COLUMN passed_gate INTEGER NOT NULL DEFAULT 0",
            ):
                with contextlib.suppress(sqlite3.OperationalError):
                    conn.execute(_stmt)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS predictions (
                    id              TEXT PRIMARY KEY,
                    predictor_id    TEXT NOT NULL,
                    source_obs_ids  TEXT NOT NULL DEFAULT '[]',
                    kind            TEXT NOT NULL,
                    evidence_class  TEXT NOT NULL DEFAULT 'modeled',
                    uncertainty     TEXT NOT NULL DEFAULT '{}',
                    rng_seed        INTEGER,
                    attrs           TEXT NOT NULL DEFAULT '{}',
                    created_at      TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS forecast_frames (
                    id              TEXT PRIMARY KEY,
                    prediction_id   TEXT NOT NULL,
                    valid_at        TEXT NOT NULL,
                    footprint       TEXT NOT NULL,
                    grid_ref        TEXT,
                    particle_count  INTEGER NOT NULL DEFAULT 0,
                    stats           TEXT NOT NULL DEFAULT '{}'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS exposure_layers (
                    id          TEXT PRIMARY KEY,
                    name        TEXT NOT NULL,
                    layer_type  TEXT NOT NULL,
                    geometry    TEXT NOT NULL,
                    attrs       TEXT NOT NULL DEFAULT '{}',
                    created_at  TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS impact_assessments (
                    id                  TEXT PRIMARY KEY,
                    prediction_id       TEXT NOT NULL,
                    exposure_layer_id   TEXT NOT NULL,
                    valid_at            TEXT NOT NULL,
                    eta_hours           REAL NOT NULL,
                    metrics             TEXT NOT NULL DEFAULT '{}',
                    created_at          TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS choke_points (
                    id                  TEXT PRIMARY KEY,
                    aoi_id              TEXT NOT NULL,
                    location            TEXT NOT NULL,
                    upstream_area_km2   REAL NOT NULL,
                    constriction_score  REAL NOT NULL,
                    dem_source          TEXT NOT NULL DEFAULT 'cop_glo30',
                    evidence_class      TEXT NOT NULL DEFAULT 'inferred',
                    created_at          TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS run_history (
                    id                  TEXT PRIMARY KEY,
                    domain_id           TEXT NOT NULL,
                    aoi_id              TEXT NOT NULL,
                    t_start             TEXT NOT NULL,
                    t_end               TEXT NOT NULL,
                    scenes_fetched      INTEGER NOT NULL DEFAULT 0,
                    observations_created INTEGER NOT NULL DEFAULT 0,
                    bytes_used          INTEGER NOT NULL DEFAULT 0,
                    status              TEXT NOT NULL DEFAULT 'complete',
                    error               TEXT,
                    created_at          TEXT NOT NULL
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

    def get_scene_by_product_id(self, product_id: str) -> Scene | None:
        """Return the most recent Scene for a given product_id, or None.

        Used by acquire_scene() to skip re-downloading already-acquired products
        (idempotency rule from F-038).
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM scenes WHERE product_id = ? ORDER BY created_at DESC LIMIT 1",
                (product_id,),
            ).fetchone()
        return _row_to_scene(row) if row else None

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
                     geometry, area_km2, confidence, status, status_updated_at,
                     features, domain, target_id, value, unit, attrs, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    obs.status_updated_at.isoformat() if obs.status_updated_at else None,
                    json.dumps(obs.features) if obs.features is not None else None,
                    obs.domain,
                    obs.target_id,
                    obs.value,
                    obs.unit,
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

    def get_observations_by_target(
        self,
        target_id: str,
        *,
        since: datetime | None = None,
        obs_types: list[str] | None = None,
    ) -> list[Observation]:
        """Return Observations for a specific target, ordered newest-first."""
        query = "SELECT * FROM observations WHERE target_id = ?"
        params: list[object] = [target_id]
        if since is not None:
            query += " AND created_at >= ?"
            params.append(since.isoformat())
        if obs_types:
            placeholders = ",".join("?" * len(obs_types))
            query += f" AND obs_type IN ({placeholders})"
            params.extend(obs_types)
        query += " ORDER BY created_at DESC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [_row_to_obs(r) for r in rows]

    def transition_observation_status(
        self,
        obs_id: str,
        new_status: str,
        *,
        updated_at: datetime | None = None,
    ) -> None:
        """Move an Observation from candidate to confirmed or dismissed, recording the timestamp."""
        ts = (updated_at or datetime.now(UTC)).isoformat()
        with self._connect() as conn:
            conn.execute(
                "UPDATE observations SET status = ?, status_updated_at = ? WHERE id = ?",
                (new_status, ts, obs_id),
            )

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
        passed_gate: bool = False,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO skill_reports
                    (id, predictor_id, eval_case_id, precision, recall, f1,
                     n_observations, created_at, passed_gate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    int(passed_gate),
                ),
            )

    def get_skill_reports_for_case(self, eval_case_id: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM skill_reports WHERE eval_case_id = ?",
                (eval_case_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_skill_reports_by_predictor(self, predictor_id: str) -> list[dict]:
        """Return all SkillReports for a predictor, sorted by created_at ascending."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM skill_reports WHERE predictor_id = ? ORDER BY created_at ASC",
                (predictor_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Prediction CRUD (scaffold — F-011) ───────────────────────────────────

    def save_prediction(self, pred: Prediction) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO predictions
                    (id, predictor_id, source_obs_ids, kind, evidence_class,
                     uncertainty, rng_seed, attrs, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pred.id,
                    pred.predictor_id,
                    json.dumps(pred.source_obs_ids),
                    pred.kind,
                    pred.evidence_class,
                    json.dumps(pred.uncertainty),
                    pred.rng_seed,
                    json.dumps(pred.attrs),
                    pred.created_at.isoformat(),
                ),
            )

    def get_prediction(self, pred_id: str) -> Prediction | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM predictions WHERE id = ?", (pred_id,)).fetchone()
        return _row_to_prediction(row) if row else None

    def get_predictions_by_kind(self, kind: str) -> list[Prediction]:
        """Return all Predictions with the specified kind, sorted by created_at ascending."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM predictions WHERE kind = ? ORDER BY created_at ASC",
                (kind,),
            ).fetchall()
        return [_row_to_prediction(r) for r in rows]

    def get_predictions_for_target(
        self,
        target_id: str,
        kind: str | None = None,
    ) -> list[Prediction]:
        """Return Predictions whose source observations include any obs for *target_id*.

        Avoids adding target_id to the predictions table by resolving via the
        observations table. Returns predictions sorted by created_at ascending.
        """
        obs_rows = self.get_observations_by_target(target_id)
        if not obs_rows:
            return []
        obs_ids = {o.id for o in obs_rows}
        candidates = self.get_predictions_by_kind(kind) if kind else self._get_all_predictions()
        return [p for p in candidates if any(sid in obs_ids for sid in p.source_obs_ids)]

    def _get_all_predictions(self) -> list[Prediction]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM predictions ORDER BY created_at ASC"
            ).fetchall()
        return [_row_to_prediction(r) for r in rows]

    def get_waterbody_targets(self) -> list[str]:
        """Return distinct target_ids from WQ domain observations (inland_wq)."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT target_id FROM observations "
                "WHERE domain = 'inland_wq' AND target_id IS NOT NULL "
                "ORDER BY target_id"
            ).fetchall()
        return [r[0] for r in rows]

    # ── ForecastFrame CRUD (scaffold — F-011) ────────────────────────────────

    def save_forecast_frame(self, frame: ForecastFrame) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO forecast_frames
                    (id, prediction_id, valid_at, footprint, grid_ref, particle_count, stats)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    frame.id,
                    frame.prediction_id,
                    frame.valid_at.isoformat(),
                    json.dumps(frame.footprint),
                    frame.grid_ref,
                    frame.particle_count,
                    json.dumps(frame.stats),
                ),
            )

    def get_forecast_frames_for_prediction(self, pred_id: str) -> list[ForecastFrame]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM forecast_frames WHERE prediction_id = ?", (pred_id,)
            ).fetchall()
        return [_row_to_frame(r) for r in rows]

    # ── ExposureLayer CRUD ────────────────────────────────────────────────────

    def save_exposure_layer(self, layer: ExposureLayer) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO exposure_layers
                    (id, name, layer_type, geometry, attrs, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    layer.id,
                    layer.name,
                    layer.layer_type,
                    json.dumps(layer.geometry),
                    json.dumps(layer.attrs),
                    layer.created_at.isoformat(),
                ),
            )

    def get_exposure_layers(self) -> list[ExposureLayer]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM exposure_layers").fetchall()
        return [_row_to_exposure_layer(r) for r in rows]

    # ── ImpactAssessment CRUD ─────────────────────────────────────────────────

    def save_impact_assessment(self, ia: ImpactAssessment) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO impact_assessments
                    (id, prediction_id, exposure_layer_id, valid_at, eta_hours,
                     metrics, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ia.id,
                    ia.prediction_id,
                    ia.exposure_layer_id,
                    ia.valid_at.isoformat(),
                    ia.eta_hours,
                    json.dumps(ia.metrics),
                    ia.created_at.isoformat(),
                ),
            )

    def get_impact_assessments_for_prediction(self, pred_id: str) -> list[ImpactAssessment]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM impact_assessments WHERE prediction_id = ?", (pred_id,)
            ).fetchall()
        return [_row_to_impact_assessment(r) for r in rows]

    # ── ChokePoint CRUD (F-040) ───────────────────────────────────────────────

    def save_choke_point(self, cp: ChokePoint) -> None:
        """Persist a ChokePoint (INSERT OR REPLACE)."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO choke_points
                    (id, aoi_id, location, upstream_area_km2, constriction_score,
                     dem_source, evidence_class, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cp.id,
                    cp.aoi_id,
                    json.dumps(cp.location),
                    cp.upstream_area_km2,
                    cp.constriction_score,
                    cp.dem_source,
                    cp.evidence_class,
                    cp.created_at.isoformat(),
                ),
            )

    def get_choke_points(self, aoi_id: str) -> list[ChokePoint]:
        """Return all ChokePoints for a given AOI, sorted by constriction_score descending."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM choke_points WHERE aoi_id = ? ORDER BY constriction_score DESC",
                (aoi_id,),
            ).fetchall()
        return [_row_to_choke_point(r) for r in rows]

    # ── RunHistory CRUD (F-038) ───────────────────────────────────────────────

    def save_run_history(self, run: RunHistory) -> None:
        """Persist a RunHistory record (idempotent — INSERT OR REPLACE)."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO run_history
                    (id, domain_id, aoi_id, t_start, t_end,
                     scenes_fetched, observations_created, bytes_used,
                     status, error, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.id,
                    run.domain_id,
                    run.aoi_id,
                    run.t_start.isoformat(),
                    run.t_end.isoformat(),
                    run.scenes_fetched,
                    run.observations_created,
                    run.bytes_used,
                    run.status,
                    run.error,
                    run.created_at.isoformat(),
                ),
            )

    def get_run_history(
        self,
        domain_id: str | None = None,
        aoi_id: str | None = None,
        *,
        limit: int = 100,
    ) -> list[RunHistory]:
        """Return run history records, newest first. Optionally filter by domain and/or AOI."""
        query = "SELECT * FROM run_history"
        params: list[object] = []
        clauses: list[str] = []
        if domain_id:
            clauses.append("domain_id = ?")
            params.append(domain_id)
        if aoi_id:
            clauses.append("aoi_id = ?")
            params.append(aoi_id)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at DESC"
        if limit:
            query += f" LIMIT {int(limit)}"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [_row_to_run_history(r) for r in rows]

    def get_last_run_for_domain(self, domain_id: str, aoi_id: str) -> RunHistory | None:
        """Return the most recent successful RunHistory for a domain×AOI pair."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM run_history WHERE domain_id = ? AND aoi_id = ? "
                "AND status = 'complete' ORDER BY created_at DESC LIMIT 1",
                (domain_id, aoi_id),
            ).fetchone()
        return _row_to_run_history(row) if row else None

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

    def open_meteo_calls_today(self, on: datetime) -> int:
        """Sum of bytes_used from weather_hydro RunHistory records created today.

        For the weather domain, RunHistory.bytes_used records API call count rather
        than byte count (same field, different unit by convention).
        """
        date_prefix = on.astimezone(UTC).strftime("%Y-%m-%d")
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(bytes_used), 0) FROM run_history "
                "WHERE domain_id = 'weather_hydro' AND SUBSTR(created_at, 1, 10) = ?",
                (date_prefix,),
            ).fetchone()
        return int(row[0]) if row else 0

    def ping(self) -> bool:
        """Return True if the store is accessible; raise on any error."""
        with self._connect() as conn:
            conn.execute("SELECT 1")
        return True

    def get_last_analysis_run_at(self) -> datetime | None:
        """Return the started_at of the most recent AnalysisRun, or None if empty."""
        with self._connect() as conn:
            row = conn.execute("SELECT MAX(started_at) FROM analysis_runs").fetchone()
        if row and row[0]:
            return datetime.fromisoformat(row[0])
        return None


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
    row_dict = dict(row)
    return Observation(
        id=row_dict["id"],
        analysis_run_id=row_dict["analysis_run_id"],
        scene_id=row_dict["scene_id"],
        obs_type=row_dict["obs_type"],
        evidence_class=row_dict["evidence_class"],
        geometry=json.loads(row_dict["geometry"]),
        area_km2=row_dict["area_km2"],
        confidence=row_dict["confidence"],
        status=row_dict["status"],
        status_updated_at=(
            datetime.fromisoformat(row_dict["status_updated_at"])
            if row_dict.get("status_updated_at")
            else None
        ),
        features=(
            json.loads(row_dict["features"]) if row_dict.get("features") is not None else None
        ),
        domain=row_dict.get("domain"),
        target_id=row_dict.get("target_id"),
        value=row_dict.get("value"),
        unit=row_dict.get("unit"),
        attrs=json.loads(row_dict["attrs"]),
        created_at=datetime.fromisoformat(row_dict["created_at"]),
    )


def _row_to_prediction(row: sqlite3.Row) -> Prediction:
    return Prediction(
        id=row["id"],
        predictor_id=row["predictor_id"],
        source_obs_ids=json.loads(row["source_obs_ids"]),
        kind=row["kind"],
        evidence_class=row["evidence_class"],
        uncertainty=json.loads(row["uncertainty"]),
        rng_seed=row["rng_seed"],
        attrs=json.loads(row["attrs"]),
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def _row_to_frame(row: sqlite3.Row) -> ForecastFrame:
    return ForecastFrame(
        id=row["id"],
        prediction_id=row["prediction_id"],
        valid_at=datetime.fromisoformat(row["valid_at"]),
        footprint=json.loads(row["footprint"]),
        grid_ref=row["grid_ref"],
        particle_count=row["particle_count"],
        stats=json.loads(row["stats"]),
    )


def _row_to_exposure_layer(row: sqlite3.Row) -> ExposureLayer:
    return ExposureLayer(
        id=row["id"],
        name=row["name"],
        layer_type=row["layer_type"],
        geometry=json.loads(row["geometry"]),
        attrs=json.loads(row["attrs"]),
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def _row_to_impact_assessment(row: sqlite3.Row) -> ImpactAssessment:
    return ImpactAssessment(
        id=row["id"],
        prediction_id=row["prediction_id"],
        exposure_layer_id=row["exposure_layer_id"],
        valid_at=datetime.fromisoformat(row["valid_at"]),
        eta_hours=row["eta_hours"],
        metrics=json.loads(row["metrics"]),
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def _row_to_choke_point(row: sqlite3.Row) -> ChokePoint:
    return ChokePoint(
        id=row["id"],
        aoi_id=row["aoi_id"],
        location=json.loads(row["location"]),
        upstream_area_km2=row["upstream_area_km2"],
        constriction_score=row["constriction_score"],
        dem_source=row["dem_source"],
        evidence_class=row["evidence_class"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def _row_to_run_history(row: sqlite3.Row) -> RunHistory:
    return RunHistory(
        id=row["id"],
        domain_id=row["domain_id"],
        aoi_id=row["aoi_id"],
        t_start=datetime.fromisoformat(row["t_start"]),
        t_end=datetime.fromisoformat(row["t_end"]),
        scenes_fetched=row["scenes_fetched"],
        observations_created=row["observations_created"],
        bytes_used=row["bytes_used"],
        status=row["status"],
        error=row["error"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )
