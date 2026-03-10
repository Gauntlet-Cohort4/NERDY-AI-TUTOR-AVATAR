"""List available Simli face IDs for the tutor avatar.

Usage: python scripts/list-faces.py
Requires: SIMLI_API_KEY in .env
"""

import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    api_key = os.getenv("SIMLI_API_KEY")
    if not api_key:
        print("Error: SIMLI_API_KEY not set in .env")
        sys.exit(1)

    try:
        resp = requests.get(
            "https://api.simli.ai/faces",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        resp.raise_for_status()
        faces = resp.json()
        print(f"\n{'Name':<30} {'Face ID':<40}")
        print("-" * 70)
        for face in faces:
            name = face.get("name", "Unknown")
            face_id = face.get("id", "Unknown")
            print(f"{name:<30} {face_id:<40}")
    except requests.RequestException as exc:
        print(f"Error fetching faces: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
