"""Pre-flight quota checks for scheduled domain tasks.

Guards are stateless functions — they read the store and settings, make a binary
allow/deny decision, and return a reason string when denying. No side effects.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from argus.core.store import Store

logger = logging.getLogger(__name__)

_SATELLITE_DOMAINS = frozenset({"marine_oil", "inland_wq", "hydro_chokepoints"})
_WEATHER_DOMAINS = frozenset({"weather_hydro"})

# Open-Meteo calls today is approximated from scenes where source is open-meteo.
# Scenes for weather domains use bytes_or_calls to record API call count (not bytes).


@dataclass(frozen=True)
class QuotaDecision:
    allowed: bool
    reason: str


def check_cdse_daily_quota(store: Store, daily_quota_gb: float = 1.0) -> QuotaDecision:
    """Return allowed=True if CDSE bytes used today are under the daily quota."""
    used_bytes = store.daily_bytes_total(datetime.now(UTC))
    quota_bytes = int(daily_quota_gb * 1024**3)
    if used_bytes >= quota_bytes:
        return QuotaDecision(
            allowed=False,
            reason=(
                f"CDSE daily quota exhausted: {used_bytes / 1024**2:.1f} MB / "
                f"{daily_quota_gb * 1024:.0f} MB used"
            ),
        )
    return QuotaDecision(allowed=True, reason="ok")


def check_open_meteo_daily_quota(store: Store, daily_call_limit: int = 10_000) -> QuotaDecision:
    """Return allowed=True if estimated Open-Meteo calls today are under the daily limit.

    Uses the same daily_bytes_total helper — for weather domains bytes_or_calls
    records API call count rather than byte count.
    """
    calls_today = store.daily_bytes_total(datetime.now(UTC))
    if calls_today >= daily_call_limit:
        return QuotaDecision(
            allowed=False,
            reason=f"Open-Meteo daily limit reached: {calls_today} / {daily_call_limit} calls",
        )
    return QuotaDecision(allowed=True, reason="ok")


def check_domain_quota(
    domain_id: str,
    store: Store,
    daily_quota_gb: float = 1.0,
    daily_call_limit: int = 10_000,
) -> QuotaDecision:
    """Route to the right quota guard for the given domain."""
    if domain_id in _SATELLITE_DOMAINS:
        return check_cdse_daily_quota(store, daily_quota_gb)
    if domain_id in _WEATHER_DOMAINS:
        return check_open_meteo_daily_quota(store, daily_call_limit)
    return QuotaDecision(allowed=True, reason="no quota guard for domain")
