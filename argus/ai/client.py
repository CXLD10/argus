"""Anthropic API client wrapper — pinned model, logged calls, budget tracking.

No live calls in the default test suite (INV-7 variant for AI). Tests that need
the client must use the mock_anthropic fixture or set ARGUS_AI_OFFLINE=true.
"""

from __future__ import annotations

from typing import Any

# Pinned model id — never "latest" or an unversioned alias (F-030 AC).
_PINNED_MODEL: str = "claude-sonnet-4-6"
_MAX_TOKENS: int = 1024


class ArgusAIClient:
    """Thin wrapper around the Anthropic messages API.

    Tracks call count and token usage for quota monitoring. The anthropic
    package is lazy-imported so that the test suite can run without it
    when ARGUS_AI_OFFLINE=true or mocking is used.
    """

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key
        self._total_calls: int = 0
        self._total_input_tokens: int = 0
        self._total_output_tokens: int = 0

    @property
    def model(self) -> str:
        return _PINNED_MODEL

    @property
    def usage(self) -> dict[str, int]:
        return {
            "calls": self._total_calls,
            "input_tokens": self._total_input_tokens,
            "output_tokens": self._total_output_tokens,
        }

    def complete(self, prompt: str, *, system: str = "") -> str:
        """Call the Anthropic messages API and return the text response.

        Raises ImportError if the anthropic package is not installed.
        Raises RuntimeError on API-level errors.
        """
        try:
            import anthropic  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "anthropic package is required for live AI calls. "
                "Install it with: pip install 'argus[ai]'"
            ) from exc

        client = anthropic.Anthropic(api_key=self._api_key)
        kwargs: dict[str, Any] = {
            "model": _PINNED_MODEL,
            "max_tokens": _MAX_TOKENS,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system

        response = client.messages.create(**kwargs)
        self._total_calls += 1
        usage = response.usage
        self._total_input_tokens += usage.input_tokens
        self._total_output_tokens += usage.output_tokens

        block = response.content[0]
        return str(block.text) if hasattr(block, "text") else str(block)
