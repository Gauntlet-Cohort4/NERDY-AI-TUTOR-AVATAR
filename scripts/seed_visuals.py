"""Seed visual assets from manifest.json into the database.

Usage:
    DATABASE_URL=postgres://... python scripts/seed_visuals.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

import asyncpg


async def main() -> None:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)

    manifest_path = os.path.join(
        os.path.dirname(__file__), "..", "assets", "visuals", "manifest.json"
    )
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    conn = await asyncpg.connect(dsn)
    count = 0
    try:
        for asset in manifest.get("assets", []):
            await conn.execute(
                """INSERT INTO visual_assets
                       (subject, topic_key, asset_type, title, content, metadata)
                   VALUES ($1, $2, $3, $4, $5, $6::jsonb)
                   ON CONFLICT (subject, topic_key) DO UPDATE SET
                       title    = EXCLUDED.title,
                       content  = EXCLUDED.content,
                       metadata = EXCLUDED.metadata""",
                asset["subject"],
                asset["topic_key"],
                asset["asset_type"],
                asset["title"],
                asset["content"],
                json.dumps(asset.get("metadata", {})),
            )
            count += 1
    finally:
        await conn.close()

    print(f"Seeded {count} visual assets")


if __name__ == "__main__":
    asyncio.run(main())
