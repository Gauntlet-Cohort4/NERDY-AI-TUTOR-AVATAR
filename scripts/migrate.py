#!/usr/bin/env python3
"""Run SQL migrations against the database.

Reads DATABASE_URL from the environment (or .env file) and executes
each migration file in order.

Usage:
    python scripts/migrate.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import asyncpg
from dotenv import load_dotenv


async def run_migrations() -> None:
    load_dotenv()

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        print("ERROR: DATABASE_URL environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    sql_files = sorted(migrations_dir.glob("*.sql"))

    if not sql_files:
        print("No migration files found in", migrations_dir)
        sys.exit(0)

    conn: asyncpg.Connection = await asyncpg.connect(dsn)
    try:
        for sql_file in sql_files:
            print(f"Running {sql_file.name} ...")
            sql = sql_file.read_text(encoding="utf-8")
            await conn.execute(sql)
            print(f"  OK: {sql_file.name}")
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        await conn.close()

    print("All migrations applied successfully.")


if __name__ == "__main__":
    asyncio.run(run_migrations())
