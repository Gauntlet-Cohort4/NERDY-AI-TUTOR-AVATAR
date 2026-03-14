"""CRUD operations for the flash_cards table.

Flash cards are automatically generated from tutoring sessions and
deduplicated on (user_id, subject, LOWER(term)).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import asyncpg
import structlog

logger = structlog.get_logger(__name__)


async def upsert_flash_card(
    pool: asyncpg.Pool,
    user_id: UUID,
    subject: str,
    term: str,
    definition: str,
    example: str | None,
    grade: int,
    session_id: UUID | None,
) -> bool:
    """Insert a flash card, skipping duplicates.

    Returns True if a new row was inserted, False if a duplicate was skipped.
    """
    result = await pool.execute(
        """
        INSERT INTO flash_cards
            (user_id, subject, term, definition, example, grade, source_session_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (user_id, subject, LOWER(term)) DO NOTHING
        """,
        user_id,
        subject,
        term,
        definition,
        example,
        grade,
        session_id,
    )
    inserted = result == "INSERT 0 1"
    if inserted:
        logger.info("flash_card_created", subject=subject, term=term)
    else:
        logger.debug("flash_card_duplicate_skipped", subject=subject, term=term)
    return inserted


async def list_flash_cards(
    pool: asyncpg.Pool,
    user_id: UUID,
    subject: str | None = None,
    mastery: str | None = None,
) -> list[dict[str, Any]]:
    """List flash cards with optional subject and mastery filters."""
    if subject is not None and mastery is not None:
        rows = await pool.fetch(
            "SELECT * FROM flash_cards WHERE user_id=$1 AND subject=$2 AND mastery=$3 ORDER BY created_at DESC",
            user_id, subject, mastery,
        )
    elif subject is not None:
        rows = await pool.fetch(
            "SELECT * FROM flash_cards WHERE user_id=$1 AND subject=$2 ORDER BY created_at DESC",
            user_id, subject,
        )
    elif mastery is not None:
        rows = await pool.fetch(
            "SELECT * FROM flash_cards WHERE user_id=$1 AND mastery=$2 ORDER BY created_at DESC",
            user_id, mastery,
        )
    else:
        rows = await pool.fetch(
            "SELECT * FROM flash_cards WHERE user_id=$1 ORDER BY created_at DESC",
            user_id,
        )
    return [dict(r) for r in rows]


async def update_mastery(
    pool: asyncpg.Pool,
    card_id: UUID,
    mastery: str,
) -> None:
    """Update mastery level and set last_reviewed_at to now."""
    await pool.execute(
        """
        UPDATE flash_cards
        SET mastery          = $2,
            last_reviewed_at = now()
        WHERE id = $1
        """,
        card_id,
        mastery,
    )
    logger.info("flash_card_mastery_updated", card_id=str(card_id), mastery=mastery)


async def count_by_subject(
    pool: asyncpg.Pool,
    user_id: UUID,
) -> dict[str, dict[str, int]]:
    """Return card counts grouped by subject and mastery level.

    Returns: {subject: {total, new, learning, known}}
    """
    rows = await pool.fetch(
        """
        SELECT subject, mastery, COUNT(*)::INT AS cnt
        FROM flash_cards
        WHERE user_id = $1
        GROUP BY subject, mastery
        ORDER BY subject
        """,
        user_id,
    )

    result: dict[str, dict[str, int]] = {}
    for row in rows:
        subj = row["subject"]
        if subj not in result:
            result[subj] = {"total": 0, "new": 0, "learning": 0, "known": 0}
        result[subj][row["mastery"]] = row["cnt"]
        result[subj]["total"] += row["cnt"]

    return result
