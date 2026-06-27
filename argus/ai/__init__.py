"""Argus AI layer — grounded, cited, LLM-powered environmental intelligence."""

from argus.ai.base import AIReport, Assistant, GroundedAnswer, GroundedText, Scope
from argus.ai.client import ArgusAIClient
from argus.ai.fallback import generate_template_report, is_offline
from argus.ai.grounding import GroundingGuard

__all__ = [
    "AIReport",
    "ArgusAIClient",
    "Assistant",
    "GroundedAnswer",
    "GroundedText",
    "GroundingGuard",
    "Scope",
    "generate_template_report",
    "is_offline",
]
