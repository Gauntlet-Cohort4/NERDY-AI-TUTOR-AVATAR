"""Shared LLM utilities: JSON extraction, Groq and Anthropic client singletons.

Centralises helpers that were previously duplicated across
processor.py, chat.py, and generator.py.
"""

from __future__ import annotations

import json
import re
from typing import Any

from groq import AsyncGroq

# Module-level singletons — reused across calls to avoid repeated instantiation.
_groq_client: AsyncGroq | None = None
_UNSET = object()
_anthropic_client: object = _UNSET


def extract_json(text: str) -> dict[str, Any]:
    """Strip markdown fences and parse JSON safely."""
    stripped = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    stripped = re.sub(r"```\s*$", "", stripped.strip(), flags=re.MULTILINE)
    return json.loads(stripped)


def get_groq_client() -> AsyncGroq:
    """Return a shared AsyncGroq client (reads GROQ_API_KEY from env).

    Uses a module-level singleton so that connection pooling is reused.
    """
    global _groq_client
    if _groq_client is None:
        _groq_client = AsyncGroq()
    return _groq_client


def get_anthropic_client():
    """Return a shared AsyncAnthropic client (reads ANTHROPIC_API_KEY from env).

    Returns None if the anthropic package is not installed or no key is set.
    Uses _UNSET sentinel to distinguish "not yet initialized" from "unavailable".
    """
    global _anthropic_client
    if _anthropic_client is _UNSET:
        try:
            import os

            from anthropic import AsyncAnthropic

            if not os.getenv("ANTHROPIC_API_KEY"):
                _anthropic_client = None
                return None
            _anthropic_client = AsyncAnthropic()
        except ImportError:
            _anthropic_client = None
    return _anthropic_client
