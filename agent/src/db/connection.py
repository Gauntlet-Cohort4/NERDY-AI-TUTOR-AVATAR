"""Async PostgreSQL connection pool manager.

Provides a single Database instance per process with health-check support.
"""

from __future__ import annotations

import asyncpg
import structlog

logger = structlog.get_logger(__name__)


class Database:
    """Async PostgreSQL connection pool. One instance per process."""

    def __init__(self) -> None:
        self._pool: asyncpg.Pool | None = None

    async def connect(self, dsn: str) -> None:
        """Create the connection pool.

        Args:
            dsn: PostgreSQL connection string (DATABASE_URL).
        """
        if self._pool is not None:
            logger.warning("database_already_connected")
            return

        host_info = dsn.rsplit("@", 1)[-1] if "@" in dsn else "***"
        try:
            self._pool = await asyncpg.create_pool(
                dsn,
                min_size=2,
                max_size=10,
            )
        except Exception:
            logger.exception("database_connect_failed", host=host_info)
            raise
        logger.info("database_connected", host=host_info)

    async def close(self) -> None:
        """Gracefully close the connection pool."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            logger.info("database_closed")

    @property
    def pool(self) -> asyncpg.Pool:
        """Return the connection pool, raising if not connected."""
        if self._pool is None:
            raise RuntimeError(
                "Database is not connected. Call await db.connect(dsn) first."
            )
        return self._pool

    async def health_check(self) -> bool:
        """Return True if the database is reachable."""
        if self._pool is None:
            return False
        try:
            async with self._pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception:
            logger.exception("database_health_check_failed")
            return False
