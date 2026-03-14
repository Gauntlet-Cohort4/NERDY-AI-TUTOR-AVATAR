"""CRUD operations for the uploads table.

Handles student-uploaded files (images, PDFs) that may be classified
into subjects and grades for context-aware tutoring.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import asyncpg
import structlog

logger = structlog.get_logger(__name__)


async def create_upload(
    pool: asyncpg.Pool,
    user_id: UUID,
    file_name: str,
    file_type: str,
    file_data: bytes,
    session_id: UUID | None = None,
) -> UUID:
    """Store an uploaded file and return its id."""
    row = await pool.fetchrow(
        """
        INSERT INTO uploads (user_id, session_id, file_name, file_type, file_data)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id
        """,
        user_id,
        session_id,
        file_name,
        file_type,
        file_data,
    )
    upload_id: UUID = row["id"]
    logger.info("upload_created", upload_id=str(upload_id), file_name=file_name)
    return upload_id


async def update_classification(
    pool: asyncpg.Pool,
    upload_id: UUID,
    extracted_text: str,
    detected_subject: str,
    detected_grade: int,
    status: str = "classified",
) -> None:
    """Update an upload with classification results."""
    await pool.execute(
        """
        UPDATE uploads
        SET extracted_text   = $2,
            detected_subject = $3,
            detected_grade   = $4,
            status           = $5
        WHERE id = $1
        """,
        upload_id,
        extracted_text,
        detected_subject,
        detected_grade,
        status,
    )
    logger.info(
        "upload_classified",
        upload_id=str(upload_id),
        detected_subject=detected_subject,
    )


async def get_upload(
    pool: asyncpg.Pool,
    upload_id: UUID,
) -> dict[str, Any] | None:
    """Fetch a single upload by id."""
    row = await pool.fetchrow("SELECT * FROM uploads WHERE id = $1", upload_id)
    return dict(row) if row else None


async def list_uploads(
    pool: asyncpg.Pool,
    user_id: UUID,
) -> list[dict[str, Any]]:
    """List all uploads for a user, most recent first."""
    rows = await pool.fetch(
        """
        SELECT * FROM uploads
        WHERE user_id = $1
        ORDER BY created_at DESC
        """,
        user_id,
    )
    return [dict(r) for r in rows]
