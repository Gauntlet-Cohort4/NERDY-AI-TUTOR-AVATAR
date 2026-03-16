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
    """Strip markdown fences and parse JSON safely.

    Handles: bare JSON, ```json ... ```, ``` ... ```, and JSON embedded
    in surrounding prose.  Falls back to locating the first { or [ block.
    """
    # 1. Try to extract content between code fences
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    candidate = fence_match.group(1).strip() if fence_match else text.strip()

    # 2. Try parsing the candidate directly
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    # 3. Fall back: find the first { ... } or [ ... ] block
    brace = candidate.find("{")
    bracket = candidate.find("[")
    if brace == -1 and bracket == -1:
        raise ValueError("No JSON object found in text")
    start = min(p for p in (brace, bracket) if p >= 0)
    open_char = candidate[start]
    close_char = "}" if open_char == "{" else "]"
    depth = 0
    for i in range(start, len(candidate)):
        if candidate[i] == open_char:
            depth += 1
        elif candidate[i] == close_char:
            depth -= 1
            if depth == 0:
                return json.loads(candidate[start : i + 1])
    raise ValueError("Unbalanced braces/brackets in JSON")


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
