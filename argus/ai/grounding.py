"""Grounding guard — enforces INV-4: every factual AI claim cites a store record.

The guard performs two checks:
1. Citation existence: every id in `citations` resolves to an Observation or Prediction.
2. Coverage: every factual sentence (one containing a number, measurement, risk label,
   or date) must contain at least one inline citation [record_id].

A grounded response passes both checks and returns a GroundedText. Any failure
raises GroundingError, which is a defect, not a warning.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from argus.ai.base import GroundedText
from argus.ai.client import _PINNED_MODEL
from argus.core.errors import GroundingError

if TYPE_CHECKING:
    from argus.core.store import Store

# Matches an inline citation token: [some_record_id]
_CITATION_RE = re.compile(r"\[[^\[\]]+\]")

# A sentence is "factual" if it contains a digit sequence OR a risk/measurement keyword.
# Conservative on purpose: false positives are better than missed ungrounded claims.
_FACTUAL_RE = re.compile(
    r"\d"  # any digit (numeric values, dates, coordinates)
    r"|bloom\b"
    r"|anomal\w*"
    r"|elevated\b"
    r"|severe\w*"
    r"|detected\b"
    r"|slick\b"
    r"|inundation\b"
    r"|concentration\b"
    r"|risk\b"
    r"|µg"
    r"|mg/l"
    r"|mg/L"
    r"|ppm\b"
    r"|ppb\b",
    re.IGNORECASE,
)


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences on . ! ? followed by whitespace or end-of-string."""
    parts = re.split(r"(?<=[.!?])(?:\s+|$)", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _is_factual(sentence: str) -> bool:
    return bool(_FACTUAL_RE.search(sentence))


def _has_citation(sentence: str) -> bool:
    return bool(_CITATION_RE.search(sentence))


def _record_exists(record_id: str, store: Store) -> bool:
    if store.get_observation(record_id) is not None:
        return True
    return store.get_prediction(record_id) is not None


class GroundingGuard:
    """Validates that an AI response is fully grounded against the store.

    Usage:
        guard = GroundingGuard()
        grounded = guard.validate(response_text, citation_ids, store)
    """

    def validate(self, response: str, citations: list[str], store: Store) -> GroundedText:
        """Validate response and citations; raise GroundingError on any violation.

        Raises:
            GroundingError: if any citation id is not in the store, or if any
                factual sentence lacks a citation.
        """
        for cid in citations:
            if not _record_exists(cid, store):
                raise GroundingError(
                    f"Citation {cid!r} not found in store (no matching Observation or "
                    "Prediction). Remove the citation or save the record first."
                )

        for sentence in _split_sentences(response):
            if _is_factual(sentence) and not _has_citation(sentence):
                raise GroundingError(
                    f"Factual sentence lacks a citation [record_id]: {sentence!r}. "
                    "Every sentence containing a number, measurement, or risk label "
                    "must end with a [record_id] reference."
                )

        return GroundedText(text=response, citations=citations, model=_PINNED_MODEL)
