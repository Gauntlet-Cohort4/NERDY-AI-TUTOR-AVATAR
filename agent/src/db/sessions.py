"""CRUD operations for sessions and transcript_turns tables.

All functions take an asyncpg.Pool as the first argument and return
plain dicts for serialisation safety.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

import asyncpg
import structlog

logger = structlog.get_logger(__name__)


async def create_session(
    pool: asyncpg.Pool,
    user_id: UUID,
    subject: str,
    grade: int,
    room_name: str,
) -> UUID:
    """Insert a new tutoring session and return its id."""
    row = await pool.fetchrow(
        """
        INSERT INTO sessions (user_id, subject, grade, room_name)
        VALUES ($1, $2, $3, $4)
        RETURNING id
        """,
        user_id,
        subject,
        grade,
        room_name,
    )
    session_id: UUID = row["id"]
    logger.info("session_created", session_id=str(session_id), subject=subject)
    return session_id


async def end_session(
    pool: asyncpg.Pool,
    session_id: UUID,
    summary_cache: str | None = None,
) -> None:
    """Mark a session as completed, computing duration from started_at."""
    await pool.execute(
        """
        UPDATE sessions
        SET ended_at      = now(),
            duration_secs = EXTRACT(EPOCH FROM (now() - started_at))::INT,
            summary_cache = $2,
            status        = 'completed'
        WHERE id = $1
        """,
        session_id,
        summary_cache,
    )
    logger.info("session_ended", session_id=str(session_id))


async def get_session(pool: asyncpg.Pool, session_id: UUID) -> dict[str, Any] | None:
    """Fetch a single session by id."""
    row = await pool.fetchrow("SELECT * FROM sessions WHERE id = $1", session_id)
    return dict(row) if row else None


async def list_sessions(
    pool: asyncpg.Pool,
    user_id: UUID,
    subject: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """List sessions for a user, optionally filtered by subject."""
    if subject is not None:
        rows = await pool.fetch(
            """
            SELECT * FROM sessions
            WHERE user_id = $1 AND subject = $2
            ORDER BY started_at DESC
            LIMIT $3
            """,
            user_id,
            subject,
            limit,
        )
    else:
        rows = await pool.fetch(
            """
            SELECT * FROM sessions
            WHERE user_id = $1
            ORDER BY started_at DESC
            LIMIT $2
            """,
            user_id,
            limit,
        )
    return [dict(r) for r in rows]


# ── Transcript Turns ─────────────────────────────────────────────────────────


async def add_turn(
    pool: asyncpg.Pool,
    session_id: UUID,
    turn_number: int,
    role: str,
    content: str,
    metrics: dict[str, Any] | None = None,
) -> UUID:
    """Append a transcript turn to the session."""
    metrics_json = json.dumps(metrics) if metrics is not None else None
    row = await pool.fetchrow(
        """
        INSERT INTO transcript_turns (session_id, turn_number, role, content, metrics)
        VALUES ($1, $2, $3, $4, $5::jsonb)
        RETURNING id
        """,
        session_id,
        turn_number,
        role,
        content,
        metrics_json,
    )
    return row["id"]


async def get_turns(
    pool: asyncpg.Pool,
    session_id: UUID,
    limit: int | None = None,
    order: str = "asc",
) -> list[dict[str, Any]]:
    """Fetch transcript turns for a session.

    Args:
        pool: Connection pool.
        session_id: Target session.
        limit: Max rows to return (None = all).
        order: 'asc' or 'desc' by turn_number.
    """
    # Allowlist for ORDER BY direction — never interpolate raw input into SQL
    _valid_order = {"asc": "ASC", "desc": "DESC"}
    direction = _valid_order.get(order.lower(), "ASC")

    if limit is not None:
        if direction == "DESC":
            rows = await pool.fetch(
                "SELECT * FROM transcript_turns WHERE session_id = $1 ORDER BY turn_number DESC LIMIT $2",
                session_id, limit,
            )
        else:
            rows = await pool.fetch(
                "SELECT * FROM transcript_turns WHERE session_id = $1 ORDER BY turn_number ASC LIMIT $2",
                session_id, limit,
            )
    else:
        if direction == "DESC":
            rows = await pool.fetch(
                "SELECT * FROM transcript_turns WHERE session_id = $1 ORDER BY turn_number DESC",
                session_id,
            )
        else:
            rows = await pool.fetch(
                "SELECT * FROM transcript_turns WHERE session_id = $1 ORDER BY turn_number ASC",
                session_id,
            )

    return [dict(r) for r in rows]


async def get_recent_turns(
    pool: asyncpg.Pool,
    session_id: UUID,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Fetch the most recent turns (DESC order by turn_number)."""
    rows = await pool.fetch(
        """
        SELECT * FROM transcript_turns
        WHERE session_id = $1
        ORDER BY turn_number DESC
        LIMIT $2
        """,
        session_id,
        limit,
    )
    return [dict(r) for r in rows]
