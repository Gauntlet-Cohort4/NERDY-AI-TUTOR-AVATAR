"""Shared LLM utilities: JSON extraction and Groq client singleton.

Centralises helpers that were previously duplicated across
processor.py, chat.py, and generator.py.
"""

from __future__ import annotations

import json
import re
from typing import Any

from groq import AsyncGroq

# Module-level singleton — reused across calls to avoid repeated instantiation.
_groq_client: AsyncGroq | None = None


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
