"""Scene acquisition: quota enforcement, idempotency check, Process API fetch, persistence."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from argus.core.config import Settings
from argus.core.errors import AcquisitionError, QuotaExceededError
from argus.core.models import AOI, Scene, SourceRef
from argus.core.store import Store
from argus.ingest.cdse_auth import CdseAuth
from argus.ingest.process_api import fetch_s1_subset

_BYTES_PER_GB = 1_073_741_824

__all__ = ["AcquisitionError", "QuotaExceededError", "acquire_scene"]


def acquire_scene(
    ref: SourceRef,
    aoi: AOI,
    auth: CdseAuth,
    store: Store,
    settings: Settings,
) -> Scene:
    """Download a σ⁰ GeoTIFF for *ref*, enforce the daily CDSE quota, persist the Scene.

    Idempotency (F-038): if a Scene with the same product_id already exists with
    ingest_status="ready", the existing Scene is returned without re-downloading.
    This ensures repeated runs over the same date window never double-fetch.

    Raises QuotaExceededError if the daily quota is already exhausted before downloading,
    or AcquisitionError if the downloaded byte count would push usage over the limit.
    """
    # ── Idempotency check ─────────────────────────────────────────────────────
    existing = store.get_scene_by_product_id(ref.product_id)
    if existing is not None and existing.ingest_status == "ready":
        return existing

    # ── Quota guard ───────────────────────────────────────────────────────────
    daily_limit = int(settings.cdse.daily_quota_gb * _BYTES_PER_GB)
    today = datetime.now(UTC)
    used = store.daily_bytes_total(today)

    if used >= daily_limit:
        raise QuotaExceededError(
            f"CDSE daily quota exhausted: {used / _BYTES_PER_GB:.3f} GB used of "
            f"{settings.cdse.daily_quota_gb:.1f} GB. Try again tomorrow."
        )

    artifact_dir = Path(settings.store.artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    tiff_bytes, byte_count = fetch_s1_subset(ref, aoi, auth)

    if used + byte_count > daily_limit:
        raise AcquisitionError(
            f"Download of {byte_count / 1e6:.1f} MB would exceed the CDSE daily quota "
            f"({settings.cdse.daily_quota_gb:.1f} GB). Acquisition aborted."
        )

    scene_id = str(uuid.uuid4())
    artifact_path = artifact_dir / f"{scene_id}.tif"
    artifact_path.write_bytes(tiff_bytes)

    scene = Scene(
        id=scene_id,
        product_id=ref.product_id,
        aoi_id=aoi.id,
        sensing_time=ref.sensing_time,
        ingest_status="ready",
        artifact_path=str(artifact_path),
        bytes_or_calls=byte_count,
    )
    store.save_scene(scene)
    return scene
