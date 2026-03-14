"""CRUD operations for the artifacts table.

Artifacts are lesson-generated outputs (study guides, quizzes, diagrams)
linked to a tutoring session.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

import asyncpg
import structlog

logger = structlog.get_logger(__name__)


async def create_artifact(
    pool: asyncpg.Pool,
    session_id: UUID,
    artifact_type: str,
    title: str,
) -> UUID:
    """Create a pending artifact record and return its id."""
    row = await pool.fetchrow(
        """
        INSERT INTO artifacts (session_id, artifact_type, title)
        VALUES ($1, $2, $3)
        RETURNING id
        """,
        session_id,
        artifact_type,
        title,
    )
    artifact_id: UUID = row["id"]
    logger.info(
        "artifact_created",
        artifact_id=str(artifact_id),
        artifact_type=artifact_type,
    )
    return artifact_id


async def update_content(
    pool: asyncpg.Pool,
    artifact_id: UUID,
    content_json: dict[str, Any],
    status: str = "ready",
) -> None:
    """Set the JSON content payload and transition status."""
    await pool.execute(
        """
        UPDATE artifacts
        SET content_json = $2::jsonb,
            status       = $3,
            updated_at   = now()
        WHERE id = $1
        """,
        artifact_id,
        json.dumps(content_json),
        status,
    )
    logger.info("artifact_content_updated", artifact_id=str(artifact_id), status=status)


async def update_pdf(
    pool: asyncpg.Pool,
    artifact_id: UUID,
    pdf_bytes: bytes,
) -> None:
    """Attach a rendered PDF to an existing artifact."""
    await pool.execute(
        """
        UPDATE artifacts
        SET content_pdf = $2,
            updated_at  = now()
        WHERE id = $1
        """,
        artifact_id,
        pdf_bytes,
    )
    logger.info("artifact_pdf_updated", artifact_id=str(artifact_id))


async def get_artifact(
    pool: asyncpg.Pool,
    artifact_id: UUID,
) -> dict[str, Any] | None:
    """Fetch a single artifact by id."""
    row = await pool.fetchrow("SELECT * FROM artifacts WHERE id = $1", artifact_id)
    return dict(row) if row else None


async def list_artifacts(
    pool: asyncpg.Pool,
    session_id: UUID,
) -> list[dict[str, Any]]:
    """List all artifacts belonging to a session."""
    rows = await pool.fetch(
        """
        SELECT * FROM artifacts
        WHERE session_id = $1
        ORDER BY created_at ASC
        """,
        session_id,
    )
    return [dict(r) for r in rows]


async def get_artifacts_by_status(
    pool: asyncpg.Pool,
    status: str,
) -> list[dict[str, Any]]:
    """List artifacts with a given status across all sessions."""
    rows = await pool.fetch(
        """
        SELECT * FROM artifacts
        WHERE status = $1
        ORDER BY created_at ASC
        """,
        status,
    )
    return [dict(r) for r in rows]
