"""List available Cartesia voices for the tutor avatar.

Usage: python scripts/list-voices.py
Requires: CARTESIA_API_KEY in .env
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()


async def main() -> None:
    api_key = os.getenv("CARTESIA_API_KEY")
    if not api_key:
        print("Error: CARTESIA_API_KEY not set in .env")
        sys.exit(1)

    try:
        from cartesia import AsyncCartesia

        client = AsyncCartesia(api_key=api_key)
        voices = await client.voices.list()
        print(f"\n{'Name':<30} {'ID':<40} {'Language'}")
        print("-" * 80)
        for voice in voices:
            name = getattr(voice, "name", "Unknown")
            voice_id = getattr(voice, "id", "Unknown")
            lang = getattr(voice, "language", "en")
            print(f"{name:<30} {voice_id:<40} {lang}")
        await client.close()
    except ImportError:
        print("Error: cartesia package not installed. Run: pip install cartesia")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
