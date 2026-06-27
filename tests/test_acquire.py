"""F-003 tests: scene acquisition (mocked Process API + mocked auth)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import responses

from argus.aoi.loader import load_aoi
from argus.core.config import CdseConfig, Settings, StoreConfig
from argus.core.models import SourceRef
from argus.core.store import Store
from argus.ingest.acquire import AcquisitionError, acquire_scene
from argus.ingest.cdse_auth import CdseAuth
from argus.ingest.process_api import CDSE_PROCESS_API_URL

_TOBAGO = Path(__file__).parent.parent / "config" / "aois" / "tobago.geojson"
_FAKE_TIFF = b"FAKE_TIFF_BYTES_FOR_TESTING"
_FAKE_TOKEN = "fake-access-token"


def _make_ref() -> SourceRef:
    return SourceRef(
        product_id="S1A_IW_GRDH_1SDV_20240207T215408_20240207T215433_052578_065C2A_4F91.SAFE",
        source="cdse",
        collection="SENTINEL-1",
        product_type="GRD",
        sensor_mode="IW",
        sensing_time=datetime(2024, 2, 7, 21, 54, 8, tzinfo=UTC),
        footprint={
            "type": "Polygon",
            "coordinates": [[[-62, 10], [-59, 10], [-59, 12], [-62, 12], [-62, 10]]],
        },
        polarizations=["VV", "VH"],
    )


def _make_settings(tmp_path: Path, quota_gb: float = 1.0) -> Settings:
    return Settings(
        cdse=CdseConfig(user="u", password="p", daily_quota_gb=quota_gb),
        store=StoreConfig(artifact_dir=tmp_path / "artifacts"),  # type: ignore[arg-type]
    )


def _make_auth_with_cached_token() -> CdseAuth:
    """Return a CdseAuth instance with a pre-cached token (no HTTP call needed)."""
    import time

    from argus.ingest.cdse_auth import _TokenCache

    auth = CdseAuth("u", "p")
    auth._cache = _TokenCache(access_token=_FAKE_TOKEN, expires_at=time.monotonic() + 3600)
    return auth


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "argus.db")


@responses.activate
def test_acquire_scene_success(tmp_path: Path, store: Store) -> None:
    responses.add(
        responses.POST,
        CDSE_PROCESS_API_URL,
        body=_FAKE_TIFF,
        status=200,
        headers={"Content-Length": str(len(_FAKE_TIFF)), "Content-Type": "image/tiff"},
    )
    aoi = load_aoi(_TOBAGO)
    ref = _make_ref()
    auth = _make_auth_with_cached_token()
    settings = _make_settings(tmp_path)

    scene = acquire_scene(ref, aoi, auth, store, settings)

    assert scene.ingest_status == "ready"
    assert scene.bytes_or_calls > 0
    assert scene.artifact_path is not None
    assert Path(scene.artifact_path).exists()


@responses.activate
def test_acquire_scene_persisted(tmp_path: Path, store: Store) -> None:
    responses.add(
        responses.POST,
        CDSE_PROCESS_API_URL,
        body=_FAKE_TIFF,
        status=200,
        headers={"Content-Length": str(len(_FAKE_TIFF))},
    )
    aoi = load_aoi(_TOBAGO)
    ref = _make_ref()
    auth = _make_auth_with_cached_token()
    settings = _make_settings(tmp_path)

    scene = acquire_scene(ref, aoi, auth, store, settings)
    retrieved = store.get_scene(scene.id)

    assert retrieved is not None
    assert retrieved.id == scene.id
    assert retrieved.ingest_status == "ready"
    assert retrieved.bytes_or_calls == scene.bytes_or_calls


@responses.activate
def test_acquire_scene_artifact_contains_tiff_bytes(tmp_path: Path, store: Store) -> None:
    responses.add(
        responses.POST,
        CDSE_PROCESS_API_URL,
        body=_FAKE_TIFF,
        status=200,
        headers={"Content-Length": str(len(_FAKE_TIFF))},
    )
    aoi = load_aoi(_TOBAGO)
    auth = _make_auth_with_cached_token()
    settings = _make_settings(tmp_path)

    scene = acquire_scene(_make_ref(), aoi, auth, store, settings)
    assert Path(scene.artifact_path).read_bytes() == _FAKE_TIFF  # type: ignore[arg-type]


@responses.activate
def test_acquire_refuses_when_quota_exhausted(tmp_path: Path, store: Store) -> None:
    # Pre-fill the store so the daily quota is already at the limit
    from argus.core.models import Scene

    already_used = int(0.5 * 1_073_741_824)  # 0.5 GB
    store.save_scene(
        Scene(
            id="prior",
            product_id="prior",
            aoi_id="tobago",
            sensing_time=datetime(2024, 2, 7, tzinfo=UTC),
            ingest_status="ready",
            bytes_or_calls=already_used,
        )
    )

    aoi = load_aoi(_TOBAGO)
    auth = _make_auth_with_cached_token()
    # Set quota to 0.1 GB — already_used (0.5 GB) exceeds this immediately
    settings = _make_settings(tmp_path, quota_gb=0.1)

    with pytest.raises(AcquisitionError, match="exhausted"):
        acquire_scene(_make_ref(), aoi, auth, store, settings)


@responses.activate
def test_acquire_refuses_when_download_would_exceed_quota(tmp_path: Path, store: Store) -> None:
    # Response body is large enough to push total over a tiny quota
    large_body = b"X" * 200  # 200 bytes
    responses.add(
        responses.POST,
        CDSE_PROCESS_API_URL,
        body=large_body,
        status=200,
        headers={"Content-Length": str(len(large_body))},
    )

    aoi = load_aoi(_TOBAGO)
    auth = _make_auth_with_cached_token()
    # quota = 100 bytes; download = 200 bytes → should raise
    settings = Settings(
        cdse=CdseConfig(user="u", password="p", daily_quota_gb=100 / 1_073_741_824),
        store=StoreConfig(artifact_dir=tmp_path / "artifacts"),  # type: ignore[arg-type]
    )

    with pytest.raises(AcquisitionError, match="exceed"):
        acquire_scene(_make_ref(), aoi, auth, store, settings)


@responses.activate
def test_acquire_process_api_http_error_propagates(tmp_path: Path, store: Store) -> None:
    from argus.ingest.process_api import ProcessApiError

    responses.add(
        responses.POST,
        CDSE_PROCESS_API_URL,
        json={"error": "Bad Request"},
        status=400,
    )

    aoi = load_aoi(_TOBAGO)
    auth = _make_auth_with_cached_token()
    settings = _make_settings(tmp_path)

    with pytest.raises(ProcessApiError):
        acquire_scene(_make_ref(), aoi, auth, store, settings)
