"""Load data/dataset/manifest.json into the database.

Usage (from the repo root, after scripts/init_db.py):
    python backend/scripts/load_dataset.py
    python backend/scripts/load_dataset.py --no-jobs   # only sites and images
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.db import connect  # noqa: E402

MANIFEST = REPO_ROOT / "data" / "dataset" / "manifest.json"


def _site_id(conn, site: dict[str, Any]) -> int:
    row = conn.execute(
        """SELECT id FROM sites
           WHERE lower(name)=lower(%s) AND coalesce(region, '')=coalesce(%s, '')
           ORDER BY id LIMIT 1""",
        (site["name"], site.get("region")),
    ).fetchone()
    if row:
        conn.execute(
            """UPDATE sites SET
                 description=COALESCE(NULLIF(description, ''), %s),
                 description_source=COALESCE(NULLIF(description_source, ''), %s),
                 lat=COALESCE(lat, %s), lon=COALESCE(lon, %s), updated_at=now()
               WHERE id=%s""",
            (
                site.get("description"),
                site.get("description_source"),
                site.get("lat"),
                site.get("lon"),
                row["id"],
            ),
        )
        return int(row["id"])
    created = conn.execute(
        """INSERT INTO sites
             (name, region, district, category, lat, lon, description, description_source)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
        (
            site["name"],
            site.get("region"),
            site.get("district"),
            site.get("category"),
            site.get("lat"),
            site.get("lon"),
            site.get("description"),
            site.get("description_source"),
        ),
    ).fetchone()
    assert created is not None
    return int(created["id"])


def _insert_image(conn, site_id: int, image: dict[str, Any], queue_job: bool) -> bool:
    existing = conn.execute("SELECT id FROM images WHERE sha256=%s", (image["sha256"],)).fetchone()
    if existing:
        return False
    storage_path = (REPO_ROOT / image["local_path"]).resolve()
    row = conn.execute(
        """INSERT INTO images
             (site_id, storage_path, original_filename, author, licence, licence_url,
              source_url, sha256, width, height, mime_type, file_size)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
        (
            site_id,
            str(storage_path),
            image.get("file_title"),
            image.get("author"),
            image.get("licence"),
            image.get("licence_url"),
            image.get("source_url"),
            image["sha256"],
            image.get("local_width") or image.get("width"),
            image.get("local_height") or image.get("height"),
            image.get("mime_type"),
            image.get("file_size"),
        ),
    ).fetchone()
    assert row is not None
    if queue_job:
        conn.execute("INSERT INTO jobs (image_id) VALUES (%s)", (row["id"],))
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--no-jobs", action="store_true", help="do not queue embedding jobs")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    sites = 0
    images = 0
    with connect() as conn:
        for site in manifest.get("sites", []):
            site_id = _site_id(conn, site)
            sites += 1
            for image in site.get("images", []):
                images += int(_insert_image(conn, site_id, image, not args.no_jobs))
    print(f"Loaded {sites} sites and {images} new images.")
    if not args.no_jobs:
        print("Embedding jobs queued; start backend/worker.py to process them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
