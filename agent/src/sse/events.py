"""Server-Sent Events helpers for streaming artifact status and LLM responses."""

from __future__ import annotations

import json

import structlog

logger = structlog.get_logger(__name__)


def format_sse(event: str, data: dict) -> str:
    """Format a single SSE message."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def format_sse_artifact_status(
    artifact_type: str, status: str, **kwargs,
) -> str:
    """Format an artifact status SSE event."""
    data = {"artifact_type": artifact_type, "status": status, **kwargs}
    return format_sse("artifact_status", data)


def format_sse_token(text: str) -> str:
    """Format a streaming token SSE event."""
    return format_sse("token", {"text": text})


def format_sse_done(full_text: str) -> str:
    """Format a stream completion SSE event."""
    return format_sse("done", {"full_text": full_text})
