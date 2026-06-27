"""CDSE OAuth2 token acquisition and caching.

Token values are never logged or included in error messages.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import requests

from argus.core.errors import CdseAuthError  # noqa: E402 — re-export for backward compat

CDSE_TOKEN_URL = (
    "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
)
_EXPIRY_BUFFER_SECS = 60

__all__ = ["CdseAuth", "CdseAuthError"]


@dataclass
class _TokenCache:
    access_token: str
    expires_at: float  # unix timestamp


class CdseAuth:
    """Handles CDSE OAuth2 password-grant token acquisition and in-memory caching."""

    def __init__(
        self,
        user: str,
        password: str,
        *,
        token_url: str = CDSE_TOKEN_URL,
    ) -> None:
        self._user = user
        self._password = password
        self._token_url = token_url
        self._cache: _TokenCache | None = None

    def get_access_token(self) -> str:
        """Return a valid access token, fetching a new one only when needed."""
        if (
            self._cache is not None
            and time.monotonic() < self._cache.expires_at - _EXPIRY_BUFFER_SECS
        ):
            return self._cache.access_token
        return self._fetch()

    def _fetch(self) -> str:
        try:
            resp = requests.post(
                self._token_url,
                data={
                    "grant_type": "password",
                    "username": self._user,
                    "password": self._password,
                    "client_id": "cdse-public",
                },
                timeout=30,
            )
        except requests.RequestException as exc:
            raise CdseAuthError(
                f"CDSE token request failed: {type(exc).__name__}. "
                "Check network connectivity and try again."
            ) from exc

        if resp.status_code != 200:
            raise CdseAuthError(
                f"CDSE authentication failed (HTTP {resp.status_code}). "
                "Verify that ARGUS_CDSE_USER and ARGUS_CDSE_PASSWORD are correct. "
                "Manage credentials at https://dataspace.copernicus.eu/"
            )

        body = resp.json()
        token: str = body["access_token"]
        expires_in = int(body.get("expires_in", 600))
        self._cache = _TokenCache(
            access_token=token,
            expires_at=time.monotonic() + expires_in,
        )
        return token
