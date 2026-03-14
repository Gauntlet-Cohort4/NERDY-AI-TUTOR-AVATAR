"""CRUD operations for the visual_assets table.

Visual assets cache pre-built or generated diagrams, charts, and
illustrations keyed by subject and topic.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

import asyncpg
import structlog

logger = structlog.get_logger(__name__)


async def get_visual(
    pool: asyncpg.Pool,
    subject: str,
    topic_key: str,
) -> dict[str, Any] | None:
    """Look up a cached visual asset by subject and topic key."""
    row = await pool.fetchrow(
        """
        SELECT * FROM visual_assets
        WHERE subject = $1 AND topic_key = $2
        """,
        subject,
        topic_key,
    )
    return dict(row) if row else None


async def list_visuals(
    pool: asyncpg.Pool,
    subject: str,
) -> list[dict[str, Any]]:
    """List all visual assets for a given subject."""
    rows = await pool.fetch(
        """
        SELECT * FROM visual_assets
        WHERE subject = $1
        ORDER BY created_at DESC
        """,
        subject,
    )
    return [dict(r) for r in rows]


async def create_visual(
    pool: asyncpg.Pool,
    subject: str,
    topic_key: str,
    asset_type: str,
    title: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> UUID:
    """Insert a new visual asset and return its id."""
    metadata_json = json.dumps(metadata) if metadata is not None else None
    row = await pool.fetchrow(
        """
        INSERT INTO visual_assets (subject, topic_key, asset_type, title, content, metadata)
        VALUES ($1, $2, $3, $4, $5, $6::jsonb)
        RETURNING id
        """,
        subject,
        topic_key,
        asset_type,
        title,
        content,
        metadata_json,
    )
    visual_id: UUID = row["id"]
    logger.info(
        "visual_asset_created",
        visual_id=str(visual_id),
        subject=subject,
        topic_key=topic_key,
    )
    return visual_id
