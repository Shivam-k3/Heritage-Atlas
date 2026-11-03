"""Embed site descriptions with MiniLM. Run after seeding a dataset.

Usage (from the repo root):
    python backend/scripts/embed_descriptions.py
"""

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app import ml  # noqa: E402
from app.db import connect  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="re-embed every description")
    args = parser.parse_args()

    with connect() as conn:
        if args.force:
            rows = conn.execute(
                "SELECT id, description FROM sites WHERE description IS NOT NULL ORDER BY id"
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT id, description FROM sites
                   WHERE description_embedding IS NULL AND description IS NOT NULL
                   ORDER BY id"""
            ).fetchall()
        if not rows:
            print("No descriptions to embed.")
            return 0
        vectors = ml.embed_texts([str(row["description"]) for row in rows])
        for row, vector in zip(rows, vectors, strict=True):
            conn.execute(
                "UPDATE sites SET description_embedding=%s, updated_at=now() WHERE id=%s",
                (vector, row["id"]),
            )
    print(f"Embedded {len(rows)} site descriptions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
