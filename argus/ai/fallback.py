"""Templated report generator — used when ARGUS_AI_OFFLINE=true or over API budget.

Produces a plain-language GroundedText without any LLM call. Citations are the
ids of the observations passed in; every factual sentence references them.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from argus.ai.base import GroundedText
from argus.ai.client import _PINNED_MODEL

if TYPE_CHECKING:
    from argus.ai.base import Scope
    from argus.core.models import Observation


def is_offline() -> bool:
    """Return True when ARGUS_AI_OFFLINE=true (or 1, yes) is set."""
    return os.environ.get("ARGUS_AI_OFFLINE", "").strip().lower() in ("1", "true", "yes")


def generate_template_report(scope: Scope, obs: list[Observation]) -> GroundedText:
    """Build a plain-language templated report from store observations (no LLM).

    Each factual sentence is backed by the observation id, satisfying INV-4
    without an API call.
    """
    citations: list[str] = [o.id for o in obs]
    lines: list[str] = [f"Situation report for area {scope.aoi_id!r} for the requested period."]

    if not obs:
        lines.append("No observations found in the requested time window.")
    else:
        type_groups: dict[str, list[Observation]] = {}
        for o in obs:
            type_groups.setdefault(o.obs_type, []).append(o)

        for obs_type, group in sorted(type_groups.items()):
            values = [o.value for o in group if o.value is not None]
            ids_tag = " ".join(f"[{o.id}]" for o in group)
            if values:
                mean_val = sum(values) / len(values)
                lines.append(
                    f"{obs_type.replace('_', ' ').title()}: mean value "
                    f"{mean_val:.4f} across {len(group)} observations {ids_tag}."
                )
            else:
                lines.append(
                    f"{obs_type.replace('_', ' ').title()}: "
                    f"{len(group)} observation(s) recorded {ids_tag}."
                )

    text = " ".join(lines)
    return GroundedText(text=text, citations=citations, model=f"{_PINNED_MODEL}:template")
