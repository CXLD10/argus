"""Seasonal baseline construction from water quality Observation history."""

from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass, field

from argus.core.models import Observation


@dataclass
class SeasonalBaseline:
    """Per-ISO-week descriptive statistics derived from historical Observations.

    weekly_stats: iso_week (1–53) → (mean, std) of the obs_type index value.
    Weeks with fewer than 2 data points have std=0 (treated as insufficient).
    """

    obs_type: str
    weekly_stats: dict[int, tuple[float, float]] = field(default_factory=dict)

    def mean_std(self, iso_week: int) -> tuple[float | None, float | None]:
        """Return (mean, std) for the given ISO week, or (None, None) if unknown."""
        entry = self.weekly_stats.get(iso_week)
        if entry is None:
            return None, None
        return entry


def build_baseline(
    obs: list[Observation],
    obs_type: str = "chlorophyll_a",
) -> SeasonalBaseline:
    """Compute per-ISO-week mean and std from a list of historical Observations.

    Uses Observation.created_at to assign each observation to an ISO week.
    Weeks with only one data point have std=0.0 (z-score cannot be computed).
    """
    weekly_values: dict[int, list[float]] = defaultdict(list)

    for o in obs:
        if o.obs_type == obs_type and o.value is not None:
            week = o.created_at.isocalendar().week
            weekly_values[week].append(o.value)

    weekly_stats: dict[int, tuple[float, float]] = {}
    for week, values in weekly_values.items():
        mean = statistics.mean(values)
        std = statistics.stdev(values) if len(values) >= 2 else 0.0
        weekly_stats[week] = (mean, std)

    return SeasonalBaseline(obs_type=obs_type, weekly_stats=weekly_stats)
