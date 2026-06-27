"""F-010 tests: Observation schema finalization, status transitions, obs_type validation."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from argus.core.models import VALID_OBS_TYPES, Observation
from argus.core.store import Store

# ── Helpers ───────────────────────────────────────────────────────────────────

_POINT_GEOM = {"type": "Point", "coordinates": [-61.0, 11.0]}


def _make_obs(
    *,
    obs_id: str = "obs-001",
    obs_type: str = "oil_slick",
    status: str = "candidate",
    analysis_run_id: str = "run-001",
    scene_id: str = "scene-001",
) -> Observation:
    return Observation(
        id=obs_id,
        analysis_run_id=analysis_run_id,
        scene_id=scene_id,
        obs_type=obs_type,
        evidence_class="measured",
        geometry=_POINT_GEOM,
        area_km2=10.0,
        confidence=0.7,
        status=status,  # type: ignore[arg-type]
    )


# ── obs_type validation ───────────────────────────────────────────────────────


@pytest.mark.parametrize("obs_type", sorted(VALID_OBS_TYPES))
def test_all_valid_obs_types_accepted(obs_type: str) -> None:
    obs = _make_obs(obs_type=obs_type)
    assert obs.obs_type == obs_type


def test_invalid_obs_type_raises_validation_error() -> None:
    with pytest.raises(Exception, match="not in registered types"):
        _make_obs(obs_type="plankton_bloom")


def test_valid_obs_types_set_non_empty() -> None:
    assert len(VALID_OBS_TYPES) >= 6


# ── evidence_class validation ─────────────────────────────────────────────────


@pytest.mark.parametrize("ec", ["measured", "modeled", "inferred"])
def test_all_valid_evidence_classes_accepted(ec: str) -> None:
    obs = Observation(
        id="obs-ec",
        analysis_run_id="run-ec",
        scene_id="scene-ec",
        obs_type="oil_slick",
        evidence_class=ec,  # type: ignore[arg-type]
        geometry=_POINT_GEOM,
        area_km2=1.0,
        confidence=0.5,
    )
    assert obs.evidence_class == ec


def test_invalid_evidence_class_raises() -> None:
    with pytest.raises(ValueError):
        Observation(
            id="obs-bad",
            analysis_run_id="run-bad",
            scene_id="scene-bad",
            obs_type="oil_slick",
            evidence_class="guessed",  # type: ignore[arg-type]
            geometry=_POINT_GEOM,
            area_km2=1.0,
            confidence=0.5,
        )


# ── new optional schema fields ────────────────────────────────────────────────


def test_features_field_default_none() -> None:
    obs = _make_obs()
    assert obs.features is None


def test_features_field_populated() -> None:
    obs = Observation(
        id="obs-feats",
        analysis_run_id="run-feats",
        scene_id="scene-feats",
        obs_type="oil_slick",
        evidence_class="measured",
        geometry=_POINT_GEOM,
        area_km2=5.0,
        confidence=0.8,
        features={"area_km2": 5.0, "contrast_vs_background_db": 12.0},
    )
    assert obs.features is not None
    assert obs.features["contrast_vs_background_db"] == pytest.approx(12.0)


def test_status_updated_at_default_none() -> None:
    obs = _make_obs()
    assert obs.status_updated_at is None


def test_domain_target_value_unit_defaults_none() -> None:
    obs = _make_obs()
    assert obs.domain is None
    assert obs.target_id is None
    assert obs.value is None
    assert obs.unit is None


# ── status transitions round-trip ─────────────────────────────────────────────


def test_status_transition_candidate_to_confirmed(tmp_path: Path) -> None:
    store = Store(tmp_path / "argus.db")
    obs = _make_obs(status="candidate")
    store.save_observation(obs)

    ts = datetime(2024, 3, 1, 12, 0, tzinfo=UTC)
    store.transition_observation_status(obs.id, "confirmed", updated_at=ts)

    retrieved = store.get_observation(obs.id)
    assert retrieved is not None
    assert retrieved.status == "confirmed"
    assert retrieved.status_updated_at is not None
    assert retrieved.status_updated_at.replace(tzinfo=UTC) == ts


def test_status_transition_candidate_to_dismissed(tmp_path: Path) -> None:
    store = Store(tmp_path / "argus.db")
    obs = _make_obs(status="candidate")
    store.save_observation(obs)
    store.transition_observation_status(obs.id, "dismissed")
    retrieved = store.get_observation(obs.id)
    assert retrieved is not None
    assert retrieved.status == "dismissed"


def test_mixed_statuses_in_run(tmp_path: Path) -> None:
    store = Store(tmp_path / "argus.db")
    confirmed = _make_obs(obs_id="obs-c", status="confirmed")
    dismissed = _make_obs(obs_id="obs-d", status="dismissed")
    candidate = _make_obs(obs_id="obs-k", status="candidate")
    for obs in (confirmed, dismissed, candidate):
        store.save_observation(obs)

    observations = store.get_observations_for_run("run-001")
    statuses = {o.id: o.status for o in observations}
    assert statuses["obs-c"] == "confirmed"
    assert statuses["obs-d"] == "dismissed"
    assert statuses["obs-k"] == "candidate"


# ── features round-trip in store ─────────────────────────────────────────────


def test_features_round_trip(tmp_path: Path) -> None:
    store = Store(tmp_path / "argus.db")
    feats = {"area_km2": 8.5, "contrast_vs_background_db": 13.2, "texture_glcm": 0.04}
    obs = Observation(
        id="obs-feats-rt",
        analysis_run_id="run-feats-rt",
        scene_id="scene-feats-rt",
        obs_type="oil_slick",
        evidence_class="measured",
        geometry=_POINT_GEOM,
        area_km2=8.5,
        confidence=0.85,
        features=feats,
    )
    store.save_observation(obs)
    retrieved = store.get_observation("obs-feats-rt")
    assert retrieved is not None
    assert retrieved.features is not None
    assert retrieved.features["contrast_vs_background_db"] == pytest.approx(13.2)


def test_status_updated_at_round_trip(tmp_path: Path) -> None:
    ts = datetime(2024, 5, 10, 8, 30, tzinfo=UTC)
    store = Store(tmp_path / "argus.db")
    obs = Observation(
        id="obs-ts-rt",
        analysis_run_id="run-ts-rt",
        scene_id="scene-ts-rt",
        obs_type="oil_slick",
        evidence_class="measured",
        geometry=_POINT_GEOM,
        area_km2=3.0,
        confidence=0.6,
        status="confirmed",
        status_updated_at=ts,
    )
    store.save_observation(obs)
    retrieved = store.get_observation("obs-ts-rt")
    assert retrieved is not None
    assert retrieved.status_updated_at is not None
    # Compare ignoring tz info (SQLite stores naive ISO strings)
    assert retrieved.status_updated_at.replace(tzinfo=UTC) == ts


# ── migration / schema check ──────────────────────────────────────────────────


_EXPECTED_OBSERVATION_COLUMNS = {
    "id",
    "analysis_run_id",
    "scene_id",
    "obs_type",
    "evidence_class",
    "geometry",
    "area_km2",
    "confidence",
    "status",
    "status_updated_at",
    "features",
    "domain",
    "target_id",
    "value",
    "unit",
    "attrs",
    "created_at",
}


def test_fresh_db_has_all_observation_columns(tmp_path: Path) -> None:
    Store(tmp_path / "argus.db")
    conn = sqlite3.connect(tmp_path / "argus.db")
    pragma = conn.execute("PRAGMA table_info(observations)").fetchall()
    conn.close()
    actual_columns = {row[1] for row in pragma}
    assert actual_columns == _EXPECTED_OBSERVATION_COLUMNS


def test_existing_db_upgraded_with_new_columns(tmp_path: Path) -> None:
    """Re-opening an old-schema DB adds new columns without error."""
    db_path = tmp_path / "argus.db"
    # Create a DB with the old minimal schema.
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE observations (
            id TEXT PRIMARY KEY,
            analysis_run_id TEXT NOT NULL,
            scene_id TEXT NOT NULL,
            obs_type TEXT NOT NULL,
            evidence_class TEXT NOT NULL,
            geometry TEXT NOT NULL,
            area_km2 REAL NOT NULL,
            confidence REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'candidate',
            attrs TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    # Bootstrap should add the missing columns without raising.
    Store(db_path)
    conn2 = sqlite3.connect(db_path)
    pragma = conn2.execute("PRAGMA table_info(observations)").fetchall()
    conn2.close()
    actual = {row[1] for row in pragma}
    assert "status_updated_at" in actual
    assert "features" in actual
