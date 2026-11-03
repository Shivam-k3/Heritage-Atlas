"""Load data/dataset/manifest.json into the database.

Usage (from the repo root, after scripts/init_db.py):
    python backend/scripts/load_dataset.py
    python backend/scripts/load_dataset.py --dry-run
    python backend/scripts/load_dataset.py --no-jobs
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.db import connect  # noqa: E402

MANIFEST = REPO_ROOT / "data" / "dataset" / "manifest.json"
PROCESSABLE_IMAGE_STATUSES = frozenset({"uploaded", "failed"})


def _site_key(site: dict[str, Any]) -> tuple[str, str]:
    return (site["name"].casefold(), (site.get("region") or "").casefold())


def _validate_manifest(manifest: dict[str, Any], repo_root: Path = REPO_ROOT) -> None:
    sites = manifest.get("sites")
    if not isinstance(sites, list):
        raise ValueError("manifest must contain a sites list")
    seen_sites: set[tuple[str, str]] = set()
    seen_hashes: set[str] = set()
    for site in sites:
        if not isinstance(site, dict) or not isinstance(site.get("name"), str):
            raise ValueError("each manifest site must have a name")
        key = _site_key(site)
        if key in seen_sites:
            raise ValueError(
                f"duplicate manifest site name/region combination: {site['name']} / "
                f"{site.get('region') or ''}"
            )
        seen_sites.add(key)
        images = site.get("images")
        if not isinstance(images, list):
            raise ValueError(f"site {site['name']} must contain an images list")
        for image in images:
            if not isinstance(image, dict):
                raise ValueError(f"site {site['name']} contains an invalid image record")
            local_path = image.get("local_path")
            expected_hash = image.get("sha256")
            if not isinstance(local_path, str) or not local_path:
                raise ValueError(f"site {site['name']} contains an image without local_path")
            if not isinstance(expected_hash, str) or len(expected_hash) != 64:
                raise ValueError(f"invalid SHA-256 for {local_path}")
            path = (repo_root / local_path).resolve()
            if not path.is_file():
                raise ValueError(f"missing image file: {local_path}")
            actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual_hash != expected_hash:
                raise ValueError(
                    f"SHA-256 mismatch for {local_path}: expected {expected_hash}, "
                    f"got {actual_hash}"
                )
            if expected_hash in seen_hashes:
                raise ValueError(f"duplicate manifest SHA-256: {expected_hash}")
            seen_hashes.add(expected_hash)


def _site_id(conn, site: dict[str, Any]) -> int:
    rows = conn.execute(
        """SELECT id FROM sites
           WHERE lower(name)=lower(%s) AND coalesce(region, '')=coalesce(%s, '')
           ORDER BY id""",
        (site["name"], site.get("region")),
    ).fetchall()
    if len(rows) > 1:
        raise ValueError(
            f"duplicate existing site name/region combination: {site['name']} / "
            f"{site.get('region') or ''}"
        )
    if rows:
        row = rows[0]
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
    existing = conn.execute(
        "SELECT id, status FROM images WHERE sha256=%s", (image["sha256"],)
    ).fetchone()
    if existing:
        if queue_job and existing["status"] in PROCESSABLE_IMAGE_STATUSES:
            job = conn.execute(
                """SELECT id FROM jobs
                   WHERE image_id=%s AND job_type='process_image'
                   LIMIT 1""",
                (existing["id"],),
            ).fetchone()
            if not job:
                conn.execute("INSERT INTO jobs (image_id) VALUES (%s)", (existing["id"],))
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


def _dry_run(manifest: dict[str, Any]) -> dict[str, int | str]:
    _validate_manifest(manifest, REPO_ROOT)
    sites = manifest["sites"]
    image_count = sum(len(site["images"]) for site in sites)
    return {
        "site_inserts": len(sites),
        "site_updates": 0,
        "image_inserts": image_count,
        "image_skips": 0,
        "job_inserts": image_count,
        "existing_images_without_jobs": "not checked (database not accessed)",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--no-jobs", action="store_true", help="do not queue embedding jobs")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate the manifest and report planned writes without database access",
    )
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if args.dry_run:
        report = _dry_run(manifest)
        print("Dry run: no database writes performed.")
        for key, value in report.items():
            print(f"{key}: {value}")
        return 0
    _validate_manifest(manifest)
    sites = 0
    images = 0
    with connect() as conn:
        for site in manifest["sites"]:
            site_id = _site_id(conn, site)
            sites += 1
            for image in site["images"]:
                images += int(_insert_image(conn, site_id, image, not args.no_jobs))
    print(f"Loaded {sites} sites and {images} new images.")
    if not args.no_jobs:
        print("Embedding jobs queued; start backend/worker.py to process them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
