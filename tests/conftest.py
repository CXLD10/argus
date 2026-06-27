"""Shared pytest fixtures for the Argus test suite.

All fixtures here are available to every test file automatically.
Test files may also define their own local fixtures — these are additive.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
import responses as resp_lib

from argus.core.store import Store

# ── Store ─────────────────────────────────────────────────────────────────────


@pytest.fixture()
def tmp_store(tmp_path: Path) -> Store:
    """Fresh SQLite Store in a temporary directory. Isolated per test."""
    return Store(tmp_path / "argus_test.db")


# ── Open-Meteo mock ───────────────────────────────────────────────────────────

_OPEN_METEO_BASE = "https://api.open-meteo.com"

_OPEN_METEO_WIND_STUB: dict = {
    "latitude": 11.15,
    "longitude": -61.25,
    "hourly": {
        "time": ["2024-02-07T00:00", "2024-02-07T01:00"],
        "wind_speed_10m": [5.2, 5.8],
        "wind_direction_10m": [135, 140],
    },
}


@pytest.fixture()
def mock_open_meteo():
    """Intercept Open-Meteo HTTP calls with a minimal wind stub.

    Yields the responses mock so tests can introspect calls if needed.
    """
    with resp_lib.RequestsMock() as rsps:
        rsps.add(
            resp_lib.GET,
            _OPEN_METEO_BASE,
            json=_OPEN_METEO_WIND_STUB,
            status=200,
            match_querystring=False,
        )
        yield rsps


# ── CDSE auth mock ────────────────────────────────────────────────────────────

_CDSE_TOKEN_URL = (
    "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
)

_CDSE_TOKEN_STUB: dict = {
    "access_token": "mock-cdse-token-abc123",
    "expires_in": 3600,
    "token_type": "Bearer",
}


@pytest.fixture()
def mock_cdse_auth():
    """Intercept CDSE OAuth token endpoint so no live credentials are needed.

    Yields the responses mock so tests can introspect calls if needed.
    """
    with resp_lib.RequestsMock() as rsps:
        rsps.add(
            resp_lib.POST,
            _CDSE_TOKEN_URL,
            json=_CDSE_TOKEN_STUB,
            status=200,
        )
        yield rsps


# ── Anthropic mock ────────────────────────────────────────────────────────────


@pytest.fixture()
def mock_anthropic():
    """Return a MagicMock that mimics the anthropic.Anthropic client.

    Use this fixture in AI-layer tests to avoid live API calls (INV-7).
    Wire it up with:
        with patch("argus.ai.client.anthropic.Anthropic", return_value=mock_anthropic):
            ...
    """
    client = MagicMock()
    message = MagicMock()
    message.content = [MagicMock(text="Mock AI response.")]
    client.messages.create.return_value = message
    return client
